from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import AnalyticsModelStatus, AnalyticsRunStatus, ExportStatus, ReportStatus
from .policies import (
    analyze_distractors,
    calculate_discrimination,
    calculate_facility,
    classify_item_flags,
    cronbach_alpha,
    observed_difficulty_from_facility,
    point_biserial,
    privacy_guard,
    stable_hash,
)
from .schemas import (
    AnalyticsModelCreate,
    AnalyticsModelRead,
    AnalyticsRunCreate,
    AnalyticsRunRead,
    DistractorAnalysisRequest,
    ItemAnalysisRequest,
    ItemAnalysisResult,
    PrivacyCheckRequest,
    ReliabilityRequest,
    ReportDefinitionCreate,
    ReportDefinitionRead,
    ReportExportCreate,
    ReportExportRead,
)

router = APIRouter(prefix="/assessment-analytics", tags=["assessment-analytics"])
SessionDep = Annotated[Any, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]
ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
ANALYTICS_ROLES = ADMIN_ROLES | {"TEACHER", "COORDINATOR", "PEDAGOGICAL_COORDINATOR"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    actor_roles = {str(item).upper() for item in actor.roles}
    if not actor_roles.intersection(allowed):
        raise HTTPException(status_code=403, detail="Permissao insuficiente para analytics de avaliacoes.")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "15.5", "module": "assessment-analytics"}


@router.post("/simulate/item", response_model=ItemAnalysisResult)
async def simulate_item(payload: ItemAnalysisRequest, actor: ActorDep) -> ItemAnalysisResult:
    require_role(actor, ANALYTICS_ROLES)
    sample_size = len(payload.item_scores)
    facility = calculate_facility(sum(payload.item_scores), sample_size - payload.omitted)
    observed = observed_difficulty_from_facility(facility)
    discrimination = calculate_discrimination(
        payload.upper_correct, payload.upper_total, payload.lower_correct, payload.lower_total
    )
    biserial = point_biserial(payload.item_scores, payload.total_scores)
    omission_rate = round(payload.omitted / sample_size, 4) if sample_size else 0.0
    delta = None
    if payload.predicted_difficulty is not None and observed is not None:
        delta = round(observed - payload.predicted_difficulty, 4)
    flags = classify_item_flags(
        sample_size=sample_size,
        facility_index=facility,
        discrimination_index=discrimination,
        omission_rate=omission_rate,
        predicted_difficulty=payload.predicted_difficulty,
        observed_difficulty=observed,
        minimum_sample=payload.minimum_sample,
    )
    return ItemAnalysisResult(
        sample_size=sample_size,
        facility_index=facility,
        observed_difficulty=observed,
        difficulty_delta=delta,
        discrimination_index=discrimination,
        point_biserial=biserial,
        omission_rate=omission_rate,
        flags=flags,
    )


@router.post("/simulate/distractors")
async def simulate_distractors(payload: DistractorAnalysisRequest, actor: ActorDep) -> list[dict[str, Any]]:
    require_role(actor, ANALYTICS_ROLES)
    return analyze_distractors(
        payload.selections, payload.correct_option, minimum_functioning_rate=payload.minimum_functioning_rate
    )


@router.post("/simulate/reliability")
async def simulate_reliability(payload: ReliabilityRequest, actor: ActorDep) -> dict[str, float | None]:
    require_role(actor, ANALYTICS_ROLES)
    return {"cronbach_alpha": cronbach_alpha(payload.score_matrix)}


@router.post("/privacy/check")
async def check_privacy(payload: PrivacyCheckRequest, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, ANALYTICS_ROLES)
    return privacy_guard(payload.sample_size, payload.minimum_group_size)


@router.post("/models", response_model=AnalyticsModelRead, status_code=status.HTTP_201_CREATED)
async def create_model(payload: AnalyticsModelCreate, session: SessionDep, actor: ActorDep) -> AnalyticsModelRead:
    require_role(actor, ADMIN_ROLES)
    configuration_hash = stable_hash(payload.model_dump(mode="json"))
    item = models.AssessmentAnalyticsModel(
        organization_id=actor.organization_id,
        code=payload.code,
        name=payload.name,
        version=payload.version,
        status=AnalyticsModelStatus.DRAFT,
        description=payload.description,
        configuration=payload.configuration,
        privacy_rules=payload.privacy_rules,
        metric_definitions=payload.metric_definitions,
        configuration_hash=configuration_hash,
        is_default=payload.is_default,
        created_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/models", response_model=list[AnalyticsModelRead])
async def list_models(session: SessionDep, actor: ActorDep) -> list[AnalyticsModelRead]:
    require_role(actor, ANALYTICS_ROLES)
    result = await session.execute(
        select(models.AssessmentAnalyticsModel)
        .where(models.AssessmentAnalyticsModel.organization_id == actor.organization_id)
        .order_by(models.AssessmentAnalyticsModel.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/models/{model_id}/publish", response_model=AnalyticsModelRead)
async def publish_model(model_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> AnalyticsModelRead:
    require_role(actor, ADMIN_ROLES)
    item = await session.scalar(select(models.AssessmentAnalyticsModel).where(
        models.AssessmentAnalyticsModel.organization_id == actor.organization_id,
        models.AssessmentAnalyticsModel.id == model_id,
    ))
    if not item:
        raise HTTPException(404, "Modelo de analytics nao encontrado.")
    item.status = AnalyticsModelStatus.PUBLISHED
    item.published_by_user_id = actor.user_id
    item.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/runs", response_model=AnalyticsRunRead, status_code=status.HTTP_201_CREATED)
async def create_run(payload: AnalyticsRunCreate, session: SessionDep, actor: ActorDep) -> AnalyticsRunRead:
    require_role(actor, ANALYTICS_ROLES)
    model = await session.scalar(select(models.AssessmentAnalyticsModel).where(
        models.AssessmentAnalyticsModel.organization_id == actor.organization_id,
        models.AssessmentAnalyticsModel.id == payload.analytics_model_id,
    ))
    if not model:
        raise HTTPException(404, "Modelo de analytics nao encontrado.")
    if model.status != AnalyticsModelStatus.PUBLISHED:
        raise HTTPException(409, "Somente modelos publicados podem executar analytics.")
    item = models.AssessmentAnalyticsRun(
        organization_id=actor.organization_id,
        analytics_model_id=model.id,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        status=AnalyticsRunStatus.QUEUED,
        requested_by_user_id=actor.user_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        filters=payload.filters,
        input_snapshot={"model_hash": model.configuration_hash, "filters": payload.filters},
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/runs", response_model=list[AnalyticsRunRead])
async def list_runs(
    session: SessionDep, actor: ActorDep, limit: int = Query(default=50, ge=1, le=200)
) -> list[AnalyticsRunRead]:
    require_role(actor, ANALYTICS_ROLES)
    result = await session.execute(
        select(models.AssessmentAnalyticsRun)
        .where(models.AssessmentAnalyticsRun.organization_id == actor.organization_id)
        .order_by(models.AssessmentAnalyticsRun.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/reports", response_model=ReportDefinitionRead, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ReportDefinitionCreate, session: SessionDep, actor: ActorDep) -> ReportDefinitionRead:
    require_role(actor, ADMIN_ROLES)
    item = models.AssessmentReportDefinition(
        organization_id=actor.organization_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=ReportStatus.DRAFT,
        audience=payload.audience,
        sections=payload.sections,
        filters=payload.filters,
        privacy_rules=payload.privacy_rules,
        created_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/reports", response_model=list[ReportDefinitionRead])
async def list_reports(session: SessionDep, actor: ActorDep) -> list[ReportDefinitionRead]:
    require_role(actor, ANALYTICS_ROLES)
    result = await session.execute(
        select(models.AssessmentReportDefinition)
        .where(models.AssessmentReportDefinition.organization_id == actor.organization_id)
        .order_by(models.AssessmentReportDefinition.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/exports", response_model=ReportExportRead, status_code=status.HTTP_201_CREATED)
async def create_export(payload: ReportExportCreate, session: SessionDep, actor: ActorDep) -> ReportExportRead:
    require_role(actor, ANALYTICS_ROLES)
    report = await session.scalar(select(models.AssessmentReportDefinition).where(
        models.AssessmentReportDefinition.organization_id == actor.organization_id,
        models.AssessmentReportDefinition.id == payload.report_definition_id,
    ))
    if not report:
        raise HTTPException(404, "Relatorio nao encontrado.")
    item = models.AssessmentReportExport(
        organization_id=actor.organization_id,
        report_definition_id=report.id,
        analytics_run_id=payload.analytics_run_id,
        requested_by_user_id=actor.user_id,
        status=ExportStatus.QUEUED,
        format=payload.format,
        parameters=payload.parameters,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item
