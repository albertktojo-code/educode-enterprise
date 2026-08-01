from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import AdaptiveGroupMember, AdaptiveStudentGroup
from app.models.auth import Membership
from app.models.education import Classroom, ClassroomEnrollment

from . import models


def canonical_target_type(value: object) -> str:
    raw = getattr(value, "value", value)
    normalized = str(raw).upper()
    return "CLASSROOM" if normalized == "CLASS" else normalized


def target_window_is_open(
    target: models.AssessmentTarget,
    *,
    now: datetime | None = None,
) -> bool:
    instant = now or datetime.now(UTC)
    return (
        target.status == "ACTIVE"
        and (target.available_from is None or instant >= target.available_from)
        and (target.available_until is None or instant <= target.available_until)
    )


async def target_allows_student(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    target: models.AssessmentTarget,
    student_id: uuid.UUID,
) -> bool:
    active_membership = await session.scalar(
        select(Membership.id)
        .where(
            Membership.organization_id == organization_id,
            Membership.user_id == student_id,
            Membership.is_active.is_(True),
        )
        .limit(1)
    )
    if active_membership is None:
        return False

    target_type = canonical_target_type(target.target_type)
    if target_type == "STUDENT":
        return target.target_id == student_id

    if target_type == "CLASSROOM":
        enrollment = await session.scalar(
            select(ClassroomEnrollment.id)
            .join(Classroom, Classroom.id == ClassroomEnrollment.classroom_id)
            .where(
                Classroom.organization_id == organization_id,
                Classroom.is_active.is_(True),
                ClassroomEnrollment.classroom_id == target.target_id,
                ClassroomEnrollment.user_id == student_id,
                ClassroomEnrollment.role.ilike("student"),
            )
            .limit(1)
        )
        return enrollment is not None

    if target_type == "GROUP":
        membership = await session.scalar(
            select(AdaptiveGroupMember.id)
            .join(
                AdaptiveStudentGroup,
                AdaptiveStudentGroup.id == AdaptiveGroupMember.group_id,
            )
            .where(
                AdaptiveStudentGroup.organization_id == organization_id,
                AdaptiveStudentGroup.id == target.target_id,
                AdaptiveStudentGroup.status == "active",
                AdaptiveGroupMember.organization_id == organization_id,
                AdaptiveGroupMember.student_id == student_id,
                AdaptiveGroupMember.removed_at.is_(None),
            )
            .limit(1)
        )
        return membership is not None

    return False


async def resolve_student_target(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    publication_id: uuid.UUID,
    student_id: uuid.UUID,
    requested_target_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> models.AssessmentTarget | None:
    statement = select(models.AssessmentTarget).where(
        models.AssessmentTarget.organization_id == organization_id,
        models.AssessmentTarget.publication_id == publication_id,
        models.AssessmentTarget.status == "ACTIVE",
    )
    if requested_target_id is not None:
        statement = statement.where(models.AssessmentTarget.id == requested_target_id)

    targets = list((await session.scalars(statement)).all())
    eligible: list[models.AssessmentTarget] = []
    for target in targets:
        if not target_window_is_open(target, now=now):
            continue
        if await target_allows_student(
            session,
            organization_id=organization_id,
            target=target,
            student_id=student_id,
        ):
            eligible.append(target)

    priority = {"STUDENT": 0, "CLASSROOM": 1, "GROUP": 2}
    eligible.sort(
        key=lambda item: (
            priority.get(canonical_target_type(item.target_type), 99),
            str(item.id),
        )
    )
    return eligible[0] if eligible else None
