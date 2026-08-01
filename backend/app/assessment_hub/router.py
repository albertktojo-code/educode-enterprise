from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, repositories
from .audit import emit_audit_event
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import AttemptStatus, CorrectionType, RecordStatus
from .schemas import (
    AssemblySimulationInput,
    AssemblySimulationResult,
    AttemptCreate,
    AttemptRead,
    BlueprintCreate,
    BlueprintRead,
    DimensionSummaryInput,
    DimensionSummaryResult,
    ExternalInstrumentCreate,
    ExternalInstrumentRead,
    InstrumentDimensionCreate,
    InstrumentDimensionRead,
    ItemAnalyticsInput,
    ItemAnalyticsResult,
    QuestionCreate,
    QuestionRead,
    QuestionVersionCreate,
    QuestionVersionRead,
    ResponseCreate,
    ResponseRead,
    ReviewCreate,
    ScoreRequest,
    ScoreResult,
    SkillLinkCreate,
    SkillLinkRead,
)
from .services import assemble_assessment, calculate_item_analytics, score_response, summarize_dimensions

router = APIRouter(prefix="/assessment-hub", tags=["Assessment Hub — Sprint 15"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
TEACHER_ROLES = ADMIN_ROLES | {"TEACHER"}


def require_role(actor: ActorContext, roles: set[str]) -> None:
    if not actor.roles.intersection(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ASSESSMENT_ACCESS_DENIED", "message": "Papel sem permissao."},
        )


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "assessment-hub", "sprint": "15"}


@router.post("/questions", response_model=QuestionRead, status_code=201)
async def create_question(payload: QuestionCreate, session: SessionDep, actor: ActorDep) -> models.QuestionItem:
    require_role(actor, TEACHER_ROLES)
    duplicate = await session.execute(
        select(models.QuestionItem.id).where(
            models.QuestionItem.organization_id == actor.organization_id,
            models.QuestionItem.code == payload.code,
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"code": "QUESTION_CODE_ALREADY_EXISTS"})
    entity = models.QuestionItem(
        organization_id=actor.organization_id,
        code=payload.code,
        title=payload.title,
        subject=payload.subject,
        school_year=payload.school_year,
        source_type=payload.source_type,
        status=RecordStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event("assessment.question.created", organization_id=actor.organization_id, user_id=actor.user_id, resource_type="question", resource_id=entity.id)
    return entity


@router.get("/questions", response_model=list[QuestionRead])
async def list_questions(
    session: SessionDep,
    actor: ActorDep,
    subject: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[models.QuestionItem]:
    require_role(actor, TEACHER_ROLES)
    statement = select(models.QuestionItem).where(models.QuestionItem.organization_id == actor.organization_id)
    if subject:
        statement = statement.where(models.QuestionItem.subject == subject)
    if status_filter:
        statement = statement.where(models.QuestionItem.status == status_filter.upper())
    result = await session.execute(statement.order_by(models.QuestionItem.created_at.desc()).limit(limit))
    return list(result.scalars().all())


@router.post("/questions/{question_id}/versions", response_model=QuestionVersionRead, status_code=201)
async def create_question_version(
    question_id: uuid.UUID, payload: QuestionVersionCreate, session: SessionDep, actor: ActorDep
) -> models.QuestionVersion:
    require_role(actor, TEACHER_ROLES)
    question = await repositories.get_for_organization(session, models.QuestionItem, actor.organization_id, question_id)
    if not question:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_NOT_FOUND"})
    count = await session.execute(
        select(func.max(models.QuestionVersion.version)).where(
            models.QuestionVersion.organization_id == actor.organization_id,
            models.QuestionVersion.question_id == question_id,
        )
    )
    version = int(count.scalar_one_or_none() or 0) + 1
    entity = models.QuestionVersion(
        organization_id=actor.organization_id,
        question_id=question_id,
        version=version,
        question_type=payload.question_type.value,
        statement=payload.statement,
        options=payload.options,
        correct_answer=payload.correct_answer,
        explanation=payload.explanation,
        rubric=payload.rubric,
        predicted_difficulty=payload.predicted_difficulty,
        max_score=payload.max_score,
        accessibility=payload.accessibility,
        metadata_payload=payload.metadata,
        status=RecordStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
    )
    question.current_version = version
    question.updated_by_user_id = actor.user_id
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/questions/{question_id}/versions/{version_id}/publish", response_model=QuestionVersionRead)
async def publish_question_version(
    question_id: uuid.UUID, version_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.QuestionVersion:
    require_role(actor, TEACHER_ROLES)
    entity = await repositories.get_for_organization(session, models.QuestionVersion, actor.organization_id, version_id)
    if not entity or entity.question_id != question_id:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_VERSION_NOT_FOUND"})
    entity.status = RecordStatus.PUBLISHED.value
    entity.published_at = datetime.now(UTC)
    entity.published_by_user_id = actor.user_id
    question = await repositories.get_for_organization(session, models.QuestionItem, actor.organization_id, question_id)
    if question:
        question.status = RecordStatus.PUBLISHED.value
    await session.commit()
    return entity


@router.post("/question-versions/{version_id}/skills", response_model=SkillLinkRead, status_code=201)
async def link_skill(
    version_id: uuid.UUID, payload: SkillLinkCreate, session: SessionDep, actor: ActorDep
) -> models.QuestionSkillLink:
    require_role(actor, TEACHER_ROLES)
    version = await repositories.get_for_organization(session, models.QuestionVersion, actor.organization_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_VERSION_NOT_FOUND"})
    entity = models.QuestionSkillLink(
        organization_id=actor.organization_id,
        question_version_id=version_id,
        **payload.model_dump(),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/blueprints", response_model=BlueprintRead, status_code=201)
async def create_blueprint(payload: BlueprintCreate, session: SessionDep, actor: ActorDep) -> models.AssessmentBlueprint:
    require_role(actor, TEACHER_ROLES)
    entity = models.AssessmentBlueprint(
        organization_id=actor.organization_id,
        **payload.model_dump(),
        status=RecordStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.get("/blueprints", response_model=list[BlueprintRead])
async def list_blueprints(session: SessionDep, actor: ActorDep) -> list[models.AssessmentBlueprint]:
    require_role(actor, TEACHER_ROLES)
    return await repositories.list_for_organization(
        session, models.AssessmentBlueprint, actor.organization_id, order_by=models.AssessmentBlueprint.created_at.desc()
    )


@router.post("/blueprints/assemble/simulate", response_model=AssemblySimulationResult)
async def simulate_assembly(payload: AssemblySimulationInput, actor: ActorDep) -> AssemblySimulationResult:
    require_role(actor, TEACHER_ROLES)
    return assemble_assessment(payload)


@router.post("/external-instruments", response_model=ExternalInstrumentRead, status_code=201)
async def create_external_instrument(
    payload: ExternalInstrumentCreate, session: SessionDep, actor: ActorDep
) -> models.ExternalInstrument:
    require_role(actor, ADMIN_ROLES)
    entity = models.ExternalInstrument(
        organization_id=actor.organization_id,
        **payload.model_dump(mode="json"),
        status=RecordStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.get("/external-instruments", response_model=list[ExternalInstrumentRead])
async def list_external_instruments(session: SessionDep, actor: ActorDep) -> list[models.ExternalInstrument]:
    require_role(actor, TEACHER_ROLES)
    return await repositories.list_for_organization(
        session, models.ExternalInstrument, actor.organization_id, order_by=models.ExternalInstrument.created_at.desc()
    )


@router.post("/external-instruments/{instrument_id}/dimensions", response_model=InstrumentDimensionRead, status_code=201)
async def create_dimension(
    instrument_id: uuid.UUID, payload: InstrumentDimensionCreate, session: SessionDep, actor: ActorDep
) -> models.InstrumentDimension:
    require_role(actor, ADMIN_ROLES)
    instrument = await repositories.get_for_organization(session, models.ExternalInstrument, actor.organization_id, instrument_id)
    if not instrument:
        raise HTTPException(status_code=404, detail={"code": "EXTERNAL_INSTRUMENT_NOT_FOUND"})
    entity = models.InstrumentDimension(
        organization_id=actor.organization_id,
        instrument_id=instrument_id,
        **payload.model_dump(),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/attempts", response_model=AttemptRead, status_code=201)
async def create_attempt(payload: AttemptCreate, session: SessionDep, actor: ActorDep) -> models.AssessmentAttempt:
    require_role(actor, TEACHER_ROLES)
    entity = models.AssessmentAttempt(
        organization_id=actor.organization_id,
        student_id=payload.student_id,
        classroom_id=payload.classroom_id,
        blueprint_id=payload.blueprint_id,
        external_instrument_id=payload.external_instrument_id,
        attempt_number=payload.attempt_number,
        question_snapshot=payload.question_snapshot,
        metadata_payload=payload.metadata,
        status=AttemptStatus.CREATED.value,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/attempts/{attempt_id}/responses", response_model=ResponseRead, status_code=201)
async def create_response(
    attempt_id: uuid.UUID, payload: ResponseCreate, session: SessionDep, actor: ActorDep
) -> models.AssessmentResponse:
    require_role(actor, TEACHER_ROLES)
    attempt = await repositories.get_for_organization(session, models.AssessmentAttempt, actor.organization_id, attempt_id)
    version = await repositories.get_for_organization(session, models.QuestionVersion, actor.organization_id, payload.question_version_id)
    if not attempt:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_ATTEMPT_NOT_FOUND"})
    if not version:
        raise HTTPException(status_code=404, detail={"code": "QUESTION_VERSION_NOT_FOUND"})
    result = score_response(version.question_type, version.correct_answer, payload.response, version.max_score)  # type: ignore[arg-type]
    entity = models.AssessmentResponse(
        organization_id=actor.organization_id,
        attempt_id=attempt_id,
        question_version_id=payload.question_version_id,
        response_payload=payload.response,
        score=result.score,
        maximum_score=result.max_score,
        is_correct=result.is_correct,
        correction_type=result.correction_type,
        feedback=result.explanation,
        requires_human_review=result.requires_human_review,
        corrected_at=None if result.requires_human_review else datetime.now(UTC),
    )
    if result.requires_human_review:
        attempt.requires_human_review = True
        attempt.status = AttemptStatus.UNDER_REVIEW.value
    else:
        attempt.status = AttemptStatus.IN_PROGRESS.value
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/responses/{response_id}/review", response_model=ResponseRead)
async def review_response(
    response_id: uuid.UUID, payload: ReviewCreate, session: SessionDep, actor: ActorDep
) -> models.AssessmentResponse:
    require_role(actor, TEACHER_ROLES)
    response = await repositories.get_for_organization(session, models.AssessmentResponse, actor.organization_id, response_id)
    if not response:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_RESPONSE_NOT_FOUND"})
    if payload.proposed_score > response.maximum_score:
        raise HTTPException(status_code=422, detail={"code": "SCORE_EXCEEDS_MAXIMUM"})
    review = models.ScoreReview(
        organization_id=actor.organization_id,
        response_id=response.id,
        reviewer_user_id=actor.user_id,
        previous_score=response.score,
        proposed_score=payload.proposed_score,
        final_score=payload.proposed_score,
        justification=payload.justification,
        status="APPROVED",
        decided_at=datetime.now(UTC),
    )
    response.score = payload.proposed_score
    response.is_correct = payload.proposed_score >= response.maximum_score
    response.feedback = payload.feedback or response.feedback
    response.correction_type = CorrectionType.HUMAN.value
    response.requires_human_review = False
    response.corrected_at = datetime.now(UTC)
    response.corrected_by_user_id = actor.user_id
    session.add(review)
    await session.commit()
    return response


@router.post("/scoring/evaluate", response_model=ScoreResult)
async def evaluate_response(payload: ScoreRequest, actor: ActorDep) -> ScoreResult:
    require_role(actor, TEACHER_ROLES)
    return score_response(payload.question_type, payload.correct_answer, payload.response, payload.max_score)


@router.post("/analytics/items", response_model=ItemAnalyticsResult)
async def item_analytics(payload: ItemAnalyticsInput, actor: ActorDep) -> ItemAnalyticsResult:
    require_role(actor, TEACHER_ROLES)
    return calculate_item_analytics(payload)


@router.post("/instruments/dimensions/summarize", response_model=DimensionSummaryResult)
async def dimension_summary(payload: DimensionSummaryInput, actor: ActorDep) -> DimensionSummaryResult:
    require_role(actor, TEACHER_ROLES)
    return summarize_dimensions(payload)
