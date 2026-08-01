from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, repositories
from .audit import emit_audit_event
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import (
    AssignmentStrategy,
    ExperimentStatus,
    InterventionOutcome,
    MetricDirection,
    RecordStatus,
    SimulationStatus,
)
from .schemas import (
    AdaptiveModelCreate,
    AdaptiveModelRead,
    ControlledExperimentCreate,
    ControlledExperimentRead,
    ExperimentAssignmentInput,
    ExperimentAssignmentResult,
    ExperimentComparisonResult,
    ExperimentObservationCreate,
    InstitutionalPathDashboardInput,
    InstitutionalPathDashboardResult,
    InterventionOutcomeCreate,
    InterventionOutcomeRead,
    InterventionRecommendationInput,
    InterventionRecommendationResult,
    MaterialEffectivenessInput,
    MaterialEffectivenessMetricRead,
    MaterialEffectivenessResult,
    RecommendationSimulationInput,
    RecommendationSimulationResult,
)
from .services import (
    build_institutional_path_dashboard,
    calculate_material_effectiveness,
    compare_experiment_strategies,
    deterministic_strategy_assignment,
    recommend_from_intervention_history,
    simulate_recommendations,
)

router = APIRouter(prefix="/adaptive-insights", tags=["Adaptive Insights — Sprint 14.2"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
TEACHER_ROLES = ADMIN_ROLES | {"TEACHER"}


def require_role(actor: ActorContext, roles: set[str]) -> None:
    if not actor.roles.intersection(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ADAPTIVE_INSIGHTS_ACCESS_DENIED", "message": "Papel sem permissão."},
        )


def canonical_hash(configuration: dict) -> str:
    raw = json.dumps(configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "adaptive-insights", "sprint": "14.2"}


@router.post("/intervention-outcomes", response_model=InterventionOutcomeRead, status_code=201)
async def create_intervention_outcome(
    payload: InterventionOutcomeCreate, session: SessionDep, actor: ActorDep
) -> models.InterventionOutcomeRecord:
    require_role(actor, TEACHER_ROLES)
    gain = payload.mastery_after - payload.mastery_before
    if gain > 0.03:
        outcome = InterventionOutcome.IMPROVED
    elif gain < -0.03:
        outcome = InterventionOutcome.DECLINED
    elif abs(gain) <= 0.03:
        outcome = InterventionOutcome.STABLE
    else:
        outcome = InterventionOutcome.INCONCLUSIVE
    entity = models.InterventionOutcomeRecord(
        organization_id=actor.organization_id,
        student_id=payload.student_id,
        learning_node_id=payload.learning_node_id,
        intervention_type=payload.intervention_type,
        material_id=payload.material_id,
        mastery_before=payload.mastery_before,
        mastery_after=payload.mastery_after,
        mastery_gain=gain,
        completion_rate=payload.completion_rate,
        hints_average=payload.hints_average,
        attempts_average=payload.attempts_average,
        outcome=outcome.value,
        occurred_at=payload.occurred_at,
        source_snapshot=payload.source_snapshot,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "intervention_outcome.created",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="intervention_outcome",
        resource_id=entity.id,
    )
    return entity


@router.get("/intervention-outcomes", response_model=list[InterventionOutcomeRead])
async def list_intervention_outcomes(
    session: SessionDep,
    actor: ActorDep,
    student_id: uuid.UUID | None = Query(default=None),
    learning_node_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[models.InterventionOutcomeRecord]:
    require_role(actor, TEACHER_ROLES)
    statement = select(models.InterventionOutcomeRecord).where(
        models.InterventionOutcomeRecord.organization_id == actor.organization_id
    )
    if student_id:
        statement = statement.where(models.InterventionOutcomeRecord.student_id == student_id)
    if learning_node_id:
        statement = statement.where(models.InterventionOutcomeRecord.learning_node_id == learning_node_id)
    statement = statement.order_by(models.InterventionOutcomeRecord.occurred_at.desc()).limit(limit)
    result = await session.execute(statement)
    return list(result.scalars().all())


@router.post("/recommendations/from-interventions", response_model=InterventionRecommendationResult)
async def intervention_recommendation(
    payload: InterventionRecommendationInput, actor: ActorDep
) -> InterventionRecommendationResult:
    require_role(actor, TEACHER_ROLES)
    result = recommend_from_intervention_history(payload)
    emit_audit_event(
        "intervention_recommendation.simulated",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="student_learning_node",
        resource_id=payload.learning_node_id,
        details={"student_id": str(payload.student_id), "action": result.action.value},
    )
    return result


@router.post("/materials/effectiveness", response_model=MaterialEffectivenessResult)
async def material_effectiveness(
    payload: MaterialEffectivenessInput,
    actor: ActorDep,
    session: SessionDep,
    persist: bool = Query(default=False),
) -> MaterialEffectivenessResult:
    require_role(actor, TEACHER_ROLES)
    result = calculate_material_effectiveness(payload)
    if persist:
        entity = models.MaterialEffectivenessMetric(
            organization_id=actor.organization_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            sample_size=result.sample_size,
            completion_rate=result.completion_rate,
            accuracy_rate=result.accuracy_rate,
            average_gain=result.average_gain,
            median_gain=result.median_gain,
            average_attempts=result.average_attempts,
            average_hints=result.average_hints,
            average_duration_seconds=result.average_duration_seconds,
            confidence_score=result.confidence,
            classification=result.classification,
            metrics_snapshot=result.model_dump(),
            calculation_version=result.calculation_version,
        )
        session.add(entity)
        await session.commit()
    return result


@router.get("/materials/effectiveness", response_model=list[MaterialEffectivenessMetricRead])
async def list_material_effectiveness(
    session: SessionDep, actor: ActorDep, limit: int = Query(default=100, ge=1, le=500)
) -> list[models.MaterialEffectivenessMetric]:
    require_role(actor, TEACHER_ROLES)
    statement = (
        select(models.MaterialEffectivenessMetric)
        .where(models.MaterialEffectivenessMetric.organization_id == actor.organization_id)
        .order_by(models.MaterialEffectivenessMetric.calculated_at.desc())
        .limit(limit)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


@router.post("/models", response_model=AdaptiveModelRead, status_code=201)
async def create_model(
    payload: AdaptiveModelCreate, session: SessionDep, actor: ActorDep
) -> models.AdaptiveModelVersion:
    require_role(actor, ADMIN_ROLES)
    entity = models.AdaptiveModelVersion(
        organization_id=actor.organization_id,
        name=payload.name,
        version=payload.version,
        description=payload.description,
        scope_type=payload.scope_type.value,
        scope_id=payload.scope_id,
        algorithm_type=payload.algorithm_type,
        configuration=payload.configuration,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        configuration_hash=canonical_hash(payload.configuration),
        status=payload.status.value,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    emit_audit_event(
        "adaptive_model.created",
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        resource_type="adaptive_model",
        resource_id=entity.id,
    )
    return entity


@router.get("/models", response_model=list[AdaptiveModelRead])
async def list_models(session: SessionDep, actor: ActorDep) -> list[models.AdaptiveModelVersion]:
    require_role(actor, TEACHER_ROLES)
    return await repositories.list_for_organization(
        session, models.AdaptiveModelVersion, actor.organization_id, order_by=models.AdaptiveModelVersion.created_at.desc()
    )


@router.post("/models/{model_id}/publish", response_model=AdaptiveModelRead)
async def publish_model(
    model_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.AdaptiveModelVersion:
    require_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(
        session, models.AdaptiveModelVersion, actor.organization_id, model_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "ADAPTIVE_MODEL_NOT_FOUND"})
    entity.status = RecordStatus.PUBLISHED.value
    entity.published_by_user_id = actor.user_id
    entity.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/simulations", response_model=RecommendationSimulationResult)
async def run_simulation(
    payload: RecommendationSimulationInput, session: SessionDep, actor: ActorDep
) -> RecommendationSimulationResult:
    require_role(actor, TEACHER_ROLES)
    configuration = payload.model_configuration
    if payload.model_id:
        model = await repositories.get_for_organization(
            session, models.AdaptiveModelVersion, actor.organization_id, payload.model_id
        )
        if not model:
            raise HTTPException(status_code=404, detail={"code": "ADAPTIVE_MODEL_NOT_FOUND"})
        configuration = model.configuration
    assert configuration is not None
    result = simulate_recommendations(payload.profiles, configuration)
    if payload.persist_result:
        entity = models.RecommendationSimulation(
            organization_id=actor.organization_id,
            model_id=payload.model_id,
            profiles_count=result.profiles_count,
            input_snapshot=payload.model_dump(mode="json"),
            output_snapshot=result.model_dump(mode="json"),
            status=SimulationStatus.COMPLETED.value,
            is_simulation=True,
            created_by_user_id=actor.user_id,
        )
        session.add(entity)
        await session.commit()
    return result


@router.post("/experiments", response_model=ControlledExperimentRead, status_code=201)
async def create_experiment(
    payload: ControlledExperimentCreate, session: SessionDep, actor: ActorDep
) -> models.ControlledExperiment:
    require_role(actor, ADMIN_ROLES)
    entity = models.ControlledExperiment(
        organization_id=actor.organization_id,
        name=payload.name,
        description=payload.description,
        hypothesis=payload.hypothesis,
        primary_metric=payload.primary_metric,
        metric_direction=payload.metric_direction.value,
        assignment_strategy=payload.assignment_strategy.value,
        strategies=[item.model_dump(mode="json") for item in payload.strategies],
        minimum_sample_per_strategy=payload.minimum_sample_per_strategy,
        status=payload.status.value,
        created_by_user_id=actor.user_id,
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.get("/experiments", response_model=list[ControlledExperimentRead])
async def list_experiments(session: SessionDep, actor: ActorDep) -> list[models.ControlledExperiment]:
    require_role(actor, TEACHER_ROLES)
    return await repositories.list_for_organization(
        session, models.ControlledExperiment, actor.organization_id, order_by=models.ControlledExperiment.created_at.desc()
    )


@router.post("/experiments/{experiment_id}/start", response_model=ControlledExperimentRead)
async def start_experiment(
    experiment_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> models.ControlledExperiment:
    require_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(
        session, models.ControlledExperiment, actor.organization_id, experiment_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "EXPERIMENT_NOT_FOUND"})
    entity.status = ExperimentStatus.RUNNING.value
    entity.started_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/experiments/{experiment_id}/assign", response_model=ExperimentAssignmentResult)
async def assign_experiment_strategy(
    experiment_id: uuid.UUID,
    payload: ExperimentAssignmentInput,
    session: SessionDep,
    actor: ActorDep,
) -> ExperimentAssignmentResult:
    require_role(actor, TEACHER_ROLES)
    experiment = await repositories.get_for_organization(
        session, models.ControlledExperiment, actor.organization_id, experiment_id
    )
    if not experiment or experiment.status != ExperimentStatus.RUNNING.value:
        raise HTTPException(status_code=404, detail={"code": "RUNNING_EXPERIMENT_NOT_FOUND"})
    existing_result = await session.execute(
        select(models.ExperimentAssignment).where(
            models.ExperimentAssignment.organization_id == actor.organization_id,
            models.ExperimentAssignment.experiment_id == experiment_id,
            models.ExperimentAssignment.participant_id == payload.participant_id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return ExperimentAssignmentResult(
            experiment_id=experiment_id,
            participant_id=payload.participant_id,
            strategy_key=existing.strategy_key,
            assignment_strategy=AssignmentStrategy(existing.assignment_strategy),
        )
    keys = [item["key"] for item in experiment.strategies]
    key = deterministic_strategy_assignment(
        experiment_id=str(experiment_id), participant_id=str(payload.participant_id), strategy_keys=keys
    )
    assignment = models.ExperimentAssignment(
        organization_id=actor.organization_id,
        experiment_id=experiment_id,
        participant_id=payload.participant_id,
        strategy_key=key,
        assignment_strategy=AssignmentStrategy.DETERMINISTIC_HASH.value,
    )
    session.add(assignment)
    await session.commit()
    return ExperimentAssignmentResult(
        experiment_id=experiment_id,
        participant_id=payload.participant_id,
        strategy_key=key,
        assignment_strategy=AssignmentStrategy.DETERMINISTIC_HASH,
    )


@router.post("/experiments/{experiment_id}/observations", status_code=201)
async def create_experiment_observation(
    experiment_id: uuid.UUID,
    payload: ExperimentObservationCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, str]:
    require_role(actor, TEACHER_ROLES)
    experiment = await repositories.get_for_organization(
        session, models.ControlledExperiment, actor.organization_id, experiment_id
    )
    if not experiment:
        raise HTTPException(status_code=404, detail={"code": "EXPERIMENT_NOT_FOUND"})
    valid_keys = {item["key"] for item in experiment.strategies}
    if payload.strategy_key not in valid_keys:
        raise HTTPException(status_code=422, detail={"code": "INVALID_EXPERIMENT_STRATEGY"})
    entity = models.ExperimentObservation(
        organization_id=actor.organization_id,
        experiment_id=experiment_id,
        participant_id=payload.participant_id,
        strategy_key=payload.strategy_key,
        metric_value=payload.metric_value,
        completed=payload.completed,
        metadata_payload=payload.metadata,
    )
    session.add(entity)
    await session.commit()
    return {"id": str(entity.id), "status": "registered"}


@router.get("/experiments/{experiment_id}/comparison", response_model=ExperimentComparisonResult)
async def experiment_comparison(
    experiment_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> ExperimentComparisonResult:
    require_role(actor, TEACHER_ROLES)
    experiment = await repositories.get_for_organization(
        session, models.ControlledExperiment, actor.organization_id, experiment_id
    )
    if not experiment:
        raise HTTPException(status_code=404, detail={"code": "EXPERIMENT_NOT_FOUND"})
    result = await session.execute(
        select(models.ExperimentObservation).where(
            models.ExperimentObservation.organization_id == actor.organization_id,
            models.ExperimentObservation.experiment_id == experiment_id,
        )
    )
    observations = [
        {
            "strategy_key": item.strategy_key,
            "metric_value": item.metric_value,
            "completed": item.completed,
        }
        for item in result.scalars().all()
    ]
    return compare_experiment_strategies(
        experiment_id=str(experiment_id),
        primary_metric=experiment.primary_metric,
        metric_direction=MetricDirection(experiment.metric_direction),
        minimum_sample_per_strategy=experiment.minimum_sample_per_strategy,
        strategy_keys=[item["key"] for item in experiment.strategies],
        observations=observations,
    )


@router.post("/institutional-paths/dashboard", response_model=InstitutionalPathDashboardResult)
async def institutional_dashboard(
    payload: InstitutionalPathDashboardInput, actor: ActorDep
) -> InstitutionalPathDashboardResult:
    require_role(actor, TEACHER_ROLES)
    return build_institutional_path_dashboard(payload)
