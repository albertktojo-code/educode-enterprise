from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment_hub import models as hub_models

from . import audit, models, repositories
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import (
    AppealStatus,
    FeedbackStatus,
    RegradeStatus,
    ReviewAssignmentStatus,
    ReviewEventType,
    RubricStatus,
)
from .policies import (
    aggregate_skill_feedback,
    calculate_rubric_score,
    canonical_hash,
    determine_review_requirement,
    reconcile_scores,
    score_snapshot,
    validate_rubric_criteria,
)
from .schemas import (
    AppealCreate,
    AppealDecision,
    AppealRead,
    AssignmentCreate,
    AssignmentRead,
    CriterionScoreRead,
    FeedbackCreate,
    FeedbackRead,
    RegradeCreate,
    RegradeDecision,
    RegradeRead,
    ReviewRequirementRequest,
    ReviewRequirementResult,
    ReviewSummary,
    RubricCreate,
    RubricRead,
    RubricSimulationRequest,
    RubricSimulationResult,
    RubricVersionCreate,
    RubricVersionRead,
    ScoreSubmission,
)

router = APIRouter(prefix="/assessment-review", tags=["assessment-review"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN", "PLATFORM_ADMIN", "ORG_ADMIN"}
REVIEW_ROLES = ADMIN_ROLES | {"TEACHER", "PROFESSOR", "COORDINATOR", "ASSESSMENT_MANAGER", "REVIEWER"}
LEARNER_ROLES = {"STUDENT", "LEARNER"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    if not actor.roles.intersection(allowed):
        raise HTTPException(status_code=403, detail={"code": "ASSESSMENT_REVIEW_ACCESS_DENIED"})


async def add_event(
    session: AsyncSession,
    *,
    actor: ActorContext,
    entity_type: str,
    entity_id: uuid.UUID,
    event_type: str,
    previous: dict | None = None,
    new: dict | None = None,
    justification: str | None = None,
    request_id: str | None = None,
) -> None:
    session.add(
        models.ReviewAuditEvent(
            organization_id=actor.organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor_user_id=actor.user_id,
            previous_snapshot=previous or {},
            new_snapshot=new or {},
            justification=justification,
            request_id=request_id,
        )
    )


async def ensure_response(
    session: AsyncSession, actor: ActorContext, response_id: uuid.UUID
) -> hub_models.AssessmentResponse:
    entity = await repositories.get_for_organization(
        session, hub_models.AssessmentResponse, actor.organization_id, response_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_RESPONSE_NOT_FOUND"})
    return entity


async def ensure_attempt(
    session: AsyncSession, actor: ActorContext, attempt_id: uuid.UUID
) -> hub_models.AssessmentAttempt:
    entity = await repositories.get_for_organization(
        session, hub_models.AssessmentAttempt, actor.organization_id, attempt_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ASSESSMENT_ATTEMPT_NOT_FOUND"})
    return entity


async def recalculate_attempt_totals(
    session: AsyncSession, actor: ActorContext, attempt_id: uuid.UUID
) -> hub_models.AssessmentAttempt:
    attempt = await ensure_attempt(session, actor, attempt_id)
    result = await session.execute(
        select(hub_models.AssessmentResponse).where(
            hub_models.AssessmentResponse.organization_id == actor.organization_id,
            hub_models.AssessmentResponse.attempt_id == attempt_id,
        )
    )
    responses = list(result.scalars().all())
    total = sum(float(item.score or 0) for item in responses)
    maximum = sum(float(item.maximum_score or 0) for item in responses)
    attempt.total_score = round(total, 4)
    attempt.maximum_score = round(maximum, 4)
    attempt.percentage_score = round((total / maximum * 100) if maximum else 0, 2)
    attempt.requires_human_review = any(item.requires_human_review for item in responses)
    attempt.scored_at = datetime.now(UTC)
    summary = await session.scalar(
        select(hub_models.AssessmentResultSummary).where(
            hub_models.AssessmentResultSummary.organization_id == actor.organization_id,
            hub_models.AssessmentResultSummary.attempt_id == attempt_id,
        )
    )
    if summary:
        summary.total_score = attempt.total_score
        summary.maximum_score = attempt.maximum_score
        summary.percentage_score = attempt.percentage_score
        summary.requires_human_review = attempt.requires_human_review
    else:
        session.add(
            hub_models.AssessmentResultSummary(
                organization_id=actor.organization_id,
                attempt_id=attempt.id,
                student_id=attempt.student_id,
                total_score=attempt.total_score,
                maximum_score=attempt.maximum_score,
                percentage_score=attempt.percentage_score,
                dimension_scores={},
                skill_scores={},
                descriptive_interpretation={},
                scoring_version="15.4-review",
                requires_human_review=attempt.requires_human_review,
            )
        )
    return attempt


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "15.4", "module": "assessment-review"}


@router.post("/review-requirement", response_model=ReviewRequirementResult)
async def review_requirement(payload: ReviewRequirementRequest, actor: ActorDep) -> ReviewRequirementResult:
    require_role(actor, REVIEW_ROLES)
    required, reasons = determine_review_requirement(**payload.model_dump())
    return ReviewRequirementResult(requires_human_review=required, reasons=reasons)


@router.post("/rubrics", response_model=RubricRead, status_code=201)
async def create_rubric(
    payload: RubricCreate, session: SessionDep, actor: ActorDep
) -> models.ReviewRubric:
    require_role(actor, REVIEW_ROLES)
    exists = await session.scalar(
        select(func.count(models.ReviewRubric.id)).where(
            models.ReviewRubric.organization_id == actor.organization_id,
            models.ReviewRubric.code == payload.code,
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail={"code": "RUBRIC_CODE_ALREADY_EXISTS"})
    entity = models.ReviewRubric(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    await repositories.add_and_refresh(session, entity)
    await add_event(
        session,
        actor=actor,
        entity_type="RUBRIC",
        entity_id=entity.id,
        event_type="RUBRIC_CREATED",
        new={"code": entity.code},
    )
    await session.commit()
    audit.record("assessment_review.rubric_created", rubric_id=str(entity.id))
    return entity


@router.get("/rubrics", response_model=list[RubricRead])
async def list_rubrics(
    session: SessionDep,
    actor: ActorDep,
    status: RubricStatus | None = None,
    search: str | None = Query(default=None, max_length=120),
) -> list[models.ReviewRubric]:
    require_role(actor, REVIEW_ROLES)
    query = select(models.ReviewRubric).where(
        models.ReviewRubric.organization_id == actor.organization_id
    )
    if status:
        query = query.where(models.ReviewRubric.status == status.value)
    if search:
        query = query.where(models.ReviewRubric.name.ilike(f"%{search}%"))
    result = await session.execute(query.order_by(models.ReviewRubric.updated_at.desc()))
    return list(result.scalars().all())


@router.post("/rubrics/{rubric_id}/versions", response_model=RubricVersionRead, status_code=201)
async def create_rubric_version(
    rubric_id: uuid.UUID,
    payload: RubricVersionCreate,
    session: SessionDep,
    actor: ActorDep,
) -> models.ReviewRubricVersion:
    require_role(actor, REVIEW_ROLES)
    rubric = await repositories.get_for_organization(
        session, models.ReviewRubric, actor.organization_id, rubric_id
    )
    if not rubric:
        raise HTTPException(status_code=404, detail={"code": "RUBRIC_NOT_FOUND"})
    criteria_payload = [item.model_dump() for item in payload.criteria]
    errors = validate_rubric_criteria(criteria_payload, payload.maximum_score)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "INVALID_RUBRIC", "errors": errors})
    latest = await session.scalar(
        select(func.max(models.ReviewRubricVersion.version)).where(
            models.ReviewRubricVersion.organization_id == actor.organization_id,
            models.ReviewRubricVersion.rubric_id == rubric_id,
        )
    )
    version = int(latest or 0) + 1
    configuration = payload.model_dump(mode="json")
    entity = models.ReviewRubricVersion(
        organization_id=actor.organization_id,
        rubric_id=rubric_id,
        version=version,
        configuration_hash=canonical_hash(configuration),
        created_by_user_id=actor.user_id,
        criteria=criteria_payload,
        maximum_score=payload.maximum_score,
        score_rules=payload.score_rules,
        feedback_templates=payload.feedback_templates,
        skill_mappings=payload.skill_mappings,
        accessibility_settings=payload.accessibility_settings,
    )
    rubric.current_version = version
    rubric.updated_by_user_id = actor.user_id
    await repositories.add_and_refresh(session, entity)
    await add_event(
        session,
        actor=actor,
        entity_type="RUBRIC_VERSION",
        entity_id=entity.id,
        event_type="RUBRIC_VERSION_CREATED",
        new={"version": version, "hash": entity.configuration_hash},
    )
    await session.commit()
    return entity


@router.post("/rubric-versions/{version_id}/publish", response_model=RubricVersionRead)
async def publish_rubric_version(
    version_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.ReviewRubricVersion:
    require_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ReviewRubricVersion, actor.organization_id, version_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "RUBRIC_VERSION_NOT_FOUND"})
    if entity.status != RubricStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail={"code": "RUBRIC_VERSION_NOT_DRAFT"})
    errors = validate_rubric_criteria(entity.criteria, entity.maximum_score)
    if errors:
        raise HTTPException(status_code=422, detail={"code": "INVALID_RUBRIC", "errors": errors})
    entity.status = RubricStatus.PUBLISHED.value
    entity.published_by_user_id = actor.user_id
    entity.published_at = datetime.now(UTC)
    rubric = await repositories.get_for_organization(
        session, models.ReviewRubric, actor.organization_id, entity.rubric_id
    )
    if rubric:
        rubric.status = RubricStatus.PUBLISHED.value
    await add_event(
        session,
        actor=actor,
        entity_type="RUBRIC_VERSION",
        entity_id=entity.id,
        event_type="RUBRIC_VERSION_PUBLISHED",
        new={"version": entity.version},
    )
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/rubrics/simulate", response_model=RubricSimulationResult)
async def simulate_rubric(
    payload: RubricSimulationRequest, actor: ActorDep
) -> RubricSimulationResult:
    require_role(actor, REVIEW_ROLES)
    criteria = [item.model_dump() for item in payload.criteria]
    result = calculate_rubric_score(criteria, payload.awarded_scores)
    return RubricSimulationResult(**result)


@router.post("/assignments", response_model=AssignmentRead, status_code=201)
async def create_assignment(
    payload: AssignmentCreate,
    session: SessionDep,
    actor: ActorDep,
    request: Request,
) -> models.ReviewAssignment:
    require_role(actor, REVIEW_ROLES)
    response = await ensure_response(session, actor, payload.response_id)
    if response.attempt_id != payload.attempt_id:
        raise HTTPException(status_code=422, detail={"code": "RESPONSE_ATTEMPT_MISMATCH"})
    if response.question_version_id != payload.question_version_id:
        raise HTTPException(status_code=422, detail={"code": "RESPONSE_QUESTION_MISMATCH"})
    if payload.rubric_version_id:
        rubric_version = await repositories.get_for_organization(
            session, models.ReviewRubricVersion, actor.organization_id, payload.rubric_version_id
        )
        if not rubric_version or rubric_version.status != RubricStatus.PUBLISHED.value:
            raise HTTPException(status_code=409, detail={"code": "PUBLISHED_RUBRIC_REQUIRED"})
    entity = models.ReviewAssignment(
        organization_id=actor.organization_id,
        assigned_by_user_id=actor.user_id,
        **payload.model_dump(mode="python"),
    )
    await repositories.add_and_refresh(session, entity)
    await add_event(
        session,
        actor=actor,
        entity_type="REVIEW_ASSIGNMENT",
        entity_id=entity.id,
        event_type=ReviewEventType.ASSIGNED.value,
        new={"reviewer_user_id": str(entity.reviewer_user_id)},
        request_id=request.headers.get("x-request-id"),
    )
    await session.commit()
    return entity


@router.get("/assignments", response_model=list[AssignmentRead])
async def list_assignments(
    session: SessionDep,
    actor: ActorDep,
    status: ReviewAssignmentStatus | None = None,
    reviewer_user_id: uuid.UUID | None = None,
) -> list[models.ReviewAssignment]:
    require_role(actor, REVIEW_ROLES)
    query = select(models.ReviewAssignment).where(
        models.ReviewAssignment.organization_id == actor.organization_id
    )
    if status:
        query = query.where(models.ReviewAssignment.status == status.value)
    if reviewer_user_id:
        query = query.where(models.ReviewAssignment.reviewer_user_id == reviewer_user_id)
    elif not actor.roles.intersection(ADMIN_ROLES | {"COORDINATOR", "ASSESSMENT_MANAGER"}):
        query = query.where(models.ReviewAssignment.reviewer_user_id == actor.user_id)
    result = await session.execute(
        query.order_by(models.ReviewAssignment.priority.desc(), models.ReviewAssignment.created_at)
    )
    return list(result.scalars().all())


@router.post("/assignments/{assignment_id}/start", response_model=AssignmentRead)
async def start_assignment(
    assignment_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.ReviewAssignment:
    require_role(actor, REVIEW_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ReviewAssignment, actor.organization_id, assignment_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_ASSIGNMENT_NOT_FOUND"})
    if entity.reviewer_user_id != actor.user_id and not actor.roles.intersection(ADMIN_ROLES):
        raise HTTPException(status_code=403, detail={"code": "REVIEWER_MISMATCH"})
    if entity.status not in {ReviewAssignmentStatus.PENDING.value, ReviewAssignmentStatus.REOPENED.value}:
        raise HTTPException(status_code=409, detail={"code": "ASSIGNMENT_CANNOT_START"})
    entity.status = ReviewAssignmentStatus.IN_REVIEW.value
    entity.started_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/assignments/{assignment_id}/scores", response_model=list[CriterionScoreRead])
async def submit_scores(
    assignment_id: uuid.UUID,
    payload: ScoreSubmission,
    session: SessionDep,
    actor: ActorDep,
) -> list[models.ReviewCriterionScore]:
    require_role(actor, REVIEW_ROLES)
    assignment = await repositories.get_for_organization(
        session, models.ReviewAssignment, actor.organization_id, assignment_id
    )
    if not assignment:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_ASSIGNMENT_NOT_FOUND"})
    if assignment.reviewer_user_id != actor.user_id and not actor.roles.intersection(ADMIN_ROLES):
        raise HTTPException(status_code=403, detail={"code": "REVIEWER_MISMATCH"})
    if assignment.status == ReviewAssignmentStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail={"code": "ASSIGNMENT_ALREADY_COMPLETED"})
    created: list[models.ReviewCriterionScore] = []
    for item in payload.scores:
        current = await session.scalar(
            select(models.ReviewCriterionScore).where(
                models.ReviewCriterionScore.organization_id == actor.organization_id,
                models.ReviewCriterionScore.assignment_id == assignment_id,
                models.ReviewCriterionScore.criterion_code == item.criterion_code,
            )
        )
        data = item.model_dump(mode="json")
        data["correction_source"] = item.correction_source.value
        if current:
            for key, value in data.items():
                setattr(current, key, value)
            current.reviewer_user_id = actor.user_id
            created.append(current)
        else:
            entity = models.ReviewCriterionScore(
                organization_id=actor.organization_id,
                assignment_id=assignment_id,
                reviewer_user_id=actor.user_id,
                **data,
            )
            session.add(entity)
            created.append(entity)
    if payload.finalize:
        assignment.status = ReviewAssignmentStatus.COMPLETED.value
        assignment.completed_at = datetime.now(UTC)
    await session.flush()
    all_result = await session.execute(
        select(models.ReviewCriterionScore).where(
            models.ReviewCriterionScore.organization_id == actor.organization_id,
            models.ReviewCriterionScore.assignment_id == assignment_id,
        )
    )
    all_scores = list(all_result.scalars().all())
    if payload.finalize and assignment.rubric_version_id:
        rubric_version = await repositories.get_for_organization(
            session, models.ReviewRubricVersion, actor.organization_id, assignment.rubric_version_id
        )
        expected = {str(item["code"]) for item in (rubric_version.criteria if rubric_version else [])}
        received = {item.criterion_code for item in all_scores}
        missing = sorted(expected - received)
        if missing:
            raise HTTPException(
                status_code=422,
                detail={"code": "RUBRIC_CRITERIA_MISSING", "criteria": missing},
            )
    response = await ensure_response(session, actor, assignment.response_id)
    totals = calculate_rubric_score(
        [
            {"code": item.criterion_code, "maximum_score": item.maximum_score}
            for item in all_scores
        ],
        {item.criterion_code: item.awarded_score for item in all_scores},
    )
    response.score = totals["total_score"]
    response.maximum_score = totals["maximum_score"]
    response.is_correct = totals["percentage"] >= 70
    response.correction_type = "RUBRIC"
    response.requires_human_review = not payload.finalize
    response.corrected_at = datetime.now(UTC)
    response.corrected_by_user_id = actor.user_id
    await recalculate_attempt_totals(session, actor, assignment.attempt_id)
    await add_event(
        session,
        actor=actor,
        entity_type="REVIEW_ASSIGNMENT",
        entity_id=assignment.id,
        event_type=(ReviewEventType.COMPLETED.value if payload.finalize else ReviewEventType.SCORE_RECORDED.value),
        new={"total_score": totals["total_score"], "finalized": payload.finalize},
        justification=payload.completion_comment,
    )
    await session.commit()
    for item in all_scores:
        await session.refresh(item)
    return all_scores


@router.get("/assignments/{assignment_id}/skill-feedback")
async def assignment_skill_feedback(
    assignment_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> list[dict]:
    require_role(actor, REVIEW_ROLES)
    assignment = await repositories.get_for_organization(
        session, models.ReviewAssignment, actor.organization_id, assignment_id
    )
    if not assignment:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_ASSIGNMENT_NOT_FOUND"})
    result = await session.execute(
        select(models.ReviewCriterionScore).where(
            models.ReviewCriterionScore.organization_id == actor.organization_id,
            models.ReviewCriterionScore.assignment_id == assignment_id,
        )
    )
    rows = list(result.scalars().all())
    return aggregate_skill_feedback(
        [
            {
                "awarded_score": row.awarded_score,
                "maximum_score": row.maximum_score,
                "skill_scores": row.skill_scores,
            }
            for row in rows
        ]
    )


@router.post("/feedback", response_model=FeedbackRead, status_code=201)
async def create_feedback(
    payload: FeedbackCreate, session: SessionDep, actor: ActorDep
) -> models.ReviewFeedback:
    require_role(actor, REVIEW_ROLES)
    await ensure_attempt(session, actor, payload.attempt_id)
    if payload.response_id:
        await ensure_response(session, actor, payload.response_id)
    data = payload.model_dump(mode="json")
    content_hash = canonical_hash(data)
    entity = models.ReviewFeedback(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        content_hash=content_hash,
        **data,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/feedback/{feedback_id}/publish", response_model=FeedbackRead)
async def publish_feedback(
    feedback_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.ReviewFeedback:
    require_role(actor, REVIEW_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ReviewFeedback, actor.organization_id, feedback_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "FEEDBACK_NOT_FOUND"})
    if entity.status != FeedbackStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail={"code": "FEEDBACK_NOT_DRAFT"})
    entity.status = FeedbackStatus.PUBLISHED.value
    entity.published_by_user_id = actor.user_id
    entity.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.get("/attempts/{attempt_id}/feedback", response_model=list[FeedbackRead])
async def list_attempt_feedback(
    attempt_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> list[models.ReviewFeedback]:
    attempt = await ensure_attempt(session, actor, attempt_id)
    is_learner = bool(actor.roles.intersection(LEARNER_ROLES))
    if is_learner and attempt.student_id != actor.user_id:
        raise HTTPException(status_code=403, detail={"code": "STUDENT_ATTEMPT_ACCESS_DENIED"})
    query = select(models.ReviewFeedback).where(
        models.ReviewFeedback.organization_id == actor.organization_id,
        models.ReviewFeedback.attempt_id == attempt_id,
    )
    if is_learner:
        query = query.where(
            models.ReviewFeedback.status == FeedbackStatus.PUBLISHED.value,
            models.ReviewFeedback.audience == "STUDENT",
        )
    result = await session.execute(query.order_by(models.ReviewFeedback.created_at.desc()))
    return list(result.scalars().all())


@router.post("/appeals", response_model=AppealRead, status_code=201)
async def create_appeal(
    payload: AppealCreate, session: SessionDep, actor: ActorDep
) -> models.ReviewAppeal:
    attempt = await ensure_attempt(session, actor, payload.attempt_id)
    if actor.roles.intersection(LEARNER_ROLES):
        if attempt.student_id != actor.user_id or payload.student_id != actor.user_id:
            raise HTTPException(status_code=403, detail={"code": "STUDENT_APPEAL_ACCESS_DENIED"})
    elif not actor.roles.intersection(REVIEW_ROLES):
        raise HTTPException(status_code=403, detail={"code": "APPEAL_ACCESS_DENIED"})
    if payload.response_id:
        response = await ensure_response(session, actor, payload.response_id)
        if response.attempt_id != payload.attempt_id:
            raise HTTPException(status_code=422, detail={"code": "RESPONSE_ATTEMPT_MISMATCH"})
    entity = models.ReviewAppeal(
        organization_id=actor.organization_id,
        submitted_by_user_id=actor.user_id,
        **payload.model_dump(mode="json"),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.get("/appeals", response_model=list[AppealRead])
async def list_appeals(
    session: SessionDep,
    actor: ActorDep,
    status: AppealStatus | None = None,
) -> list[models.ReviewAppeal]:
    query = select(models.ReviewAppeal).where(
        models.ReviewAppeal.organization_id == actor.organization_id
    )
    if actor.roles.intersection(LEARNER_ROLES):
        query = query.where(models.ReviewAppeal.student_id == actor.user_id)
    else:
        require_role(actor, REVIEW_ROLES)
    if status:
        query = query.where(models.ReviewAppeal.status == status.value)
    result = await session.execute(query.order_by(models.ReviewAppeal.created_at.desc()))
    return list(result.scalars().all())


@router.post("/appeals/{appeal_id}/decision", response_model=AppealRead)
async def decide_appeal(
    appeal_id: uuid.UUID,
    payload: AppealDecision,
    session: SessionDep,
    actor: ActorDep,
) -> models.ReviewAppeal:
    require_role(actor, REVIEW_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ReviewAppeal, actor.organization_id, appeal_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "APPEAL_NOT_FOUND"})
    if entity.status not in {AppealStatus.OPEN.value, AppealStatus.UNDER_REVIEW.value}:
        raise HTTPException(status_code=409, detail={"code": "APPEAL_ALREADY_DECIDED"})
    entity.status = payload.decision
    entity.decision = payload.decision
    entity.decision_justification = payload.justification
    entity.decided_by_user_id = actor.user_id
    entity.decided_at = datetime.now(UTC)
    if payload.final_score is not None and entity.response_id:
        response = await ensure_response(session, actor, entity.response_id)
        if payload.final_score > response.maximum_score:
            raise HTTPException(status_code=422, detail={"code": "FINAL_SCORE_EXCEEDS_MAXIMUM"})
        previous = score_snapshot(
            score=response.score,
            maximum_score=response.maximum_score,
            correction_type=response.correction_type,
        )
        regrade = models.ReviewRegrade(
            organization_id=actor.organization_id,
            appeal_id=entity.id,
            attempt_id=entity.attempt_id,
            response_id=response.id,
            requested_by_user_id=actor.user_id,
            previous_score=response.score,
            proposed_score=payload.final_score,
            final_score=payload.final_score,
            maximum_score=response.maximum_score,
            reason=payload.justification,
            status=RegradeStatus.APPLIED.value,
            applied_by_user_id=actor.user_id,
            applied_at=datetime.now(UTC),
            score_snapshot_before=previous,
            score_snapshot_after={**previous, "score": payload.final_score, "correction_type": "HUMAN_REGRADE"},
        )
        response.score = payload.final_score
        response.correction_type = "HUMAN_REGRADE"
        response.corrected_at = datetime.now(UTC)
        response.corrected_by_user_id = actor.user_id
        session.add(regrade)
        await recalculate_attempt_totals(session, actor, entity.attempt_id)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/regrades", response_model=RegradeRead, status_code=201)
async def create_regrade(
    payload: RegradeCreate, session: SessionDep, actor: ActorDep
) -> models.ReviewRegrade:
    require_role(actor, REVIEW_ROLES)
    response = await ensure_response(session, actor, payload.response_id)
    if response.attempt_id != payload.attempt_id:
        raise HTTPException(status_code=422, detail={"code": "RESPONSE_ATTEMPT_MISMATCH"})
    entity = models.ReviewRegrade(
        organization_id=actor.organization_id,
        requested_by_user_id=actor.user_id,
        previous_score=response.score,
        score_snapshot_before=score_snapshot(
            score=response.score,
            maximum_score=response.maximum_score,
            correction_type=response.correction_type,
        ),
        **payload.model_dump(mode="json"),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/regrades/{regrade_id}/decision", response_model=RegradeRead)
async def decide_regrade(
    regrade_id: uuid.UUID,
    payload: RegradeDecision,
    session: SessionDep,
    actor: ActorDep,
) -> models.ReviewRegrade:
    require_role(actor, ADMIN_ROLES | {"COORDINATOR", "ASSESSMENT_MANAGER"})
    entity = await repositories.get_for_organization(
        session, models.ReviewRegrade, actor.organization_id, regrade_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "REGRADE_NOT_FOUND"})
    if entity.status != RegradeStatus.PENDING.value:
        raise HTTPException(status_code=409, detail={"code": "REGRADE_ALREADY_DECIDED"})
    response = await ensure_response(session, actor, entity.response_id)
    if payload.apply:
        final_score = payload.final_score if payload.final_score is not None else entity.proposed_score
        if final_score > entity.maximum_score:
            raise HTTPException(status_code=422, detail={"code": "FINAL_SCORE_EXCEEDS_MAXIMUM"})
        entity.status = RegradeStatus.APPLIED.value
        entity.final_score = final_score
        entity.score_snapshot_after = {
            **entity.score_snapshot_before,
            "score": final_score,
            "correction_type": "HUMAN_REGRADE",
        }
        response.score = final_score
        response.correction_type = "HUMAN_REGRADE"
        response.corrected_at = datetime.now(UTC)
        response.corrected_by_user_id = actor.user_id
    else:
        entity.status = RegradeStatus.REJECTED.value
        entity.final_score = response.score
        entity.score_snapshot_after = entity.score_snapshot_before
    entity.applied_by_user_id = actor.user_id
    entity.applied_at = datetime.now(UTC)
    entity.reason = f"{entity.reason}\nDecision: {payload.justification}"
    if payload.apply:
        await recalculate_attempt_totals(session, actor, entity.attempt_id)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.get("/attempts/{attempt_id}/summary", response_model=ReviewSummary)
async def attempt_review_summary(
    attempt_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> ReviewSummary:
    await ensure_attempt(session, actor, attempt_id)
    assignments_total = await session.scalar(
        select(func.count(models.ReviewAssignment.id)).where(
            models.ReviewAssignment.organization_id == actor.organization_id,
            models.ReviewAssignment.attempt_id == attempt_id,
        )
    ) or 0
    assignments_completed = await session.scalar(
        select(func.count(models.ReviewAssignment.id)).where(
            models.ReviewAssignment.organization_id == actor.organization_id,
            models.ReviewAssignment.attempt_id == attempt_id,
            models.ReviewAssignment.status == ReviewAssignmentStatus.COMPLETED.value,
        )
    ) or 0
    pending_appeals = await session.scalar(
        select(func.count(models.ReviewAppeal.id)).where(
            models.ReviewAppeal.organization_id == actor.organization_id,
            models.ReviewAppeal.attempt_id == attempt_id,
            models.ReviewAppeal.status.in_([AppealStatus.OPEN.value, AppealStatus.UNDER_REVIEW.value]),
        )
    ) or 0
    applied_regrades = await session.scalar(
        select(func.count(models.ReviewRegrade.id)).where(
            models.ReviewRegrade.organization_id == actor.organization_id,
            models.ReviewRegrade.attempt_id == attempt_id,
            models.ReviewRegrade.status == RegradeStatus.APPLIED.value,
        )
    ) or 0
    feedback_published = await session.scalar(
        select(func.count(models.ReviewFeedback.id)).where(
            models.ReviewFeedback.organization_id == actor.organization_id,
            models.ReviewFeedback.attempt_id == attempt_id,
            models.ReviewFeedback.status == FeedbackStatus.PUBLISHED.value,
        )
    ) or 0
    return ReviewSummary(
        attempt_id=attempt_id,
        assignments_total=int(assignments_total),
        assignments_completed=int(assignments_completed),
        pending_appeals=int(pending_appeals),
        applied_regrades=int(applied_regrades),
        feedback_published=int(feedback_published),
        requires_attention=bool(pending_appeals or assignments_completed < assignments_total),
    )


@router.post("/moderation/reconcile")
async def moderate_scores(
    scores: list[float], maximum_score: float, actor: ActorDep
) -> dict:
    require_role(actor, REVIEW_ROLES)
    if maximum_score <= 0:
        raise HTTPException(status_code=422, detail={"code": "INVALID_MAXIMUM_SCORE"})
    return reconcile_scores(scores, maximum_score)
