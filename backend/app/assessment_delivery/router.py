from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment_hub import models as hub_models
from app.assessment_hub.enums import AttemptStatus
from app.assessment_hub.services.scoring import (
    apply_review_policy,
    feedback_message,
    score_response,
)
from app.assessment_review.services import ensure_review_assignment

from . import audit, models, repositories
from .access import resolve_student_target, target_window_is_open
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import PublicationStatus, SessionStatus
from .policies import (
    calculate_duration_seconds,
    calculate_expiration,
    can_navigate,
    classify_integrity,
    deterministic_item_order,
    effective_publication_status,
    monitoring_progress,
    response_checksum,
    validate_transition,
)
from .schemas import (
    AccommodationCreate,
    AccommodationRead,
    AutosaveCreate,
    AutosaveRead,
    AvailabilityRead,
    MonitoringSummary,
    NavigationRequest,
    PublicationCreate,
    PublicationRead,
    SessionDetail,
    SessionEventCreate,
    SessionItemRead,
    SessionRead,
    SessionStart,
    TargetCreate,
    TargetRead,
    TeacherAction,
)

router = APIRouter(prefix="/assessment-delivery", tags=["assessment-delivery"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN", "PLATFORM_ADMIN", "ORG_ADMIN"}
TEACHER_ROLES = ADMIN_ROLES | {"TEACHER", "PROFESSOR", "COORDINATOR"}
STUDENT_ROLES = {"STUDENT", "LEARNER", "MEMBER", "ALUNO"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    if not actor.roles.intersection(allowed):
        raise HTTPException(status_code=403, detail={"code": "ASSESSMENT_DELIVERY_ACCESS_DENIED"})


def require_student_or_staff(actor: ActorContext, student_id: uuid.UUID) -> None:
    if actor.roles.intersection(TEACHER_ROLES):
        return
    if actor.roles.intersection(STUDENT_ROLES) and str(actor.user_id) == str(student_id):
        return
    raise HTTPException(status_code=403, detail={"code": "ASSESSMENT_SESSION_ACCESS_DENIED"})


async def get_publication(session: AsyncSession, actor: ActorContext, publication_id: uuid.UUID) -> models.AssessmentPublication:
    entity = await repositories.get_for_organization(
        session, models.AssessmentPublication, actor.organization_id, publication_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_PUBLICATION_NOT_FOUND"})
    return entity


async def get_session(session: AsyncSession, actor: ActorContext, session_id: uuid.UUID) -> models.AssessmentSession:
    entity = await repositories.get_for_organization(
        session, models.AssessmentSession, actor.organization_id, session_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_SESSION_NOT_FOUND"})
    return entity


async def add_event(
    session: AsyncSession,
    entity: models.AssessmentSession,
    event_type: str,
    *,
    actor_user_id: uuid.UUID | None = None,
    severity: str = "INFO",
    source: str = "SERVER",
    description: str | None = None,
    metadata: dict | None = None,
    occurred_at: datetime | None = None,
    client_sequence: int | None = None,
) -> models.AssessmentSessionEvent:
    event = models.AssessmentSessionEvent(
        organization_id=entity.organization_id,
        session_id=entity.id,
        event_type=event_type,
        severity=severity,
        source=source,
        client_sequence=client_sequence,
        occurred_at=occurred_at or datetime.now(UTC),
        actor_user_id=actor_user_id,
        metadata_payload=metadata or {},
        description=description,
    )
    session.add(event)
    return event


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "15.2", "module": "assessment-delivery"}


@router.post("/publications", response_model=PublicationRead, status_code=201)
async def create_publication(
    payload: PublicationCreate, session: SessionDep, actor: ActorDep
) -> models.AssessmentPublication:
    require_role(actor, TEACHER_ROLES)
    source_model = (
        hub_models.AssessmentBlueprint
        if payload.source_type.value == "BLUEPRINT"
        else hub_models.ExternalInstrument
    )
    source = await repositories.get_for_organization(session, source_model, actor.organization_id, payload.source_id)
    if not source:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_SOURCE_NOT_FOUND"})
    version_ids = [item.question_version_id for item in payload.item_snapshot]
    versions = await session.execute(
        select(hub_models.QuestionVersion.id).where(
            hub_models.QuestionVersion.organization_id == actor.organization_id,
            hub_models.QuestionVersion.id.in_(version_ids),
        )
    )
    if len(set(versions.scalars().all())) != len(set(version_ids)):
        raise HTTPException(status_code=422, detail={"code": "QUESTION_VERSION_NOT_FOUND"})
    entity = models.AssessmentPublication(
        organization_id=actor.organization_id,
        **payload.model_dump(exclude={"item_snapshot"}),
        item_snapshot=[item.model_dump(mode="json") for item in payload.item_snapshot],
        status=PublicationStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    audit.record("assessment_delivery.publication_created", publication_id=str(entity.id))
    return entity


@router.get("/publications", response_model=list[PublicationRead])
async def list_publications(
    session: SessionDep,
    actor: ActorDep,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[models.AssessmentPublication]:
    require_role(actor, TEACHER_ROLES)
    statement = select(models.AssessmentPublication).where(
        models.AssessmentPublication.organization_id == actor.organization_id
    )
    if status_filter:
        statement = statement.where(models.AssessmentPublication.status == status_filter.upper())
    result = await session.execute(statement.order_by(models.AssessmentPublication.created_at.desc()))
    return list(result.scalars().all())


@router.post("/publications/{publication_id}/publish", response_model=PublicationRead)
async def publish_publication(
    publication_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.AssessmentPublication:
    require_role(actor, TEACHER_ROLES)
    entity = await get_publication(session, actor, publication_id)
    if not entity.item_snapshot:
        raise HTTPException(status_code=422, detail={"code": "PUBLICATION_HAS_NO_ITEMS"})
    entity.status = PublicationStatus.PUBLISHED.value
    entity.published_at = datetime.now(UTC)
    entity.published_by_user_id = actor.user_id
    await session.commit()
    audit.record("assessment_delivery.publication_published", publication_id=str(entity.id))
    return entity


@router.post("/publications/{publication_id}/close", response_model=PublicationRead)
async def close_publication(
    publication_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.AssessmentPublication:
    require_role(actor, TEACHER_ROLES)
    entity = await get_publication(session, actor, publication_id)
    entity.status = PublicationStatus.CLOSED.value
    entity.closed_at = datetime.now(UTC)
    await session.commit()
    return entity


@router.post("/publications/{publication_id}/targets", response_model=TargetRead, status_code=201)
async def create_target(
    publication_id: uuid.UUID, payload: TargetCreate, session: SessionDep, actor: ActorDep
) -> models.AssessmentTarget:
    require_role(actor, TEACHER_ROLES)
    await get_publication(session, actor, publication_id)
    entity = models.AssessmentTarget(
        organization_id=actor.organization_id,
        publication_id=publication_id,
        **payload.model_dump(),
        assigned_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/publications/{publication_id}/accommodations", response_model=AccommodationRead, status_code=201)
async def create_accommodation(
    publication_id: uuid.UUID, payload: AccommodationCreate, session: SessionDep, actor: ActorDep
) -> models.AssessmentAccommodation:
    require_role(actor, TEACHER_ROLES)
    await get_publication(session, actor, publication_id)
    entity = models.AssessmentAccommodation(
        organization_id=actor.organization_id,
        publication_id=publication_id,
        **payload.model_dump(),
        approved_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.get("/students/{student_id}/available", response_model=list[AvailabilityRead])
async def available_assessments(
    student_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    classroom_id: uuid.UUID | None = None,
) -> list[AvailabilityRead]:
    require_student_or_staff(actor, student_id)
    targets_result = await session.execute(
        select(models.AssessmentTarget).where(
            models.AssessmentTarget.organization_id == actor.organization_id,
            models.AssessmentTarget.status == "ACTIVE",
        )
    )
    targets_by_publication: dict[uuid.UUID, models.AssessmentTarget] = {}
    for candidate in targets_result.scalars().all():
        if candidate.publication_id in targets_by_publication:
            continue
        eligible = await resolve_student_target(
            session,
            organization_id=actor.organization_id,
            publication_id=candidate.publication_id,
            student_id=student_id,
            requested_target_id=candidate.id,
        )
        if eligible is not None:
            targets_by_publication[candidate.publication_id] = eligible
    targets = list(targets_by_publication.values())
    publications: list[AvailabilityRead] = []
    now = datetime.now(UTC)
    for target in targets:
        publication = await repositories.get_for_organization(
            session, models.AssessmentPublication, actor.organization_id, target.publication_id
        )
        if not publication:
            continue
        effective = effective_publication_status(publication.status, publication.starts_at, publication.ends_at, now)
        count = await session.execute(
            select(func.count(models.AssessmentSession.id)).where(
                models.AssessmentSession.organization_id == actor.organization_id,
                models.AssessmentSession.publication_id == publication.id,
                models.AssessmentSession.student_id == student_id,
                models.AssessmentSession.status != SessionStatus.CANCELLED.value,
            )
        )
        used = int(count.scalar_one())
        allowed = publication.max_attempts + target.extra_attempts
        target_open = target_window_is_open(target, now=now)
        can_start = effective == "OPEN" and target_open and used < allowed
        reason = None
        if effective != "OPEN":
            reason = effective
        elif not target_open:
            reason = "TARGET_WINDOW_CLOSED"
        elif used >= allowed:
            reason = "ATTEMPT_LIMIT_REACHED"
        publications.append(
            AvailabilityRead(
                publication=PublicationRead.model_validate(publication),
                effective_status=effective,
                attempts_used=used,
                attempts_allowed=allowed,
                can_start=can_start,
                reason=reason,
            )
        )
    return publications


@router.post("/sessions/start", response_model=SessionDetail, status_code=201)
async def start_session(payload: SessionStart, session: SessionDep, actor: ActorDep) -> SessionDetail:
    require_student_or_staff(actor, payload.student_id)
    publication = await get_publication(session, actor, payload.publication_id)
    now = datetime.now(UTC)
    if effective_publication_status(publication.status, publication.starts_at, publication.ends_at, now) != "OPEN":
        raise HTTPException(status_code=409, detail={"code": "ASSESSMENT_NOT_OPEN"})
    target = await resolve_student_target(
        session,
        organization_id=actor.organization_id,
        publication_id=publication.id,
        student_id=payload.student_id,
        requested_target_id=payload.target_id,
        now=now,
    )
    if target is None:
        code = (
            "ASSESSMENT_TARGET_NOT_ELIGIBLE"
            if payload.target_id
            else "ASSESSMENT_TARGET_REQUIRED"
        )
        raise HTTPException(status_code=403, detail={"code": code})
    count_result = await session.execute(
        select(func.count(models.AssessmentSession.id)).where(
            models.AssessmentSession.organization_id == actor.organization_id,
            models.AssessmentSession.publication_id == publication.id,
            models.AssessmentSession.student_id == payload.student_id,
            models.AssessmentSession.status != SessionStatus.CANCELLED.value,
        )
    )
    session_count = int(count_result.scalar_one())
    allowed_attempts = publication.max_attempts + (target.extra_attempts if target else 0)
    if session_count >= allowed_attempts:
        raise HTTPException(status_code=409, detail={"code": "ATTEMPT_LIMIT_REACHED"})
    accommodation_result = await session.execute(
        select(models.AssessmentAccommodation).where(
            models.AssessmentAccommodation.organization_id == actor.organization_id,
            models.AssessmentAccommodation.publication_id == publication.id,
            models.AssessmentAccommodation.student_id == payload.student_id,
            models.AssessmentAccommodation.status == "ACTIVE",
        )
    )
    accommodation = accommodation_result.scalar_one_or_none()
    duration_seconds = calculate_duration_seconds(
        publication.duration_minutes,
        target_minutes=target.custom_duration_minutes if target else None,
        extra_time_percent=accommodation.extra_time_percent if accommodation else 0,
        extra_time_minutes=accommodation.extra_time_minutes if accommodation else 0,
    )
    attempt = hub_models.AssessmentAttempt(
        organization_id=actor.organization_id,
        student_id=payload.student_id,
        classroom_id=target.target_id if target and target.target_type == "CLASSROOM" else None,
        blueprint_id=publication.source_id if publication.source_type == "BLUEPRINT" else None,
        external_instrument_id=publication.source_id if publication.source_type == "EXTERNAL_INSTRUMENT" else None,
        attempt_number=session_count + 1,
        status=AttemptStatus.IN_PROGRESS.value,
        question_snapshot=publication.item_snapshot,
        started_at=now,
        metadata_payload={"publication_id": str(publication.id), "delivery_sprint": "15.2"},
    )
    session.add(attempt)
    await session.flush()
    accessibility = {
        "accessible_version_required": bool(accommodation and accommodation.accessible_version_required),
        "screen_reader_mode": bool(accommodation and accommodation.screen_reader_mode),
        "high_contrast": bool(accommodation and accommodation.high_contrast),
        "reduced_motion": bool(accommodation and accommodation.reduced_motion),
        "keyboard_only": bool(accommodation and accommodation.keyboard_only),
        "simplified_language": bool(accommodation and accommodation.simplified_language),
        "custom_settings": accommodation.custom_settings if accommodation else {},
    }
    entity = models.AssessmentSession(
        organization_id=actor.organization_id,
        publication_id=publication.id,
        target_id=target.id if target else None,
        student_id=payload.student_id,
        assessment_hub_attempt_id=attempt.id,
        session_number=session_count + 1,
        status=SessionStatus.IN_PROGRESS.value,
        started_at=now,
        last_activity_at=now,
        expires_at=calculate_expiration(now, duration_seconds),
        remaining_seconds=duration_seconds,
        delivery_snapshot={
            "navigation_mode": publication.navigation_mode,
            "shuffle_questions": publication.shuffle_questions,
            "shuffle_options": publication.shuffle_options,
            "allow_resume": publication.allow_resume,
            "autosave_seconds": publication.autosave_seconds,
            "rules": publication.delivery_rules,
        },
        accessibility_snapshot=accessibility,
        device_context=payload.device_context,
    )
    session.add(entity)
    await session.flush()
    ordered = deterministic_item_order(
        publication.item_snapshot,
        seed=f"{publication.id}:{payload.student_id}:{entity.session_number}",
        shuffle=publication.shuffle_questions,
    )
    session_items: list[models.AssessmentSessionItem] = []
    for display_position, item in enumerate(ordered):
        session_item = models.AssessmentSessionItem(
            organization_id=actor.organization_id,
            session_id=entity.id,
            question_version_id=uuid.UUID(str(item["question_version_id"])),
            position=display_position,
            original_position=int(item.get("position", display_position)),
            option_order=[],
        )
        session.add(session_item)
        session_items.append(session_item)
    await add_event(session, entity, "SESSION_STARTED", actor_user_id=actor.user_id)
    await session.commit()
    for item in session_items:
        await session.refresh(item)
    await session.refresh(entity)
    return SessionDetail(
        session=SessionRead.model_validate(entity),
        items=[SessionItemRead.model_validate(item) for item in session_items],
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def read_session(session_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> SessionDetail:
    entity = await get_session(session, actor, session_id)
    require_student_or_staff(actor, entity.student_id)
    items_result = await session.execute(
        select(models.AssessmentSessionItem).where(
            models.AssessmentSessionItem.organization_id == actor.organization_id,
            models.AssessmentSessionItem.session_id == entity.id,
        ).order_by(models.AssessmentSessionItem.position)
    )
    return SessionDetail(
        session=SessionRead.model_validate(entity),
        items=[SessionItemRead.model_validate(item) for item in items_result.scalars().all()],
    )


@router.post("/sessions/{session_id}/autosaves", response_model=AutosaveRead, status_code=201)
async def autosave_response(
    session_id: uuid.UUID, payload: AutosaveCreate, session: SessionDep, actor: ActorDep
) -> models.AssessmentAutosave:
    entity = await get_session(session, actor, session_id)
    require_student_or_staff(actor, entity.student_id)
    if entity.status != SessionStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=409, detail={"code": "SESSION_NOT_ACTIVE"})
    now = datetime.now(UTC)
    if entity.expires_at and now > entity.expires_at:
        entity.status = SessionStatus.TIMED_OUT.value
        await add_event(session, entity, "SESSION_TIMED_OUT", severity="WARNING")
        await session.commit()
        raise HTTPException(status_code=409, detail={"code": "SESSION_TIMED_OUT"})
    item = await repositories.get_for_organization(
        session, models.AssessmentSessionItem, actor.organization_id, payload.session_item_id
    )
    if not item or item.session_id != entity.id:
        raise HTTPException(status_code=404, detail={"code": "SESSION_ITEM_NOT_FOUND"})
    max_sequence_result = await session.execute(
        select(func.max(models.AssessmentAutosave.sequence_number)).where(
            models.AssessmentAutosave.organization_id == actor.organization_id,
            models.AssessmentAutosave.session_id == entity.id,
        )
    )
    maximum_sequence = int(max_sequence_result.scalar_one_or_none() or 0)
    if payload.sequence_number <= maximum_sequence:
        raise HTTPException(status_code=409, detail={"code": "AUTOSAVE_SEQUENCE_OUT_OF_ORDER"})
    checksum = payload.checksum or response_checksum(payload.response)
    if payload.checksum and payload.checksum != response_checksum(payload.response):
        raise HTTPException(status_code=422, detail={"code": "AUTOSAVE_CHECKSUM_INVALID"})
    autosave = models.AssessmentAutosave(
        organization_id=actor.organization_id,
        session_id=entity.id,
        session_item_id=item.id,
        sequence_number=payload.sequence_number,
        response_payload=payload.response,
        client_timestamp=payload.client_timestamp,
        checksum=checksum,
    )
    item.status = "ANSWERED"
    item.answered_at = now
    entity.last_activity_at = now
    await repositories.add_and_refresh(session, autosave)
    await add_event(session, entity, "AUTOSAVE_ACCEPTED", actor_user_id=actor.user_id, metadata={"sequence": payload.sequence_number})
    await session.commit()
    return autosave


@router.post("/sessions/{session_id}/navigate", response_model=SessionRead)
async def navigate_session(
    session_id: uuid.UUID, payload: NavigationRequest, session: SessionDep, actor: ActorDep
) -> models.AssessmentSession:
    entity = await get_session(session, actor, session_id)
    require_student_or_staff(actor, entity.student_id)
    item_count_result = await session.execute(
        select(func.count(models.AssessmentSessionItem.id)).where(
            models.AssessmentSessionItem.organization_id == actor.organization_id,
            models.AssessmentSessionItem.session_id == entity.id,
        )
    )
    item_count = int(item_count_result.scalar_one())
    if payload.target_position >= item_count:
        raise HTTPException(status_code=422, detail={"code": "TARGET_POSITION_OUT_OF_RANGE"})
    answered_result = await session.execute(
        select(models.AssessmentSessionItem.position).where(
            models.AssessmentSessionItem.organization_id == actor.organization_id,
            models.AssessmentSessionItem.session_id == entity.id,
            models.AssessmentSessionItem.status == "ANSWERED",
        )
    )
    answered_positions = set(answered_result.scalars().all())
    mode = str(entity.delivery_snapshot.get("navigation_mode", "FREE"))
    if not can_navigate(mode, entity.current_item_position, payload.target_position, answered_positions):
        raise HTTPException(status_code=409, detail={"code": "NAVIGATION_NOT_ALLOWED"})
    if payload.flag_current_for_review:
        current_result = await session.execute(
            select(models.AssessmentSessionItem).where(
                models.AssessmentSessionItem.organization_id == actor.organization_id,
                models.AssessmentSessionItem.session_id == entity.id,
                models.AssessmentSessionItem.position == entity.current_item_position,
            )
        )
        current = current_result.scalar_one_or_none()
        if current:
            current.flagged_for_review = True
    entity.current_item_position = payload.target_position
    entity.last_activity_at = datetime.now(UTC)
    await add_event(session, entity, "NAVIGATION", actor_user_id=actor.user_id, metadata={"target_position": payload.target_position})
    await session.commit()
    return entity


@router.post("/sessions/{session_id}/events", status_code=201)
async def register_event(
    session_id: uuid.UUID, payload: SessionEventCreate, session: SessionDep, actor: ActorDep
) -> dict[str, str]:
    entity = await get_session(session, actor, session_id)
    require_student_or_staff(actor, entity.student_id)
    if payload.event_type == "FOCUS_LOST":
        entity.focus_loss_count += 1
    if payload.event_type == "RECONNECTED":
        entity.reconnect_count += 1
    severe = 1 if payload.severity == "REVIEW" else 0
    entity.integrity_status = classify_integrity(entity.focus_loss_count, entity.reconnect_count, severe)
    await add_event(
        session,
        entity,
        payload.event_type,
        actor_user_id=actor.user_id,
        severity=payload.severity,
        source=payload.source,
        description=payload.description,
        metadata=payload.metadata,
        occurred_at=payload.occurred_at,
        client_sequence=payload.client_sequence,
    )
    await session.commit()
    return {"status": "registered", "integrity_status": entity.integrity_status}


@router.post("/sessions/{session_id}/submit", response_model=SessionRead)
async def submit_session(
    session_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> models.AssessmentSession:
    entity = await get_session(session, actor, session_id)
    require_student_or_staff(actor, entity.student_id)
    if entity.status != SessionStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=409, detail={"code": "SESSION_NOT_ACTIVE"})
    publication = await repositories.get_for_organization(
        session,
        models.AssessmentPublication,
        actor.organization_id,
        entity.publication_id,
    )
    if publication is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "PUBLICATION_NOT_FOUND_FOR_SESSION"},
        )
    items_result = await session.execute(
        select(models.AssessmentSessionItem).where(
            models.AssessmentSessionItem.organization_id == actor.organization_id,
            models.AssessmentSessionItem.session_id == entity.id,
        ).order_by(models.AssessmentSessionItem.position)
    )
    items = list(items_result.scalars().all())
    total = 0.0
    maximum = 0.0
    requires_review = False
    now = datetime.now(UTC)
    for item in items:
        version = await repositories.get_for_organization(
            session, hub_models.QuestionVersion, actor.organization_id, item.question_version_id
        )
        if not version:
            continue
        latest_result = await session.execute(
            select(models.AssessmentAutosave).where(
                models.AssessmentAutosave.organization_id == actor.organization_id,
                models.AssessmentAutosave.session_id == entity.id,
                models.AssessmentAutosave.session_item_id == item.id,
            ).order_by(models.AssessmentAutosave.sequence_number.desc()).limit(1)
        )
        latest = latest_result.scalar_one_or_none()
        response_payload = latest.response_payload if latest else {}
        scored = score_response(
            version.question_type,
            version.correct_answer,
            response_payload,
            version.max_score,
        )
        scored = apply_review_policy(
            scored,
            version.metadata_payload.get("review_correction_mode"),
        )
        response_result = await session.execute(
            select(hub_models.AssessmentResponse).where(
                hub_models.AssessmentResponse.organization_id == actor.organization_id,
                hub_models.AssessmentResponse.attempt_id == entity.assessment_hub_attempt_id,
                hub_models.AssessmentResponse.question_version_id == version.id,
            )
        )
        response = response_result.scalar_one_or_none()
        if not response:
            response = hub_models.AssessmentResponse(
                organization_id=actor.organization_id,
                attempt_id=entity.assessment_hub_attempt_id,
                question_version_id=version.id,
                response_payload=response_payload,
                maximum_score=scored.max_score,
            )
            session.add(response)
        response.response_payload = response_payload
        response.score = scored.score
        response.maximum_score = scored.max_score
        response.is_correct = scored.is_correct
        response.correction_type = scored.correction_type
        response.feedback = feedback_message(
            scored,
            version.metadata_payload.get("review_feedback_templates"),
        )
        response.requires_human_review = scored.requires_human_review
        response.corrected_at = None if scored.requires_human_review else now
        if scored.requires_human_review:
            await session.flush()
            await ensure_review_assignment(
                session,
                organization_id=actor.organization_id,
                attempt_id=entity.assessment_hub_attempt_id,
                response_id=response.id,
                question_version_id=version.id,
                reviewer_user_id=publication.created_by_user_id,
                assigned_by_user_id=publication.created_by_user_id,
                initiated_by_user_id=actor.user_id,
                rubric_version_id=version.metadata_payload.get(
                    "review_rubric_version_id"
                ),
                context_snapshot={
                    "source": "ASSESSMENT_DELIVERY_SUBMISSION",
                    "publication_id": str(publication.id),
                    "session_id": str(entity.id),
                    "student_id": str(entity.student_id),
                },
            )
        total += float(scored.score or 0)
        maximum += float(scored.max_score)
        requires_review = requires_review or scored.requires_human_review
    attempt = await repositories.get_for_organization(
        session, hub_models.AssessmentAttempt, actor.organization_id, entity.assessment_hub_attempt_id
    )
    if attempt:
        attempt.status = AttemptStatus.UNDER_REVIEW.value if requires_review else AttemptStatus.SUBMITTED.value
        attempt.submitted_at = now
        attempt.total_score = total
        attempt.maximum_score = maximum
        attempt.percentage_score = round((total / maximum) * 100, 4) if maximum else 0.0
        attempt.requires_human_review = requires_review
    entity.status = SessionStatus.UNDER_REVIEW.value if requires_review else SessionStatus.SUBMITTED.value
    entity.submitted_at = now
    entity.last_activity_at = now
    await add_event(session, entity, "SESSION_SUBMITTED", actor_user_id=actor.user_id)
    await session.commit()
    return entity


@router.post("/sessions/{session_id}/actions", response_model=SessionRead)
async def teacher_action(
    session_id: uuid.UUID, payload: TeacherAction, session: SessionDep, actor: ActorDep
) -> models.AssessmentSession:
    require_role(actor, TEACHER_ROLES)
    entity = await get_session(session, actor, session_id)
    now = datetime.now(UTC)
    if payload.action == "PAUSE":
        validate_transition(entity.status, SessionStatus.PAUSED.value)
        entity.status = SessionStatus.PAUSED.value
        entity.paused_at = now
    elif payload.action == "RESUME":
        validate_transition(entity.status, SessionStatus.IN_PROGRESS.value)
        if not entity.delivery_snapshot.get("allow_resume", True):
            raise HTTPException(status_code=409, detail={"code": "RESUME_NOT_ALLOWED"})
        entity.status = SessionStatus.IN_PROGRESS.value
        entity.resume_count += 1
        entity.paused_at = None
        entity.expires_at = (entity.expires_at or now) + timedelta(minutes=payload.extra_minutes)
    elif payload.action == "EXTEND":
        if payload.extra_minutes <= 0:
            raise HTTPException(status_code=422, detail={"code": "EXTRA_MINUTES_REQUIRED"})
        entity.expires_at = (entity.expires_at or now) + timedelta(minutes=payload.extra_minutes)
        entity.remaining_seconds += payload.extra_minutes * 60
    elif payload.action == "CANCEL":
        validate_transition(entity.status, SessionStatus.CANCELLED.value)
        entity.status = SessionStatus.CANCELLED.value
    elif payload.action == "REOPEN":
        validate_transition(entity.status, SessionStatus.IN_PROGRESS.value)
        entity.status = SessionStatus.IN_PROGRESS.value
        entity.resume_count += 1
        entity.expires_at = now + timedelta(minutes=max(1, payload.extra_minutes or 30))
    entity.last_activity_at = now
    await add_event(
        session,
        entity,
        f"TEACHER_{payload.action}",
        actor_user_id=actor.user_id,
        source="TEACHER",
        description=payload.reason,
        metadata={"extra_minutes": payload.extra_minutes},
    )
    await session.commit()
    return entity


@router.get("/monitor/publications/{publication_id}", response_model=MonitoringSummary)
async def monitor_publication(
    publication_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> MonitoringSummary:
    require_role(actor, TEACHER_ROLES)
    await get_publication(session, actor, publication_id)
    result = await session.execute(
        select(models.AssessmentSession).where(
            models.AssessmentSession.organization_id == actor.organization_id,
            models.AssessmentSession.publication_id == publication_id,
        )
    )
    sessions = list(result.scalars().all())
    counts = Counter(item.status for item in sessions)
    positions: list[int] = []
    item_counts: list[int] = []
    for item in sessions:
        count_result = await session.execute(
            select(func.count(models.AssessmentSessionItem.id)).where(
                models.AssessmentSessionItem.organization_id == actor.organization_id,
                models.AssessmentSessionItem.session_id == item.id,
            )
        )
        positions.append(item.current_item_position)
        item_counts.append(int(count_result.scalar_one()))
    return MonitoringSummary(
        publication_id=publication_id,
        total_sessions=len(sessions),
        status_counts=dict(counts),
        active_sessions=counts.get(SessionStatus.IN_PROGRESS.value, 0),
        submitted_sessions=counts.get(SessionStatus.SUBMITTED.value, 0) + counts.get(SessionStatus.UNDER_REVIEW.value, 0),
        attention_sessions=sum(1 for item in sessions if item.integrity_status != "NORMAL"),
        average_progress=monitoring_progress(positions, item_counts),
        last_updated_at=datetime.now(UTC),
    )
