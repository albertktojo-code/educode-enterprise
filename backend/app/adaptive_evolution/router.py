from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, repositories
from .audit import emit_audit_event
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import (
    AccessibleVersionStatus,
    ApprovalStatus,
    EquivalenceStatus,
    ProgressionAction,
    ReviewStatus,
    RuleStatus,
)
from .schemas import (
    AccessibleVersionGenerateInput,
    AccessibleVersionReviewInput,
    AccessibleVersionGenerateResult,
    AccessibleVersionRead,
    AdaptiveFeedbackRead,
    AdaptiveFeedbackRecordCreate,
    FeedbackAdaptInput,
    FeedbackAdaptResult,
    GraduatedHintCreate,
    GraduatedHintRead,
    HintSelectionInput,
    HintSelectionResult,
    HintUsageCreate,
    IndividualDifficultyInput,
    IndividualDifficultyResult,
    ResourceDifficultyMetricRead,
    ReviewCompletionInput,
    ObservedDifficultyInput,
    ObservedDifficultyResult,
    ProgressionEvaluationInput,
    ProgressionEvaluationResult,
    ProgressionRuleCreate,
    ProgressionDecisionRead,
    ProgressionRuleRead,
    SpacedReviewInput,
    SpacedReviewResult,
    SpacedReviewScheduleRead,
    StudentDifficultyProfileRead,
)
from .services import (
    adapt_feedback,
    calculate_individual_difficulty,
    calculate_next_review,
    calculate_observed_difficulty,
    evaluate_progression,
    generate_accessible_version,
    select_next_hint,
)

router = APIRouter(prefix="/adaptive-evolution", tags=["Adaptive evolution 14.1"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]


ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
TEACHER_ROLES = ADMIN_ROLES | {"TEACHER"}
LEARNING_ROLES = TEACHER_ROLES | {"STUDENT"}


def require_any_role(actor: ActorContext, allowed: set[str]) -> None:
    if not actor.roles.intersection(allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ADAPTIVE_EVOLUTION_ACCESS_DENIED",
                "message": "O papel do usuário não permite esta operação.",
            },
        )


@router.get("/health")
async def adaptive_evolution_health() -> dict[str, str]:
    return {"status": "ok", "module": "adaptive-evolution", "sprint": "14.1"}


@router.post("/hints", response_model=GraduatedHintRead, status_code=status.HTTP_201_CREATED)
async def create_hint(payload: GraduatedHintCreate, session: SessionDep, actor: ActorDep) -> models.GraduatedHint:
    require_any_role(actor, TEACHER_ROLES)
    entity = models.GraduatedHint(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        question_id=payload.question_id,
        learning_node_id=payload.learning_node_id,
        level=payload.level.value,
        level_order=payload.level_order,
        title=payload.title,
        content=payload.content,
        content_format=payload.content_format,
        release_rule=payload.release_rule,
        penalty_rule=payload.penalty_rule,
        version=payload.version,
        status=payload.status.value,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "hint.created",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="graduated_hint",
        resource_id=entity.id,
        details={"resource_type": entity.resource_type, "level": entity.level},
    )
    return entity


@router.get("/hints", response_model=list[GraduatedHintRead])
async def list_hints(
    session: SessionDep,
    actor: ActorDep,
    resource_type: str = Query(min_length=2, max_length=60),
    resource_id: uuid.UUID = Query(),
    question_id: uuid.UUID | None = Query(default=None),
) -> list[models.GraduatedHint]:
    require_any_role(actor, LEARNING_ROLES)
    statement = select(models.GraduatedHint).where(
        models.GraduatedHint.organization_id == actor.organization_id,
        models.GraduatedHint.resource_type == resource_type,
        models.GraduatedHint.resource_id == resource_id,
    )
    if question_id:
        statement = statement.where(models.GraduatedHint.question_id == question_id)
    statement = statement.order_by(models.GraduatedHint.level_order, models.GraduatedHint.version)
    result = await session.execute(statement)
    return list(result.scalars().all())


@router.post("/hints/select", response_model=HintSelectionResult)
async def select_hint(
    payload: HintSelectionInput,
    session: SessionDep,
    actor: ActorDep,
    resource_type: str = Query(min_length=2, max_length=60),
    resource_id: uuid.UUID = Query(),
    question_id: uuid.UUID | None = Query(default=None),
) -> HintSelectionResult:
    require_any_role(actor, LEARNING_ROLES)
    statement = select(models.GraduatedHint).where(
        models.GraduatedHint.organization_id == actor.organization_id,
        models.GraduatedHint.resource_type == resource_type,
        models.GraduatedHint.resource_id == resource_id,
    )
    if question_id:
        statement = statement.where(models.GraduatedHint.question_id == question_id)
    result = await session.execute(statement)
    selection = select_next_hint(result.scalars().all(), payload)
    emit_audit_event(
        "hint.selected",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details={"selected_hint_id": str(selection.selected_hint_id) if selection.selected_hint_id else None},
    )
    return selection


@router.post("/hint-usages", status_code=status.HTTP_201_CREATED)
async def register_hint_usage(payload: HintUsageCreate, session: SessionDep, actor: ActorDep) -> dict[str, str]:
    require_any_role(actor, LEARNING_ROLES)
    hint = await repositories.get_for_organization(
        session, models.GraduatedHint, actor.organization_id, payload.graduated_hint_id
    )
    if not hint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HINT_NOT_FOUND", "message": "Pista não encontrada na organização ativa."},
        )
    entity = models.HintUsage(
        organization_id=actor.organization_id,
        student_id=payload.student_id,
        classroom_id=payload.classroom_id,
        attempt_id=payload.attempt_id,
        question_id=payload.question_id,
        graduated_hint_id=payload.graduated_hint_id,
        release_type=payload.release_type.value,
        release_reason=payload.release_reason,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "hint.used",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="hint_usage",
        resource_id=entity.id,
        details={"attempt_id": str(payload.attempt_id), "student_id": str(payload.student_id)},
    )
    return {"id": str(entity.id), "status": "registered"}


@router.post("/reviews/calculate-next", response_model=SpacedReviewResult)
async def calculate_review(payload: SpacedReviewInput, actor: ActorDep) -> SpacedReviewResult:
    require_any_role(actor, LEARNING_ROLES)
    return calculate_next_review(payload)


@router.post("/feedback/adapt", response_model=FeedbackAdaptResult)
async def create_adaptive_feedback(payload: FeedbackAdaptInput, actor: ActorDep) -> FeedbackAdaptResult:
    require_any_role(actor, LEARNING_ROLES)
    return adapt_feedback(payload)


@router.post("/difficulty/individual", response_model=IndividualDifficultyResult)
async def calculate_student_difficulty(payload: IndividualDifficultyInput, actor: ActorDep) -> IndividualDifficultyResult:
    require_any_role(actor, TEACHER_ROLES)
    return calculate_individual_difficulty(payload)


@router.post("/difficulty/observed", response_model=ObservedDifficultyResult)
async def calculate_resource_difficulty(payload: ObservedDifficultyInput, actor: ActorDep) -> ObservedDifficultyResult:
    require_any_role(actor, TEACHER_ROLES)
    return calculate_observed_difficulty(payload)


@router.post("/progression-rules", response_model=ProgressionRuleRead, status_code=status.HTTP_201_CREATED)
async def create_progression_rule(
    payload: ProgressionRuleCreate,
    session: SessionDep,
    actor: ActorDep,
) -> models.ProgressionRule:
    require_any_role(actor, ADMIN_ROLES)
    entity = models.ProgressionRule(
        organization_id=actor.organization_id,
        name=payload.name,
        version=payload.version,
        description=payload.description,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        conditions=payload.conditions,
        result_action=payload.result_action.value,
        priority=payload.priority,
        requires_teacher_approval=payload.requires_teacher_approval,
        status=payload.status.value,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "progression_rule.created",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="progression_rule",
        resource_id=entity.id,
    )
    return entity


@router.get("/progression-rules", response_model=list[ProgressionRuleRead])
async def list_progression_rules(session: SessionDep, actor: ActorDep) -> list[models.ProgressionRule]:
    require_any_role(actor, TEACHER_ROLES)
    rows = await repositories.list_for_organization(
        session,
        models.ProgressionRule,
        actor.organization_id,
        order_by=models.ProgressionRule.priority.asc(),
    )
    return list(rows)


@router.post("/progression-rules/{rule_id}/publish", response_model=ProgressionRuleRead)
async def publish_progression_rule(
    rule_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> models.ProgressionRule:
    require_any_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ProgressionRule, actor.organization_id, rule_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "PROGRESSION_RULE_NOT_FOUND"})
    if entity.status == RuleStatus.PUBLISHED.value:
        return entity
    entity.status = RuleStatus.PUBLISHED.value
    entity.published_by_user_id = actor.user_id
    entity.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "progression_rule.published",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="progression_rule",
        resource_id=entity.id,
    )
    return entity


@router.post("/progression-rules/{rule_id}/evaluate", response_model=ProgressionEvaluationResult)
async def evaluate_rule(
    rule_id: uuid.UUID,
    payload: ProgressionEvaluationInput,
    session: SessionDep,
    actor: ActorDep,
) -> ProgressionEvaluationResult:
    require_any_role(actor, TEACHER_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ProgressionRule, actor.organization_id, rule_id
    )
    if not entity or entity.status != RuleStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=404,
            detail={"code": "PUBLISHED_PROGRESSION_RULE_NOT_FOUND"},
        )
    return evaluate_progression(
        entity.conditions,
        ProgressionAction(entity.result_action),
        entity.requires_teacher_approval,
        payload,
    )


@router.post(
    "/accessible-versions/generate",
    response_model=AccessibleVersionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_accessible_version(
    payload: AccessibleVersionGenerateInput,
    session: SessionDep,
    actor: ActorDep,
) -> models.AccessibleResourceVersion:
    require_any_role(actor, TEACHER_ROLES)
    generated: AccessibleVersionGenerateResult = generate_accessible_version(payload)
    version = await repositories.next_accessible_version_number(
        session,
        organization_id=actor.organization_id,
        source_resource_type=payload.source_resource_type,
        source_resource_id=payload.source_resource_id,
        adaptation_type=payload.adaptation_type.value,
    )
    entity = models.AccessibleResourceVersion(
        organization_id=actor.organization_id,
        source_resource_type=payload.source_resource_type,
        source_resource_id=payload.source_resource_id,
        adaptation_type=payload.adaptation_type.value,
        title=generated.title,
        content=generated.content,
        accessibility_metadata=generated.accessibility_metadata,
        pedagogical_snapshot=generated.pedagogical_snapshot,
        pedagogical_equivalence_status=generated.equivalence_status.value,
        generation_method=generated.generation_method.value,
        version=version,
        status=generated.status,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "accessible_version.generated",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="accessible_resource_version",
        resource_id=entity.id,
        details={"adaptation_type": entity.adaptation_type, "version": entity.version},
    )
    return entity


@router.post("/accessibility/preview", response_model=AccessibleVersionGenerateResult)
async def preview_accessible_version(
    payload: AccessibleVersionGenerateInput,
    actor: ActorDep,
) -> AccessibleVersionGenerateResult:
    require_any_role(actor, TEACHER_ROLES)
    return generate_accessible_version(payload)


@router.get("/accessible-versions", response_model=list[AccessibleVersionRead])
async def list_accessible_versions(
    session: SessionDep,
    actor: ActorDep,
    source_resource_type: str = Query(min_length=2, max_length=60),
    source_resource_id: uuid.UUID = Query(),
) -> list[models.AccessibleResourceVersion]:
    require_any_role(actor, TEACHER_ROLES)
    rows = await repositories.list_for_organization(
        session,
        models.AccessibleResourceVersion,
        actor.organization_id,
        filters={
            "source_resource_type": source_resource_type,
            "source_resource_id": source_resource_id,
        },
        order_by=models.AccessibleResourceVersion.version.desc(),
    )
    return list(rows)


@router.post(
    "/students/{student_id}/review-schedules/{learning_node_id}/recalculate",
    response_model=SpacedReviewScheduleRead,
)
async def recalculate_review_schedule(
    student_id: uuid.UUID,
    learning_node_id: uuid.UUID,
    payload: SpacedReviewInput,
    session: SessionDep,
    actor: ActorDep,
) -> models.SpacedReviewSchedule:
    require_any_role(actor, TEACHER_ROLES)
    calculated = calculate_next_review(payload)
    statement = select(models.SpacedReviewSchedule).where(
        models.SpacedReviewSchedule.organization_id == actor.organization_id,
        models.SpacedReviewSchedule.student_id == student_id,
        models.SpacedReviewSchedule.learning_node_id == learning_node_id,
    )
    result = await session.execute(statement)
    entity = result.scalar_one_or_none()
    next_at = datetime.combine(calculated.scheduled_for, time.min, tzinfo=UTC)
    if entity is None:
        entity = models.SpacedReviewSchedule(
            organization_id=actor.organization_id,
            student_id=student_id,
            learning_node_id=learning_node_id,
            status=calculated.status.value,
            priority=calculated.priority,
            interval_days=calculated.interval_days,
            scheduled_for=calculated.scheduled_for,
            next_review_at=next_at,
            mastery_score_at_schedule=payload.mastery_score,
            confidence_at_schedule=payload.confidence_score,
            rule_version=calculated.rule_version,
        )
        await repositories.add_and_refresh(session, entity)
    else:
        entity.status = calculated.status.value
        entity.priority = calculated.priority
        entity.interval_days = calculated.interval_days
        entity.scheduled_for = calculated.scheduled_for
        entity.next_review_at = next_at
        entity.mastery_score_at_schedule = payload.mastery_score
        entity.confidence_at_schedule = payload.confidence_score
        entity.rule_version = calculated.rule_version
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "spaced_review.rescheduled",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="spaced_review_schedule",
        resource_id=entity.id,
        details={"student_id": str(student_id), "learning_node_id": str(learning_node_id)},
    )
    return entity


@router.get(
    "/students/{student_id}/review-schedules",
    response_model=list[SpacedReviewScheduleRead],
)
async def list_review_schedules(
    student_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[models.SpacedReviewSchedule]:
    require_any_role(actor, TEACHER_ROLES)
    filters: dict[str, object] = {"student_id": student_id}
    if status_filter:
        filters["status"] = status_filter.upper()
    rows = await repositories.list_for_organization(
        session,
        models.SpacedReviewSchedule,
        actor.organization_id,
        filters=filters,
        order_by=models.SpacedReviewSchedule.scheduled_for.asc(),
    )
    return list(rows)


@router.post("/reviews/{schedule_id}/complete", response_model=SpacedReviewScheduleRead)
async def complete_review(
    schedule_id: uuid.UUID,
    payload: ReviewCompletionInput,
    session: SessionDep,
    actor: ActorDep,
) -> models.SpacedReviewSchedule:
    require_any_role(actor, TEACHER_ROLES)
    schedule = await repositories.get_for_organization(
        session, models.SpacedReviewSchedule, actor.organization_id, schedule_id
    )
    if not schedule:
        raise HTTPException(status_code=404, detail={"code": "REVIEW_SCHEDULE_NOT_FOUND"})
    calculated = calculate_next_review(
        SpacedReviewInput(
            mastery_score=payload.mastery_score,
            confidence_score=payload.confidence_score,
            result_score=payload.result_score,
            hint_level_used=payload.hint_level_used,
            previous_interval_days=schedule.interval_days,
            reference_date=date.today(),
        )
    )
    completed_at = datetime.now(UTC)
    event = models.SpacedReviewEvent(
        organization_id=actor.organization_id,
        schedule_id=schedule.id,
        student_id=schedule.student_id,
        learning_node_id=schedule.learning_node_id,
        resource_id=payload.resource_id,
        scheduled_for=schedule.scheduled_for,
        started_at=schedule.last_reviewed_at or completed_at,
        completed_at=completed_at,
        result=payload.result_score,
        previous_interval_days=schedule.interval_days,
        new_interval_days=calculated.interval_days,
        rule_applied=calculated.rule_version,
        metadata_json={"hint_level_used": payload.hint_level_used},
    )
    session.add(event)
    schedule.status = ReviewStatus.FUTURE.value
    schedule.last_reviewed_at = completed_at
    schedule.interval_days = calculated.interval_days
    schedule.scheduled_for = calculated.scheduled_for
    schedule.next_review_at = datetime.combine(calculated.scheduled_for, time.min, tzinfo=UTC)
    schedule.priority = calculated.priority
    schedule.mastery_score_at_schedule = payload.mastery_score
    schedule.confidence_at_schedule = payload.confidence_score
    await session.commit()
    await session.refresh(schedule)
    emit_audit_event(
        "spaced_review.completed",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="spaced_review_schedule",
        resource_id=schedule.id,
        details={"result_score": payload.result_score, "next_review": str(schedule.scheduled_for)},
    )
    return schedule


@router.post("/feedback/records", response_model=AdaptiveFeedbackRead, status_code=201)
async def record_adaptive_feedback(
    payload: AdaptiveFeedbackRecordCreate,
    session: SessionDep,
    actor: ActorDep,
) -> models.AdaptiveFeedback:
    require_any_role(actor, TEACHER_ROLES)
    adapted = adapt_feedback(payload.adaptation)
    entity = models.AdaptiveFeedback(
        organization_id=actor.organization_id,
        student_id=payload.student_id,
        attempt_id=payload.attempt_id,
        response_id=payload.response_id,
        learning_node_id=payload.learning_node_id,
        feedback_type=adapted.feedback_type.value,
        error_type=payload.adaptation.error_type.value,
        mastery_level=payload.adaptation.mastery_level,
        content=adapted.content,
        next_action=adapted.next_action.value,
        rule_version=adapted.rule_version,
        generated_by="DETERMINISTIC",
        review_status="PENDING" if adapted.requires_teacher_review else "NOT_REQUIRED",
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "adaptive_feedback.generated",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="adaptive_feedback",
        resource_id=entity.id,
        details={"attempt_id": str(payload.attempt_id)},
    )
    return entity


@router.post(
    "/students/{student_id}/difficulty/{learning_node_id}/recalculate",
    response_model=StudentDifficultyProfileRead,
)
async def persist_individual_difficulty(
    student_id: uuid.UUID,
    learning_node_id: uuid.UUID,
    payload: IndividualDifficultyInput,
    session: SessionDep,
    actor: ActorDep,
) -> models.StudentDifficultyProfile:
    require_any_role(actor, TEACHER_ROLES)
    statement = select(models.StudentDifficultyProfile).where(
        models.StudentDifficultyProfile.organization_id == actor.organization_id,
        models.StudentDifficultyProfile.student_id == student_id,
        models.StudentDifficultyProfile.learning_node_id == learning_node_id,
    )
    result = await session.execute(statement)
    entity = result.scalar_one_or_none()
    effective_payload = payload
    if entity and payload.previous_difficulty_score is None:
        effective_payload = payload.model_copy(update={"previous_difficulty_score": entity.difficulty_score})
    calculated = calculate_individual_difficulty(effective_payload)
    if entity is None:
        entity = models.StudentDifficultyProfile(
            organization_id=actor.organization_id,
            student_id=student_id,
            learning_node_id=learning_node_id,
            difficulty_score=calculated.difficulty_score,
            difficulty_level=calculated.difficulty_level.value,
            confidence_score=calculated.confidence_score,
            previous_score=payload.previous_difficulty_score,
            change_reason=calculated.reason,
            calculation_version=calculated.calculation_version,
            requires_review=calculated.requires_teacher_review,
        )
        await repositories.add_and_refresh(session, entity)
    else:
        entity.previous_score = entity.difficulty_score
        entity.difficulty_score = calculated.difficulty_score
        entity.difficulty_level = calculated.difficulty_level.value
        entity.confidence_score = calculated.confidence_score
        entity.change_reason = calculated.reason
        entity.last_calculated_at = datetime.now(UTC)
        entity.calculation_version = calculated.calculation_version
        entity.requires_review = calculated.requires_teacher_review
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "student_difficulty.calculated",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="student_difficulty_profile",
        resource_id=entity.id,
        details={"student_id": str(student_id), "learning_node_id": str(learning_node_id)},
    )
    return entity


@router.post(
    "/resources/{resource_type}/{resource_id}/difficulty/recalculate",
    response_model=ResourceDifficultyMetricRead,
)
async def persist_observed_difficulty(
    resource_type: str,
    resource_id: uuid.UUID,
    payload: ObservedDifficultyInput,
    session: SessionDep,
    actor: ActorDep,
    learning_node_id: uuid.UUID | None = Query(default=None),
) -> models.ResourceDifficultyMetric:
    require_any_role(actor, TEACHER_ROLES)
    calculated = calculate_observed_difficulty(payload)
    statement = select(models.ResourceDifficultyMetric).where(
        models.ResourceDifficultyMetric.organization_id == actor.organization_id,
        models.ResourceDifficultyMetric.resource_type == resource_type,
        models.ResourceDifficultyMetric.resource_id == resource_id,
        models.ResourceDifficultyMetric.learning_node_id == learning_node_id,
    )
    result = await session.execute(statement)
    entity = result.scalar_one_or_none()
    values = {
        "predicted_difficulty": calculated.predicted_difficulty,
        "observed_difficulty": calculated.observed_difficulty,
        "difficulty_difference": calculated.difference,
        "difficulty_classification": calculated.classification.value,
        "sample_size": calculated.sample_size,
        "confidence_score": calculated.confidence_score,
        "metrics_snapshot": calculated.metrics,
        "calculation_version": calculated.calculation_version,
        "last_calculated_at": datetime.now(UTC),
    }
    if entity is None:
        entity = models.ResourceDifficultyMetric(
            organization_id=actor.organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            learning_node_id=learning_node_id,
            **values,
        )
        await repositories.add_and_refresh(session, entity)
    else:
        for name, value in values.items():
            setattr(entity, name, value)
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "resource_difficulty.observed",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        details={"classification": calculated.classification.value, "sample_size": calculated.sample_size},
    )
    return entity


@router.post(
    "/progression-rules/{rule_id}/decisions",
    response_model=ProgressionDecisionRead,
    status_code=201,
)
async def create_progression_decision(
    rule_id: uuid.UUID,
    payload: ProgressionEvaluationInput,
    session: SessionDep,
    actor: ActorDep,
    student_id: uuid.UUID = Query(),
    learning_path_id: uuid.UUID | None = Query(default=None),
    learning_node_id: uuid.UUID | None = Query(default=None),
) -> models.ProgressionDecision:
    require_any_role(actor, TEACHER_ROLES)
    rule = await repositories.get_for_organization(
        session, models.ProgressionRule, actor.organization_id, rule_id
    )
    if not rule or rule.status != RuleStatus.PUBLISHED.value:
        raise HTTPException(status_code=404, detail={"code": "PUBLISHED_PROGRESSION_RULE_NOT_FOUND"})
    evaluated = evaluate_progression(
        rule.conditions,
        ProgressionAction(rule.result_action),
        rule.requires_teacher_approval,
        payload,
    )
    entity = models.ProgressionDecision(
        organization_id=actor.organization_id,
        student_id=student_id,
        learning_path_id=learning_path_id,
        learning_node_id=learning_node_id,
        rule_id=rule.id,
        decision=evaluated.action.value,
        decision_reason=evaluated.reason,
        input_snapshot=payload.model_dump(mode="json"),
        requires_teacher_approval=evaluated.requires_teacher_approval,
        approval_status=evaluated.approval_status.value,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "progression_decision.created",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="progression_decision",
        resource_id=entity.id,
        details={"decision": entity.decision, "student_id": str(student_id)},
    )
    return entity


@router.post(
    "/progression-decisions/{decision_id}/approve",
    response_model=ProgressionDecisionRead,
)
async def approve_progression_decision(
    decision_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> models.ProgressionDecision:
    require_any_role(actor, TEACHER_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ProgressionDecision, actor.organization_id, decision_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "PROGRESSION_DECISION_NOT_FOUND"})
    entity.approval_status = ApprovalStatus.APPROVED.value
    entity.reviewed_by_user_id = actor.user_id
    entity.reviewed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "progression_decision.approved",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="progression_decision",
        resource_id=entity.id,
    )
    return entity


@router.post(
    "/accessible-versions/{version_id}/review",
    response_model=AccessibleVersionRead,
)
async def review_accessible_version(
    version_id: uuid.UUID,
    payload: AccessibleVersionReviewInput,
    session: SessionDep,
    actor: ActorDep,
) -> models.AccessibleResourceVersion:
    require_any_role(actor, TEACHER_ROLES)
    entity = await repositories.get_for_organization(
        session, models.AccessibleResourceVersion, actor.organization_id, version_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ACCESSIBLE_VERSION_NOT_FOUND"})
    entity.pedagogical_equivalence_status = payload.pedagogical_equivalence_status.value
    entity.reviewed_by_user_id = actor.user_id
    metadata = dict(entity.accessibility_metadata or {})
    metadata["review_notes"] = payload.review_notes
    metadata["reviewed_at"] = datetime.now(UTC).isoformat()
    entity.accessibility_metadata = metadata
    entity.status = (
        AccessibleVersionStatus.APPROVED.value
        if payload.approved and payload.pedagogical_equivalence_status != EquivalenceStatus.NOT_EQUIVALENT
        else AccessibleVersionStatus.NEEDS_REVIEW.value
    )
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "accessible_version.reviewed",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="accessible_resource_version",
        resource_id=entity.id,
        details={"approved": payload.approved, "equivalence": payload.pedagogical_equivalence_status.value},
    )
    return entity


@router.post(
    "/accessible-versions/{version_id}/publish",
    response_model=AccessibleVersionRead,
)
async def publish_accessible_version(
    version_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> models.AccessibleResourceVersion:
    require_any_role(actor, TEACHER_ROLES)
    entity = await repositories.get_for_organization(
        session, models.AccessibleResourceVersion, actor.organization_id, version_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ACCESSIBLE_VERSION_NOT_FOUND"})
    if entity.status != AccessibleVersionStatus.APPROVED.value:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ACCESSIBLE_VERSION_REVIEW_REQUIRED",
                "message": "A versão precisa ser aprovada antes da publicação.",
            },
        )
    entity.status = AccessibleVersionStatus.PUBLISHED.value
    entity.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    emit_audit_event(
        "accessible_version.published",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="accessible_resource_version",
        resource_id=entity.id,
    )
    return entity
