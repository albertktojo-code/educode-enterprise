from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .enums import ReviewAssignmentStatus, RubricStatus


def optional_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


async def ensure_review_assignment(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    attempt_id: uuid.UUID,
    response_id: uuid.UUID,
    question_version_id: uuid.UUID,
    reviewer_user_id: uuid.UUID,
    assigned_by_user_id: uuid.UUID,
    initiated_by_user_id: uuid.UUID,
    rubric_version_id: uuid.UUID | str | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> models.ReviewAssignment:
    """Create the canonical review queue entry once for a submitted response."""
    existing = await session.scalar(
        select(models.ReviewAssignment).where(
            models.ReviewAssignment.organization_id == organization_id,
            models.ReviewAssignment.response_id == response_id,
            models.ReviewAssignment.review_round == 1,
        )
    )
    if existing is not None:
        return existing

    published_rubric_id = optional_uuid(rubric_version_id)
    if published_rubric_id is not None:
        rubric = await session.scalar(
            select(models.ReviewRubricVersion).where(
                models.ReviewRubricVersion.organization_id == organization_id,
                models.ReviewRubricVersion.id == published_rubric_id,
                models.ReviewRubricVersion.status == RubricStatus.PUBLISHED.value,
            )
        )
        if rubric is None:
            published_rubric_id = None

    assignment = models.ReviewAssignment(
        organization_id=organization_id,
        attempt_id=attempt_id,
        response_id=response_id,
        question_version_id=question_version_id,
        rubric_version_id=published_rubric_id,
        reviewer_user_id=reviewer_user_id,
        assigned_by_user_id=assigned_by_user_id,
        review_round=1,
        review_mode="SINGLE",
        status=ReviewAssignmentStatus.PENDING.value,
        priority=50,
        context_snapshot=context_snapshot or {},
    )
    session.add(assignment)
    await session.flush()
    session.add(
        models.ReviewAuditEvent(
            organization_id=organization_id,
            entity_type="REVIEW_ASSIGNMENT",
            entity_id=assignment.id,
            event_type="ASSIGNED",
            actor_user_id=initiated_by_user_id,
            previous_snapshot={},
            new_snapshot={
                "reviewer_user_id": str(reviewer_user_id),
                "response_id": str(response_id),
                "source": (context_snapshot or {}).get("source"),
            },
            justification="Atribuicao automatica apos submissao para revisao humana.",
        )
    )
    return assignment
