from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.observability import (
    DataReconciliationRun,
    DiagnosticRun,
    OperationalAlertEvent,
    OperationalAlertRule,
    OperationalMetricSnapshot,
    OrganizationQuota,
    SLODefinition,
)
from app.schemas.observability import (
    AlertEventRead,
    AlertRuleRead,
    AlertRuleWrite,
    AlertStatusWrite,
    DiagnosticRead,
    MetricSeries,
    MetricSeriesPoint,
    MetricSnapshotRead,
    OperationalOverview,
    QuotaRead,
    QuotaUsage,
    QuotaWrite,
    ReconciliationCreate,
    ReconciliationRead,
    SLOEvaluation,
    SLORead,
    SLOWrite,
)
from app.services.observability import (
    REQUEST_METRICS,
    calculate_quota_usage,
    evaluate_alert_rules,
    evaluate_slos,
    operational_overview,
    persist_metric_snapshots,
    run_diagnostics,
    run_reconciliation,
    utcnow,
)

router = APIRouter(prefix="/observability", tags=["observability"])
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(
    response: Response,
    x_metrics_token: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Response:
    if settings.observability_metrics_token and x_metrics_token != settings.observability_metrics_token:
        raise HTTPException(status_code=401, detail="Token de métricas inválido")
    response = Response(
        content=REQUEST_METRICS.prometheus_text(
            app_version=settings.app_version,
            environment=settings.environment,
        ),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/overview", response_model=OperationalOverview)
async def get_overview(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> OperationalOverview:
    data = await operational_overview(session, org_id(membership))
    await session.commit()
    return OperationalOverview.model_validate(data)


@router.get("/metrics/history", response_model=list[MetricSeries])
async def metric_history(
    metric_name: list[str] = Query(default=["http.latency_p95_ms", "http.error_rate_percent"]),
    hours: int = Query(default=24, ge=1, le=720),
    limit_per_metric: int = Query(default=240, ge=10, le=2000),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[MetricSeries]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    series: list[MetricSeries] = []
    for name in list(dict.fromkeys(metric_name))[:10]:
        rows = list((await session.scalars(select(OperationalMetricSnapshot).where(
            OperationalMetricSnapshot.organization_id == org_id(membership),
            OperationalMetricSnapshot.metric_name == name,
            OperationalMetricSnapshot.measured_at >= cutoff,
        ).order_by(OperationalMetricSnapshot.measured_at.desc()).limit(limit_per_metric))).all())
        rows.reverse()
        series.append(MetricSeries(
            metric_name=name,
            unit=rows[0].unit if rows else "",
            points=[MetricSeriesPoint(measured_at=row.measured_at, value=row.metric_value) for row in rows],
        ))
    return series


@router.post("/snapshots/collect", response_model=list[MetricSnapshotRead])
async def collect_snapshots(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[OperationalMetricSnapshot]:
    before = utcnow()
    await persist_metric_snapshots(session, org_id(membership))
    await session.commit()
    return list((await session.scalars(select(OperationalMetricSnapshot).where(
        OperationalMetricSnapshot.organization_id == org_id(membership),
        OperationalMetricSnapshot.measured_at >= before,
    ).order_by(OperationalMetricSnapshot.metric_name))).all())


@router.get("/slos", response_model=list[SLORead])
async def list_slos(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[SLODefinition]:
    return list((await session.scalars(select(SLODefinition).where(
        SLODefinition.organization_id == org_id(membership)
    ).order_by(SLODefinition.name))).all())


@router.put("/slos/{slo_key}", response_model=SLORead)
async def upsert_slo(
    slo_key: str,
    payload: SLOWrite,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> SLODefinition:
    if slo_key != payload.slo_key:
        raise HTTPException(status_code=400, detail="A chave da URL deve coincidir com a chave do SLO")
    record = await session.scalar(select(SLODefinition).where(
        SLODefinition.organization_id == org_id(membership),
        SLODefinition.slo_key == slo_key,
    ))
    values = payload.model_dump()
    if record is None:
        record = SLODefinition(
            organization_id=org_id(membership),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
            **values,
        )
        session.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
        record.updated_by_user_id = user.id
    await session.commit()
    await session.refresh(record)
    return record


@router.get("/slos/evaluate", response_model=list[SLOEvaluation])
async def get_slo_evaluation(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[SLOEvaluation]:
    return [SLOEvaluation.model_validate(item) for item in await evaluate_slos(session, org_id(membership))]


@router.get("/alert-rules", response_model=list[AlertRuleRead])
async def list_alert_rules(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[OperationalAlertRule]:
    return list((await session.scalars(select(OperationalAlertRule).where(
        OperationalAlertRule.organization_id == org_id(membership)
    ).order_by(OperationalAlertRule.name))).all())


@router.put("/alert-rules/{rule_key}", response_model=AlertRuleRead)
async def upsert_alert_rule(
    rule_key: str,
    payload: AlertRuleWrite,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> OperationalAlertRule:
    if rule_key != payload.rule_key:
        raise HTTPException(status_code=400, detail="A chave da URL deve coincidir com a regra")
    record = await session.scalar(select(OperationalAlertRule).where(
        OperationalAlertRule.organization_id == org_id(membership),
        OperationalAlertRule.rule_key == rule_key,
    ))
    values = payload.model_dump()
    if record is None:
        record = OperationalAlertRule(
            organization_id=org_id(membership),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
            **values,
        )
        session.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
        record.updated_by_user_id = user.id
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/alert-rules/evaluate", response_model=list[AlertEventRead])
async def trigger_alert_evaluation(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[OperationalAlertEvent]:
    await persist_metric_snapshots(session, org_id(membership))
    created = await evaluate_alert_rules(session, org_id(membership))
    await session.commit()
    return created


@router.get("/alerts", response_model=list[AlertEventRead])
async def list_alerts(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[OperationalAlertEvent]:
    query = select(OperationalAlertEvent).where(
        OperationalAlertEvent.organization_id == org_id(membership)
    )
    if status:
        query = query.where(OperationalAlertEvent.status == status)
    return list((await session.scalars(query.order_by(OperationalAlertEvent.opened_at.desc()).limit(limit))).all())


@router.patch("/alerts/{alert_id}", response_model=AlertEventRead)
async def update_alert_status(
    alert_id: UUID,
    payload: AlertStatusWrite,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> OperationalAlertEvent:
    alert = await session.get(OperationalAlertEvent, alert_id)
    if alert is None or alert.organization_id != org_id(membership):
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    alert.status = payload.status
    if payload.status == "acknowledged":
        alert.acknowledged_by_user_id = user.id
        alert.acknowledged_at = utcnow()
    else:
        alert.resolved_by_user_id = user.id
        alert.resolved_at = utcnow()
    await session.commit()
    await session.refresh(alert)
    return alert


@router.get("/quotas", response_model=list[QuotaRead])
async def list_quotas(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[OrganizationQuota]:
    return list((await session.scalars(select(OrganizationQuota).where(
        OrganizationQuota.organization_id == org_id(membership)
    ).order_by(OrganizationQuota.quota_key))).all())


@router.put("/quotas/{quota_key}", response_model=QuotaRead)
async def upsert_quota(
    quota_key: str,
    payload: QuotaWrite,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> OrganizationQuota:
    if quota_key != payload.quota_key:
        raise HTTPException(status_code=400, detail="A chave da URL deve coincidir com a quota")
    record = await session.scalar(select(OrganizationQuota).where(
        OrganizationQuota.organization_id == org_id(membership),
        OrganizationQuota.quota_key == quota_key,
    ))
    values = payload.model_dump()
    if record is None:
        record = OrganizationQuota(
            organization_id=org_id(membership),
            updated_by_user_id=user.id,
            **values,
        )
        session.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
        record.updated_by_user_id = user.id
    await session.commit()
    await session.refresh(record)
    return record


@router.get("/quotas/usage", response_model=list[QuotaUsage])
async def quota_usage(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[QuotaUsage]:
    return [QuotaUsage.model_validate(item) for item in await calculate_quota_usage(session, org_id(membership))]


@router.post("/diagnostics", response_model=DiagnosticRead)
async def execute_diagnostics(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> DiagnosticRun:
    run = await run_diagnostics(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        request_id=getattr(request.state, "request_id", ""),
    )
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/diagnostics", response_model=list[DiagnosticRead])
async def list_diagnostics(
    limit: int = Query(default=30, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[DiagnosticRun]:
    return list((await session.scalars(select(DiagnosticRun).where(
        DiagnosticRun.organization_id == org_id(membership)
    ).order_by(DiagnosticRun.created_at.desc()).limit(limit))).all())


@router.post("/reconciliation", response_model=ReconciliationRead)
async def execute_reconciliation(
    payload: ReconciliationCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> DataReconciliationRun:
    run = await run_reconciliation(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        run_type=payload.run_type,
        repair_safe_findings=payload.repair_safe_findings,
    )
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/reconciliation", response_model=list[ReconciliationRead])
async def list_reconciliation_runs(
    limit: int = Query(default=30, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[DataReconciliationRun]:
    return list((await session.scalars(select(DataReconciliationRun).where(
        DataReconciliationRun.organization_id == org_id(membership)
    ).order_by(DataReconciliationRun.created_at.desc()).limit(limit))).all())
