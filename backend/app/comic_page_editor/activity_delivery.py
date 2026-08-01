from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.assessment_delivery.access import canonical_target_type

if TYPE_CHECKING:
    from .compat import ActorContext


TERMINAL_SESSION_STATUSES = {
    "SUBMITTED",
    "UNDER_REVIEW",
}
ACTIVE_PRESENCE_STATUSES = {
    "STARTED",
    "READING",
    "ANSWERING",
}


def derive_presence_status(
    session_status: str | None,
    experience_stage: str | None,
) -> str:
    if session_status is None:
        return "NOT_STARTED"
    if session_status in {"PAUSED", "TIMED_OUT", "CANCELLED"}:
        return "PAUSED"
    if session_status in TERMINAL_SESSION_STATUSES:
        return "COMPLETED"
    if experience_stage == "COMPLETED":
        return "COMPLETED"
    if experience_stage == "READING":
        return "READING"
    if experience_stage == "ACTIVITY":
        return "ANSWERING"
    return "STARTED"


def safe_idle_threshold(value: object, *, default: int = 180) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return min(3600, max(30, parsed))


def _hint_payload(value: object, level: int) -> dict[str, Any] | None:
    if isinstance(value, str) and value.strip():
        return {"level": level, "message": value.strip()}
    if not isinstance(value, dict):
        return None
    message = next(
        (
            str(value[key]).strip()
            for key in ("message", "content", "hint", "text")
            if value.get(key)
        ),
        "",
    )
    if not message:
        return None
    return {
        "level": int(value.get("level") or level),
        "message": message,
        "label": str(value.get("label") or f"Dica {level}"),
    }


async def create_delivery(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    data: Any,
) -> tuple[Any, Any]:
    from app.assessment_delivery.models import (
        AssessmentPublication,
        AssessmentTarget,
    )

    from . import models

    activities = list(
        (
            await session.scalars(
                select(models.HQActivityBinding)
                .where(
                    models.HQActivityBinding.organization_id
                    == actor.organization_id,
                    models.HQActivityBinding.comic_project_id == project_id,
                    models.HQActivityBinding.status == "APPROVED",
                )
                .order_by(models.HQActivityBinding.display_order)
            )
        ).all()
    )
    if not activities:
        raise HTTPException(409, "A HQ não possui atividades aprovadas.")
    publication = AssessmentPublication(
        organization_id=actor.organization_id,
        code=f"HQ-{str(project_id)[:8]}-{uuid.uuid4().hex[:6]}".upper(),
        title=data.title,
        version=1,
        source_type="HQ_ACTIVITY_SET",
        source_id=project_id,
        item_snapshot=[
            {
                "activity_binding_id": str(item.id),
                "question_version_id": str(item.question_version_id),
                "title": item.title,
                "activity_type": item.activity_type,
                "max_score": item.max_score,
            }
            for item in activities
        ],
        status="DRAFT",
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        duration_minutes=data.duration_minutes,
        max_attempts=data.max_attempts,
        navigation_mode=data.navigation_mode,
        shuffle_questions=data.shuffle_questions,
        shuffle_options=data.shuffle_options,
        allow_resume=data.allow_resume,
        autosave_seconds=data.autosave_seconds,
        delivery_rules={
            "reader_required": data.reader_required,
            "release_answer_key": data.release_answer_key,
            "comic_project_id": str(project_id),
        },
        access_settings=data.access_settings,
        created_by_user_id=actor.user_id,
    )
    session.add(publication)
    await session.flush()
    for target in data.targets:
        session.add(
            AssessmentTarget(
                organization_id=actor.organization_id,
                publication_id=publication.id,
                target_type=canonical_target_type(target.target_type),
                target_id=target.target_id,
                available_from=target.available_from,
                available_until=target.available_until,
                extra_attempts=target.extra_attempts,
                custom_duration_minutes=target.custom_duration_minutes,
                status="ACTIVE",
                assigned_by_user_id=actor.user_id,
            )
        )
    link = models.HQActivityDeliveryLink(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        publication_id=publication.id,
        delivery_mode=data.delivery_mode,
        reader_required=data.reader_required,
        release_answer_key=data.release_answer_key,
        monitoring_settings=data.monitoring_settings,
        status="SCHEDULED",
        created_by_user_id=actor.user_id,
    )
    session.add(link)
    for item in activities:
        item.publication_id = publication.id
    await session.flush()
    return link, publication


async def publish_delivery(
    session: AsyncSession,
    *,
    actor: ActorContext,
    link_id: uuid.UUID,
) -> tuple[Any, Any]:
    from app.assessment_delivery.models import AssessmentPublication

    from . import models

    link = await session.scalar(
        select(models.HQActivityDeliveryLink)
        .where(
            models.HQActivityDeliveryLink.organization_id
            == actor.organization_id,
            models.HQActivityDeliveryLink.id == link_id,
        )
        .with_for_update()
    )
    if link is None:
        raise HTTPException(404, "Aplicação não encontrada.")
    publication = await session.scalar(
        select(AssessmentPublication).where(
            AssessmentPublication.organization_id
            == actor.organization_id,
            AssessmentPublication.id == link.publication_id,
        )
    )
    if publication is None:
        raise HTTPException(404, "Publicação canônica não encontrada.")
    publication.status = "PUBLISHED"
    publication.published_by_user_id = actor.user_id
    publication.published_at = datetime.now(UTC)
    link.status = "PUBLISHED"
    link.published_by_user_id = actor.user_id
    link.published_at = datetime.now(UTC)
    await session.flush()
    return link, publication


async def _audience_for_targets(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    targets: list[Any],
) -> tuple[
    set[uuid.UUID],
    dict[uuid.UUID, set[uuid.UUID]],
    dict[uuid.UUID, list[Any]],
    dict[uuid.UUID, str],
]:
    from app.models.adaptive import AdaptiveGroupMember, AdaptiveStudentGroup
    from app.models.auth import Membership, User
    from app.models.education import Classroom, ClassroomEnrollment

    classroom_target_ids = {
        target.target_id
        for target in targets
        if canonical_target_type(target.target_type) == "CLASSROOM"
    }
    group_target_ids = {
        target.target_id
        for target in targets
        if canonical_target_type(target.target_type) == "GROUP"
    }
    target_students: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    classroom_ids_by_student: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    classroom_names: dict[uuid.UUID, str] = {}

    for target in targets:
        if canonical_target_type(target.target_type) == "STUDENT":
            target_students[target.id].add(target.target_id)

    if classroom_target_ids:
        classroom_rows = (
            await session.execute(
                select(Classroom.id, Classroom.name).where(
                    Classroom.organization_id == organization_id,
                    Classroom.id.in_(classroom_target_ids),
                    Classroom.is_active.is_(True),
                )
            )
        ).all()
        classroom_names = {
            classroom_id: name
            for classroom_id, name in classroom_rows
        }
        enrollment_rows = (
            await session.execute(
                select(
                    ClassroomEnrollment.classroom_id,
                    ClassroomEnrollment.user_id,
                )
                .join(
                    Classroom,
                    Classroom.id == ClassroomEnrollment.classroom_id,
                )
                .where(
                    Classroom.organization_id == organization_id,
                    Classroom.id.in_(classroom_names),
                    ClassroomEnrollment.role.ilike("student"),
                )
            )
        ).all()
        target_by_classroom = {
            target.target_id: target
            for target in targets
            if canonical_target_type(target.target_type) == "CLASSROOM"
        }
        for classroom_id, student_id in enrollment_rows:
            target = target_by_classroom.get(classroom_id)
            if target is None:
                continue
            target_students[target.id].add(student_id)
            classroom_ids_by_student[student_id].add(classroom_id)

    if group_target_ids:
        group_rows = (
            await session.execute(
                select(
                    AdaptiveGroupMember.group_id,
                    AdaptiveGroupMember.student_id,
                    AdaptiveStudentGroup.classroom_id,
                )
                .join(
                    AdaptiveStudentGroup,
                    AdaptiveStudentGroup.id == AdaptiveGroupMember.group_id,
                )
                .where(
                    AdaptiveStudentGroup.organization_id == organization_id,
                    AdaptiveStudentGroup.id.in_(group_target_ids),
                    AdaptiveStudentGroup.status == "active",
                    AdaptiveGroupMember.organization_id == organization_id,
                    AdaptiveGroupMember.removed_at.is_(None),
                )
            )
        ).all()
        target_by_group = {
            target.target_id: target
            for target in targets
            if canonical_target_type(target.target_type) == "GROUP"
        }
        for group_id, student_id, classroom_id in group_rows:
            target = target_by_group.get(group_id)
            if target is None:
                continue
            target_students[target.id].add(student_id)
            if classroom_id:
                classroom_ids_by_student[student_id].add(classroom_id)

    candidate_ids = {
        student_id
        for student_ids in target_students.values()
        for student_id in student_ids
    }
    if not candidate_ids:
        return set(), classroom_ids_by_student, {}, classroom_names

    active_user_rows = (
        await session.execute(
            select(User.id, User.full_name)
                .join(
                    Membership,
                    and_(
                        Membership.user_id == User.id,
                        Membership.organization_id == organization_id,
                        Membership.is_active.is_(True),
                    ),
                )
                .where(
                    User.id.in_(candidate_ids),
                    User.is_active.is_(True),
                )
            )
    ).all()
    active_ids = {user_id for user_id, _ in active_user_rows}
    targets_by_student: dict[uuid.UUID, list[Any]] = defaultdict(list)
    target_lookup = {target.id: target for target in targets}
    for target_id, student_ids in target_students.items():
        target = target_lookup[target_id]
        for student_id in student_ids.intersection(active_ids):
            targets_by_student[student_id].append(target)
    user_names = {
        user_id: full_name
        for user_id, full_name in active_user_rows
    }
    return active_ids, classroom_ids_by_student, targets_by_student, {
        **classroom_names,
        **user_names,
    }


def _effective_target(targets: list[Any]) -> Any | None:
    priority = {"STUDENT": 0, "CLASSROOM": 1, "GROUP": 2}
    if not targets:
        return None
    return min(
        targets,
        key=lambda item: (
            priority.get(canonical_target_type(item.target_type), 99),
            str(item.id),
        ),
    )


async def monitoring_summary(
    session: AsyncSession,
    *,
    actor: ActorContext,
    link_id: uuid.UUID,
    classroom_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    idle_threshold_seconds: int | None = None,
) -> dict[str, Any]:
    from app.assessment_delivery.models import (
        AssessmentPublication,
        AssessmentSession,
        AssessmentSessionEvent,
        AssessmentSessionItem,
        AssessmentTarget,
    )
    from app.models.auth import Membership, User

    from . import models
    from .student_experience import combined_progress

    link = await session.scalar(
        select(models.HQActivityDeliveryLink).where(
            models.HQActivityDeliveryLink.organization_id
            == actor.organization_id,
            models.HQActivityDeliveryLink.id == link_id,
        )
    )
    if link is None:
        raise HTTPException(404, "Aplicação não encontrada.")
    publication = await session.scalar(
        select(AssessmentPublication).where(
            AssessmentPublication.organization_id == actor.organization_id,
            AssessmentPublication.id == link.publication_id,
        )
    )
    if publication is None:
        raise HTTPException(404, "Publicação canônica não encontrada.")

    targets = list(
        (
            await session.scalars(
                select(AssessmentTarget).where(
                    AssessmentTarget.organization_id
                    == actor.organization_id,
                    AssessmentTarget.publication_id == link.publication_id,
                    AssessmentTarget.status == "ACTIVE",
                )
            )
        ).all()
    )
    (
        audience_ids,
        classroom_ids_by_student,
        targets_by_student,
        labels,
    ) = await _audience_for_targets(
        session,
        organization_id=actor.organization_id,
        targets=targets,
    )

    sessions = list(
        (
            await session.scalars(
                select(AssessmentSession)
                .where(
                    AssessmentSession.organization_id
                    == actor.organization_id,
                    AssessmentSession.publication_id == link.publication_id,
                )
                .order_by(
                    AssessmentSession.student_id,
                    AssessmentSession.session_number.desc(),
                    AssessmentSession.created_at.desc(),
                )
            )
        ).all()
    )
    audience_ids.update(item.student_id for item in sessions)
    missing_user_ids = audience_ids.difference(labels)
    if missing_user_ids:
        extra_user_rows = (
            await session.execute(
                select(User.id, User.full_name)
                    .join(
                        Membership,
                        and_(
                            Membership.user_id == User.id,
                            Membership.organization_id
                            == actor.organization_id,
                            Membership.is_active.is_(True),
                        ),
                    )
                    .where(
                        User.id.in_(missing_user_ids),
                        User.is_active.is_(True),
                    )
                )
        ).all()
        for missing_student_id, full_name in extra_user_rows:
            labels[missing_student_id] = full_name

    latest_sessions: dict[uuid.UUID, AssessmentSession] = {}
    attempts_by_student: dict[uuid.UUID, int] = defaultdict(int)
    for item in sessions:
        if item.status != "CANCELLED":
            attempts_by_student[item.student_id] += 1
            latest_sessions.setdefault(item.student_id, item)

    states = list(
        (
            await session.scalars(
                select(models.HQStudentExperienceState).where(
                    models.HQStudentExperienceState.organization_id
                    == actor.organization_id,
                    models.HQStudentExperienceState.publication_id
                    == link.publication_id,
                )
            )
        ).all()
    )
    states_by_student = {item.student_id: item for item in states}
    activities = list(
        (
            await session.scalars(
                select(models.HQActivityBinding)
                .options(
                    load_only(
                        models.HQActivityBinding.id,
                        models.HQActivityBinding.title,
                        models.HQActivityBinding.difficulty,
                        models.HQActivityBinding.display_order,
                    )
                )
                .where(
                    models.HQActivityBinding.organization_id
                    == actor.organization_id,
                    models.HQActivityBinding.comic_project_id
                    == link.comic_project_id,
                    models.HQActivityBinding.status.in_(
                        ["APPROVED", "PUBLISHED"]
                    ),
                )
                .order_by(models.HQActivityBinding.display_order)
            )
        ).all()
    )
    profiles = list(
        (
            await session.scalars(
                select(models.HQActivityFeedbackProfile).where(
                    models.HQActivityFeedbackProfile.organization_id
                    == actor.organization_id,
                    models.HQActivityFeedbackProfile.activity_binding_id.in_(
                        [item.id for item in activities]
                    ),
                    models.HQActivityFeedbackProfile.status == "APPROVED",
                )
            )
        ).all()
    ) if activities else []
    profiles_by_activity = {
        item.activity_binding_id: item
        for item in profiles
    }

    latest_session_ids = [item.id for item in latest_sessions.values()]
    item_counts: dict[uuid.UUID, list[int]] = defaultdict(
        lambda: [0, 0]
    )
    events_by_session: dict[
        uuid.UUID,
        list[AssessmentSessionEvent],
    ] = defaultdict(list)
    if latest_session_ids:
        session_items = list(
            (
                await session.scalars(
                    select(AssessmentSessionItem).where(
                        AssessmentSessionItem.organization_id
                        == actor.organization_id,
                        AssessmentSessionItem.session_id.in_(
                            latest_session_ids
                        ),
                    )
                )
            ).all()
        )
        for session_item_row in session_items:
            item_counts[session_item_row.session_id][0] += 1
            if session_item_row.status == "ANSWERED":
                item_counts[session_item_row.session_id][1] += 1
        session_events = list(
            (
                await session.scalars(
                    select(AssessmentSessionEvent)
                    .where(
                        AssessmentSessionEvent.organization_id
                        == actor.organization_id,
                        AssessmentSessionEvent.session_id.in_(
                            latest_session_ids
                        ),
                        AssessmentSessionEvent.event_type.in_(
                            [
                                "STUDENT_HELP_REQUESTED",
                                "TEACHER_SEND_MESSAGE",
                                "TEACHER_RELEASE_HINT",
                                "TEACHER_RELEASE_ANSWER_KEY",
                            ]
                        ),
                    )
                    .order_by(AssessmentSessionEvent.occurred_at.desc())
                )
            ).all()
        )
        for event in session_events:
            events_by_session[event.session_id].append(event)

    now = datetime.now(UTC)
    configured_idle = link.monitoring_settings.get(
        "idle_threshold_seconds",
        180,
    )
    idle_threshold = safe_idle_threshold(
        idle_threshold_seconds
        if idle_threshold_seconds is not None
        else configured_idle
    )
    rows: list[dict[str, Any]] = []
    for current_student_id in sorted(audience_ids, key=str):
        if current_student_id not in labels:
            continue
        if student_id and current_student_id != student_id:
            continue
        student_classroom_ids = classroom_ids_by_student.get(
            current_student_id,
            set(),
        )
        if classroom_id and classroom_id not in student_classroom_ids:
            continue
        assessment_session = latest_sessions.get(current_student_id)
        state = states_by_student.get(current_student_id)
        if (
            assessment_session is not None
            and state is not None
            and state.assessment_session_id != assessment_session.id
        ):
            state = None
        presence_status = derive_presence_status(
            assessment_session.status if assessment_session else None,
            state.current_stage if state else None,
        )
        if status_filter and presence_status != status_filter.upper():
            continue

        current_activity = None
        if state and activities:
            current_activity = activities[
                min(state.current_activity_index, len(activities) - 1)
            ]
        total_items, answered_items = (
            item_counts.get(assessment_session.id, [0, 0])
            if assessment_session
            else [0, 0]
        )
        total_activity_count = (
            state.total_activity_count
            if state
            else total_items or len(activities)
        )
        answered_count = state.answered_count if state else answered_items
        activity_progress = (
            state.activity_progress
            if state
            else (
                round(
                    (answered_count / total_activity_count) * 100,
                    2,
                )
                if total_activity_count
                else 0.0
            )
        )
        reading_progress = state.reading_progress if state else 0.0
        progress = combined_progress(
            reading_progress=reading_progress,
            activity_progress=activity_progress,
            reader_required=link.reader_required,
        )

        session_events = (
            events_by_session.get(assessment_session.id, [])
            if assessment_session
            else []
        )
        last_interaction_candidates = [
            value
            for value in (
                assessment_session.last_activity_at
                if assessment_session
                else None,
                assessment_session.started_at
                if assessment_session
                else None,
                state.updated_at if state else None,
            )
            if value is not None
        ]
        last_interaction_at = (
            max(last_interaction_candidates)
            if last_interaction_candidates
            else None
        )
        idle_seconds = (
            max(0, int((now - last_interaction_at).total_seconds()))
            if last_interaction_at
            else None
        )
        is_idle = bool(
            presence_status in ACTIVE_PRESENCE_STATUSES
            and idle_seconds is not None
            and idle_seconds >= idle_threshold
        )

        help_event = next(
            (
                event
                for event in session_events
                if event.source == "CLIENT"
                and event.event_type == "STUDENT_HELP_REQUESTED"
            ),
            None,
        )
        latest_teacher_support = next(
            (
                event
                for event in session_events
                if event.source == "TEACHER"
                and event.event_type
                in {
                    "TEACHER_SEND_MESSAGE",
                    "TEACHER_RELEASE_HINT",
                }
            ),
            None,
        )
        help_pending = bool(
            help_event
            and (
                latest_teacher_support is None
                or help_event.occurred_at
                > latest_teacher_support.occurred_at
            )
        )
        answer_key_released = any(
            event.source == "TEACHER"
            and event.event_type == "TEACHER_RELEASE_ANSWER_KEY"
            for event in session_events
        )
        released_hint_count = sum(
            1
            for event in session_events
            if event.source == "TEACHER"
            and event.event_type == "TEACHER_RELEASE_HINT"
            and current_activity is not None
            and event.metadata_payload.get("activity_id")
            == str(current_activity.id)
        )
        next_hint = None
        if current_activity is not None:
            profile = profiles_by_activity.get(current_activity.id)
            if (
                profile is not None
                and released_hint_count < len(profile.graduated_hints)
            ):
                next_hint = _hint_payload(
                    profile.graduated_hints[released_hint_count],
                    released_hint_count + 1,
                )

        alerts: list[dict[str, str]] = []
        if is_idle:
            alerts.append(
                {
                    "code": "IDLE",
                    "severity": "WARNING",
                    "message": "Sem interação além do limite configurado.",
                }
            )
        if help_pending:
            alerts.append(
                {
                    "code": "HELP_REQUESTED",
                    "severity": "HIGH",
                    "message": "O estudante solicitou ajuda.",
                }
            )
        if (
            assessment_session is not None
            and assessment_session.integrity_status != "NORMAL"
        ):
            alerts.append(
                {
                    "code": "ATTENTION_SIGNAL",
                    "severity": "INFO",
                    "message": (
                        "Há sinais descritivos que pedem revisão humana."
                    ),
                }
            )

        effective_target = _effective_target(
            targets_by_student.get(current_student_id, [])
        )
        rows.append(
            {
                "student_id": str(current_student_id),
                "student_name": labels[current_student_id],
                "classroom_ids": [
                    str(item)
                    for item in sorted(student_classroom_ids, key=str)
                ],
                "classroom_names": [
                    labels.get(item, str(item))
                    for item in sorted(student_classroom_ids, key=str)
                ],
                "session_id": (
                    str(assessment_session.id)
                    if assessment_session
                    else None
                ),
                "session_status": (
                    assessment_session.status
                    if assessment_session
                    else None
                ),
                "presence_status": presence_status,
                "current_page_number": (
                    state.current_page_number if state else None
                ),
                "current_panel_number": (
                    state.current_panel_number if state else None
                ),
                "current_activity_index": (
                    state.current_activity_index if state else None
                ),
                "current_activity_id": (
                    str(current_activity.id)
                    if current_activity
                    else None
                ),
                "current_activity_title": (
                    current_activity.title
                    if current_activity
                    else None
                ),
                "current_activity_difficulty": (
                    current_activity.difficulty
                    if current_activity
                    else None
                ),
                "reading_progress": reading_progress,
                "activity_progress": activity_progress,
                "combined_progress": progress,
                "answered_count": answered_count,
                "total_activity_count": total_activity_count,
                "last_interaction_at": last_interaction_at,
                "idle_seconds": idle_seconds,
                "is_idle": is_idle,
                "remaining_seconds": (
                    assessment_session.remaining_seconds
                    if assessment_session
                    else None
                ),
                "attempts_used": attempts_by_student.get(
                    current_student_id,
                    0,
                ),
                "attempts_allowed": publication.max_attempts
                + (
                    effective_target.extra_attempts
                    if effective_target
                    else 0
                ),
                "alerts": alerts,
                "support": {
                    "help_pending": help_pending,
                    "next_hint": next_hint,
                    "answer_key_released": answer_key_released,
                    "last_teacher_update_at": (
                        latest_teacher_support.occurred_at
                        if latest_teacher_support
                        else None
                    ),
                },
            }
        )

    status_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        status_counts[row["presence_status"]] += 1
    active_rows = [
        row
        for row in rows
        if row["presence_status"] in ACTIVE_PRESENCE_STATUSES
    ]
    return {
        "delivery": {
            "id": str(link.id),
            "publication_id": str(link.publication_id),
            "title": publication.title,
            "status": link.status,
            "starts_at": publication.starts_at,
            "ends_at": publication.ends_at,
        },
        "summary": {
            "total_students": len(rows),
            "status_counts": dict(status_counts),
            "started": sum(
                row["presence_status"] != "NOT_STARTED"
                for row in rows
            ),
            "active": len(active_rows),
            "completed": status_counts.get("COMPLETED", 0),
            "paused": status_counts.get("PAUSED", 0),
            "attention": sum(bool(row["alerts"]) for row in rows),
            "average_progress": (
                round(
                    sum(
                        float(row["combined_progress"])
                        for row in rows
                    )
                    / len(rows),
                    2,
                )
                if rows
                else 0.0
            ),
        },
        "filters": {
            "classrooms": [
                {
                    "id": str(item),
                    "name": labels.get(item, str(item)),
                }
                for item in sorted(
                    {
                        classroom
                        for values in classroom_ids_by_student.values()
                        for classroom in values
                    },
                    key=str,
                )
            ]
        },
        "students": rows,
        "monitoring": {
            "transport": "AUTHENTICATED_POLLING",
            "poll_after_seconds": 5,
            "idle_threshold_seconds": idle_threshold,
            "last_updated_at": now,
        },
        "privacy": {
            "answers_exposed": False,
            "answer_keys_exposed": False,
            "device_details_exposed": False,
            "ranking_enabled": False,
            "message": (
                "O painel exibe somente presença e progresso necessários "
                "ao acompanhamento pedagógico."
            ),
        },
    }
