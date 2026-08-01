from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .activities import student_activity_payload

if TYPE_CHECKING:
    from .compat import ActorContext


def combined_progress(
    *,
    reading_progress: float,
    activity_progress: float,
    reader_required: bool,
) -> float:
    reading = max(0.0, min(100.0, reading_progress))
    activity = max(0.0, min(100.0, activity_progress))
    if not reader_required:
        return round(activity, 2)
    return round((reading * 0.45) + (activity * 0.55), 2)


def next_stage(
    *,
    reading_progress: float,
    activity_progress: float,
    reader_required: bool,
) -> str:
    if reader_required and reading_progress < 100:
        return "READING"
    if activity_progress < 100:
        return "ACTIVITY"
    return "COMPLETED"


async def accessible_published_release_id(
    session: AsyncSession,
    *,
    actor: ActorContext,
    comic_project_id: uuid.UUID,
) -> uuid.UUID | None:
    from app.comic_reader_access.services import release_for_actor
    from app.comic_review_publish.models import ComicEditorialRelease

    release_ids = list(
        (
            await session.scalars(
                select(ComicEditorialRelease.id)
                .where(
                    ComicEditorialRelease.organization_id
                    == actor.organization_id,
                    ComicEditorialRelease.comic_project_id == comic_project_id,
                    ComicEditorialRelease.status == "PUBLISHED",
                )
                .order_by(ComicEditorialRelease.release_number.desc())
            )
        ).all()
    )
    for release_id in release_ids:
        try:
            await release_for_actor(
                session,
                actor=actor,
                release_id=release_id,
            )
        except HTTPException:
            continue
        return release_id
    return None


async def experience_manifest(
    session: AsyncSession,
    *,
    actor: ActorContext,
    publication_id: uuid.UUID,
) -> dict[str, Any]:
    from app.assessment_delivery.access import resolve_student_target
    from app.assessment_delivery.enums import SessionStatus
    from app.assessment_delivery.models import (
        AssessmentAutosave,
        AssessmentPublication,
        AssessmentSession,
        AssessmentSessionEvent,
        AssessmentSessionItem,
    )
    from app.assessment_delivery.policies import effective_publication_status

    from . import models

    now = datetime.now(UTC)
    publication = await session.scalar(
        select(AssessmentPublication).where(
            AssessmentPublication.organization_id == actor.organization_id,
            AssessmentPublication.id == publication_id,
            AssessmentPublication.status == "PUBLISHED",
        )
    )
    if publication is None:
        raise HTTPException(404, "Aplicação publicada não encontrada.")
    if (
        effective_publication_status(
            publication.status,
            publication.starts_at,
            publication.ends_at,
            now,
        )
        != "OPEN"
    ):
        raise HTTPException(409, {"code": "ASSESSMENT_NOT_OPEN"})

    delivery = await session.scalar(
        select(models.HQActivityDeliveryLink).where(
            models.HQActivityDeliveryLink.organization_id
            == actor.organization_id,
            models.HQActivityDeliveryLink.publication_id == publication_id,
        )
    )
    if delivery is None:
        raise HTTPException(404, "Vínculo da experiência pós-HQ não encontrado.")

    release_id = await accessible_published_release_id(
        session,
        actor=actor,
        comic_project_id=delivery.comic_project_id,
    )

    target = await resolve_student_target(
        session,
        organization_id=actor.organization_id,
        publication_id=publication_id,
        student_id=actor.user_id,
        now=now,
    )
    if target is None:
        raise HTTPException(403, {"code": "ASSESSMENT_TARGET_NOT_ELIGIBLE"})

    pages = list(
        (
            await session.scalars(
                select(models.HQEditorPage)
                .where(
                    models.HQEditorPage.organization_id == actor.organization_id,
                    models.HQEditorPage.comic_project_id
                    == delivery.comic_project_id,
                    models.HQEditorPage.page_type.in_(
                        ["COVER", "STORY", "ACTIVITY", "BACK_COVER"]
                    ),
                )
                .order_by(models.HQEditorPage.page_number)
            )
        ).all()
    )
    activities = list(
        (
            await session.scalars(
                select(models.HQActivityBinding)
                .where(
                    models.HQActivityBinding.organization_id
                    == actor.organization_id,
                    models.HQActivityBinding.comic_project_id
                    == delivery.comic_project_id,
                    models.HQActivityBinding.status.in_(["APPROVED", "PUBLISHED"]),
                )
                .order_by(models.HQActivityBinding.display_order)
            )
        ).all()
    )

    state = await session.scalar(
        select(models.HQStudentExperienceState).where(
            models.HQStudentExperienceState.organization_id
            == actor.organization_id,
            models.HQStudentExperienceState.publication_id == publication_id,
            models.HQStudentExperienceState.student_id == actor.user_id,
        )
    )
    active_session = await session.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.organization_id == actor.organization_id,
            AssessmentSession.publication_id == publication_id,
            AssessmentSession.student_id == actor.user_id,
            AssessmentSession.status.in_(
                [SessionStatus.IN_PROGRESS.value, SessionStatus.PAUSED.value]
            ),
        )
        .order_by(AssessmentSession.session_number.desc())
        .limit(1)
    )
    support_session = active_session
    if support_session is None:
        support_session = await session.scalar(
            select(AssessmentSession)
            .where(
                AssessmentSession.organization_id
                == actor.organization_id,
                AssessmentSession.publication_id == publication_id,
                AssessmentSession.student_id == actor.user_id,
                AssessmentSession.status
                != SessionStatus.CANCELLED.value,
            )
            .order_by(AssessmentSession.session_number.desc())
            .limit(1)
        )
    teacher_events: list[AssessmentSessionEvent] = []
    if support_session is not None:
        teacher_events = list(
            (
                await session.scalars(
                    select(AssessmentSessionEvent)
                    .where(
                        AssessmentSessionEvent.organization_id
                        == actor.organization_id,
                        AssessmentSessionEvent.session_id
                        == support_session.id,
                        AssessmentSessionEvent.source == "TEACHER",
                        AssessmentSessionEvent.event_type.in_(
                            [
                                "TEACHER_SEND_MESSAGE",
                                "TEACHER_RELEASE_HINT",
                                "TEACHER_RELEASE_ANSWER_KEY",
                            ]
                        ),
                    )
                    .order_by(AssessmentSessionEvent.occurred_at)
                )
            ).all()
        )
    answer_key_released = (
        delivery.release_answer_key == "IMMEDIATE"
        or any(
            event.event_type == "TEACHER_RELEASE_ANSWER_KEY"
            for event in teacher_events
        )
        or (
            delivery.release_answer_key == "AFTER_SUBMISSION"
            and support_session is not None
            and support_session.status
            in {
                SessionStatus.SUBMITTED.value,
                SessionStatus.UNDER_REVIEW.value,
            }
        )
    )
    attempt_count = int(
        (
            await session.scalar(
                select(func.count(AssessmentSession.id)).where(
                    AssessmentSession.organization_id == actor.organization_id,
                    AssessmentSession.publication_id == publication_id,
                    AssessmentSession.student_id == actor.user_id,
                    AssessmentSession.status != SessionStatus.CANCELLED.value,
                )
            )
        )
        or 0
    )
    allowed_attempts = publication.max_attempts + target.extra_attempts

    session_items: list[AssessmentSessionItem] = []
    latest_responses: dict[uuid.UUID, AssessmentAutosave] = {}
    autosave_sequence = 0
    if active_session is not None:
        session_items = list(
            (
                await session.scalars(
                    select(AssessmentSessionItem)
                    .where(
                        AssessmentSessionItem.organization_id
                        == actor.organization_id,
                        AssessmentSessionItem.session_id == active_session.id,
                    )
                    .order_by(AssessmentSessionItem.position)
                )
            ).all()
        )
        autosaves = list(
            (
                await session.scalars(
                    select(AssessmentAutosave)
                    .where(
                        AssessmentAutosave.organization_id
                        == actor.organization_id,
                        AssessmentAutosave.session_id == active_session.id,
                    )
                    .order_by(AssessmentAutosave.sequence_number)
                )
            ).all()
        )
        for autosave in autosaves:
            latest_responses[autosave.session_item_id] = autosave
            autosave_sequence = max(autosave_sequence, autosave.sequence_number)

    items_by_question = {
        item.question_version_id: item for item in session_items
    }
    answered_count = sum(item.status == "ANSWERED" for item in session_items)
    total_activity_count = len(activities)
    activity_progress = (
        round((answered_count / total_activity_count) * 100, 2)
        if total_activity_count
        else 100.0
    )
    reading_progress = state.reading_progress if state else 0.0
    state_payload = {
        "id": str(state.id) if state else None,
        "current_stage": (
            state.current_stage
            if state
            else ("READING" if delivery.reader_required else "ACTIVITY")
        ),
        "current_page_number": state.current_page_number if state else 1,
        "current_panel_number": state.current_panel_number if state else 1,
        "current_activity_index": state.current_activity_index if state else 0,
        "reading_progress": reading_progress,
        "activity_progress": activity_progress,
        "answered_count": answered_count,
        "total_activity_count": total_activity_count,
        "combined_progress": combined_progress(
            reading_progress=reading_progress,
            activity_progress=activity_progress,
            reader_required=delivery.reader_required,
        ),
        "preferences": state.preferences if state else {},
        "navigation_state": state.navigation_state if state else {},
        "last_feedback": {},
        "last_sequence": state.last_sequence if state else 0,
        "completed_at": state.completed_at if state else None,
    }

    activity_payloads: list[dict[str, Any]] = []
    for activity in activities:
        session_item = (
            items_by_question.get(activity.question_version_id)
            if activity.question_version_id is not None
            else None
        )
        latest = (
            latest_responses.get(session_item.id)
            if session_item is not None
            else None
        )
        activity_payloads.append(
            {
                "id": str(activity.id),
                "question_version_id": (
                    str(activity.question_version_id)
                    if activity.question_version_id
                    else None
                ),
                "session_item_id": str(session_item.id) if session_item else None,
                "response_status": (
                    session_item.status if session_item else "NOT_STARTED"
                ),
                "saved_response": latest.response_payload if latest else {},
                "activity_page_id": str(activity.activity_page_id),
                "source_page_id": (
                    str(activity.source_page_id)
                    if activity.source_page_id
                    else None
                ),
                "source_panel_id": (
                    str(activity.source_panel_id)
                    if activity.source_panel_id
                    else None
                ),
                "activity_type": activity.activity_type,
                "title": activity.title,
                "instructions": activity.instructions,
                "activity_payload": student_activity_payload(
                    activity.activity_type,
                    activity.activity_payload,
                ),
                "released_answer_key": (
                    activity.answer_key
                    if answer_key_released
                    else None
                ),
                "difficulty": activity.difficulty,
                "max_score": activity.max_score,
                "pedagogical_links": activity.pedagogical_links,
                "accessibility": activity.accessibility,
            }
        )

    return {
        "publication": {
            "id": str(publication.id),
            "title": publication.title,
            "starts_at": publication.starts_at,
            "ends_at": publication.ends_at,
            "duration_minutes": publication.duration_minutes,
            "allow_resume": publication.allow_resume,
            "navigation_mode": publication.navigation_mode,
            "autosave_seconds": publication.autosave_seconds,
        },
        "delivery": {
            "id": str(delivery.id),
            "comic_project_id": str(delivery.comic_project_id),
            "release_id": str(release_id) if release_id else None,
            "delivery_mode": delivery.delivery_mode,
            "reader_required": delivery.reader_required,
            "release_answer_key": delivery.release_answer_key,
        },
        "assessment": {
            "student_id": str(actor.user_id),
            "target_id": str(target.id),
            "attempts_used": attempt_count,
            "attempts_allowed": allowed_attempts,
            "can_start": active_session is None
            and attempt_count < allowed_attempts,
            "autosave_sequence": autosave_sequence,
            "session": (
                {
                    "id": str(active_session.id),
                    "status": active_session.status,
                    "expires_at": active_session.expires_at,
                    "remaining_seconds": active_session.remaining_seconds,
                    "accessibility": active_session.accessibility_snapshot,
                }
                if active_session
                else None
            ),
        },
        "teacher_support": {
            "answer_key_released": answer_key_released,
            "updates": [
                {
                    "id": str(event.id),
                    "type": event.event_type.removeprefix("TEACHER_"),
                    "message": event.metadata_payload.get("message"),
                    "activity_id": event.metadata_payload.get(
                        "activity_id"
                    ),
                    "hint_level": event.metadata_payload.get(
                        "hint_level"
                    ),
                    "occurred_at": event.occurred_at,
                }
                for event in teacher_events
            ],
        },
        "state": state_payload,
        "pages": [
            {
                "id": str(page.id),
                "page_number": page.page_number,
                "page_type": page.page_type,
                "title": page.title,
                "background_settings": page.background_settings,
                "accessibility_settings": page.accessibility_settings,
                "content_layers": page.content_layers,
            }
            for page in pages
        ],
        "activities": activity_payloads,
    }


async def save_experience_state(
    session: AsyncSession,
    *,
    actor: ActorContext,
    publication_id: uuid.UUID,
    data: Any,
) -> Any:
    from app.assessment_delivery.enums import SessionStatus
    from app.assessment_delivery.models import AssessmentSession, AssessmentSessionItem

    from . import models

    assessment_session = await session.scalar(
        select(AssessmentSession).where(
            AssessmentSession.organization_id == actor.organization_id,
            AssessmentSession.id == data.assessment_session_id,
            AssessmentSession.publication_id == publication_id,
            AssessmentSession.student_id == actor.user_id,
        )
    )
    if assessment_session is None:
        raise HTTPException(404, {"code": "ASSESSMENT_SESSION_NOT_FOUND"})
    if assessment_session.status not in {
        SessionStatus.IN_PROGRESS.value,
        SessionStatus.PAUSED.value,
        SessionStatus.SUBMITTED.value,
        SessionStatus.UNDER_REVIEW.value,
    }:
        raise HTTPException(409, {"code": "ASSESSMENT_SESSION_NOT_AVAILABLE"})

    total_activity_count = int(
        (
            await session.scalar(
                select(func.count(AssessmentSessionItem.id)).where(
                    AssessmentSessionItem.organization_id
                    == actor.organization_id,
                    AssessmentSessionItem.session_id == assessment_session.id,
                )
            )
        )
        or 0
    )
    answered_count = int(
        (
            await session.scalar(
                select(func.count(AssessmentSessionItem.id)).where(
                    AssessmentSessionItem.organization_id
                    == actor.organization_id,
                    AssessmentSessionItem.session_id == assessment_session.id,
                    AssessmentSessionItem.status == "ANSWERED",
                )
            )
        )
        or 0
    )
    activity_progress = (
        round((answered_count / total_activity_count) * 100, 2)
        if total_activity_count
        else 100.0
    )

    delivery = await session.scalar(
        select(models.HQActivityDeliveryLink).where(
            models.HQActivityDeliveryLink.organization_id
            == actor.organization_id,
            models.HQActivityDeliveryLink.publication_id == publication_id,
        )
    )
    if delivery is None:
        raise HTTPException(404, "Aplicação da HQ não encontrada.")

    state = await session.scalar(
        select(models.HQStudentExperienceState)
        .where(
            models.HQStudentExperienceState.organization_id
            == actor.organization_id,
            models.HQStudentExperienceState.publication_id == publication_id,
            models.HQStudentExperienceState.student_id == actor.user_id,
        )
        .with_for_update()
    )
    release_id = await accessible_published_release_id(
        session,
        actor=actor,
        comic_project_id=delivery.comic_project_id,
    )
    if state is None:
        state = models.HQStudentExperienceState(
            organization_id=actor.organization_id,
            comic_project_id=delivery.comic_project_id,
            publication_id=publication_id,
            student_id=actor.user_id,
            assessment_session_id=assessment_session.id,
            release_id=release_id,
            current_stage="READING" if delivery.reader_required else "ACTIVITY",
            current_page_number=1,
            current_panel_number=1,
            current_activity_index=0,
            reading_progress=0,
            activity_progress=activity_progress,
            answered_count=answered_count,
            total_activity_count=total_activity_count,
            resume_token=secrets.token_urlsafe(48),
            preferences={},
            navigation_state={},
            last_feedback={},
            last_sequence=0,
        )
        session.add(state)
        await session.flush()
    if data.sequence <= state.last_sequence:
        raise HTTPException(
            409,
            {
                "code": "STALE_EXPERIENCE_SEQUENCE",
                "last_sequence": state.last_sequence,
            },
        )

    state.assessment_session_id = assessment_session.id
    state.release_id = release_id
    state.current_page_number = data.current_page_number
    state.current_panel_number = data.current_panel_number
    state.current_activity_index = min(
        data.current_activity_index,
        max(0, total_activity_count - 1),
    )
    state.reading_progress = data.reading_progress
    state.activity_progress = activity_progress
    state.answered_count = answered_count
    state.total_activity_count = total_activity_count
    state.preferences = data.preferences
    state.navigation_state = data.navigation_state
    state.last_feedback = {}
    state.last_sequence = data.sequence
    state.current_stage = next_stage(
        reading_progress=data.reading_progress,
        activity_progress=activity_progress,
        reader_required=delivery.reader_required,
    )
    if (
        state.current_stage == "COMPLETED"
        and assessment_session.status
        not in {
            SessionStatus.SUBMITTED.value,
            SessionStatus.UNDER_REVIEW.value,
        }
    ):
        state.current_stage = "ACTIVITY"
    if state.current_stage == "COMPLETED" and state.completed_at is None:
        state.completed_at = datetime.now(UTC)
    await session.flush()
    return state, delivery
