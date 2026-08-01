from __future__ import annotations

import math
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.ai_runtime import AIUsageRecord
from app.models.assessment import Assessment
from app.models.auth import Membership, User
from app.models.document import Document
from app.models.education import Classroom, Project
from app.models.operations import BackgroundJob, WorkerHeartbeat
from app.models.observability import (
    DataReconciliationRun,
    DiagnosticRun,
    OperationalAlertEvent,
    OperationalAlertRule,
    OperationalMetricSnapshot,
    OrganizationQuota,
    SLODefinition,
)
from app.models.platform import ServiceHealthSnapshot, SystemIncident
from app.services.platform import (
    configuration_warnings,
    current_migration,
    database_status,
    integrity_report,
    redis_status,
    storage_status,
    worker_status,
)


class RequestMetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests_total: dict[tuple[str, str, int], int] = defaultdict(int)
        self._durations_ms: list[float] = []
        self._active_requests = 0
        self._exceptions_total = 0

    def begin(self) -> None:
        with self._lock:
            self._active_requests += 1

    def finish(self, method: str, route: str, status_code: int, duration_ms: float, *, exception: bool = False) -> None:
        normalized_route = normalize_route(route)
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            self._requests_total[(method, normalized_route, status_code)] += 1
            self._durations_ms.append(duration_ms)
            if len(self._durations_ms) > 10000:
                self._durations_ms = self._durations_ms[-5000:]
            if exception:
                self._exceptions_total += 1

    def summary(self) -> dict[str, float]:
        with self._lock:
            values = sorted(self._durations_ms)
            total = sum(self._requests_total.values())
            error_total = sum(count for (_, _, status), count in self._requests_total.items() if status >= 500)
            return {
                "requests_total": float(total),
                "active_requests": float(self._active_requests),
                "exceptions_total": float(self._exceptions_total),
                "error_rate_percent": round((error_total / total * 100) if total else 0.0, 3),
                "latency_avg_ms": round(sum(values) / len(values), 2) if values else 0.0,
                "latency_p95_ms": round(percentile(values, 0.95), 2) if values else 0.0,
                "latency_p99_ms": round(percentile(values, 0.99), 2) if values else 0.0,
            }

    def prometheus_text(self, *, app_version: str, environment: str) -> str:
        with self._lock:
            lines = [
                "# HELP educode_info Informações da versão do EduCode.",
                "# TYPE educode_info gauge",
                f'educode_info{{version="{escape_label(app_version)}",environment="{escape_label(environment)}"}} 1',
                "# HELP educode_http_requests_total Total de requisições HTTP.",
                "# TYPE educode_http_requests_total counter",
            ]
            for (method, route, status), count in sorted(self._requests_total.items()):
                lines.append(
                    f'educode_http_requests_total{{method="{escape_label(method)}",route="{escape_label(route)}",status="{status}"}} {count}'
                )
            lines.extend([
                "# HELP educode_http_active_requests Requisições HTTP ativas.",
                "# TYPE educode_http_active_requests gauge",
                f"educode_http_active_requests {self._active_requests}",
                "# HELP educode_http_exceptions_total Exceções HTTP não tratadas.",
                "# TYPE educode_http_exceptions_total counter",
                f"educode_http_exceptions_total {self._exceptions_total}",
            ])
            summary = self.summary_unlocked()
            for key in ("latency_avg_ms", "latency_p95_ms", "latency_p99_ms", "error_rate_percent"):
                metric_name = f"educode_http_{key}"
                lines.extend([f"# TYPE {metric_name} gauge", f"{metric_name} {summary[key]}"])
            return "\n".join(lines) + "\n"

    def summary_unlocked(self) -> dict[str, float]:
        values = sorted(self._durations_ms)
        total = sum(self._requests_total.values())
        error_total = sum(count for (_, _, status), count in self._requests_total.items() if status >= 500)
        return {
            "requests_total": float(total),
            "active_requests": float(self._active_requests),
            "exceptions_total": float(self._exceptions_total),
            "error_rate_percent": round((error_total / total * 100) if total else 0.0, 3),
            "latency_avg_ms": round(sum(values) / len(values), 2) if values else 0.0,
            "latency_p95_ms": round(percentile(values, 0.95), 2) if values else 0.0,
            "latency_p99_ms": round(percentile(values, 0.99), 2) if values else 0.0,
        }


REQUEST_METRICS = RequestMetricsRegistry()


def utcnow() -> datetime:
    return datetime.now(UTC)


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, math.ceil(len(values) * ratio) - 1))
    return float(values[index])


def normalize_route(path: str) -> str:
    parts = []
    for part in path.split("/"):
        if not part:
            continue
        if len(part) >= 32 and "-" in part:
            parts.append("{id}")
        elif part.isdigit():
            parts.append("{id}")
        else:
            parts.append(part)
    return "/" + "/".join(parts)


def escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def compare(value: float, comparator: str, target: float) -> bool:
    if comparator == ">":
        return value > target
    if comparator == ">=":
        return value >= target
    if comparator == "<":
        return value < target
    if comparator == "<=":
        return value <= target
    if comparator == "==":
        return math.isclose(value, target, rel_tol=1e-9, abs_tol=1e-9)
    raise ValueError(f"Comparador não suportado: {comparator}")


async def collect_operational_metrics(session: AsyncSession, organization_id: UUID) -> dict[str, tuple[float, str]]:
    now = utcnow()
    day_ago = now - timedelta(hours=24)
    active_statuses = ["pending", "queued", "processing", "waiting_provider", "validating", "retrying"]
    active_jobs = int(await session.scalar(select(func.count(BackgroundJob.id)).where(
        BackgroundJob.organization_id == organization_id,
        BackgroundJob.status.in_(active_statuses),
    )) or 0)
    failed_jobs = int(await session.scalar(select(func.count(BackgroundJob.id)).where(
        BackgroundJob.organization_id == organization_id,
        BackgroundJob.status == "failed",
        BackgroundJob.completed_at >= day_ago,
    )) or 0)
    completed_jobs = int(await session.scalar(select(func.count(BackgroundJob.id)).where(
        BackgroundJob.organization_id == organization_id,
        BackgroundJob.status == "completed",
        BackgroundJob.completed_at >= day_ago,
    )) or 0)
    stale_cutoff = now - timedelta(seconds=45)
    active_workers = int(await session.scalar(select(func.count(WorkerHeartbeat.id)).where(
        WorkerHeartbeat.last_seen_at >= stale_cutoff,
    )) or 0)
    open_incidents = int(await session.scalar(select(func.count(SystemIncident.id)).where(
        SystemIncident.organization_id == organization_id,
        SystemIncident.status.not_in(["resolved", "closed"]),
    )) or 0)
    open_alerts = int(await session.scalar(select(func.count(OperationalAlertEvent.id)).where(
        OperationalAlertEvent.organization_id == organization_id,
        OperationalAlertEvent.status.in_(["open", "acknowledged"]),
    )) or 0)
    http = REQUEST_METRICS.summary()
    processed = completed_jobs + failed_jobs
    job_failure_rate = (failed_jobs / processed * 100) if processed else 0.0
    metrics = {
        "http.requests_total": (http["requests_total"], "count"),
        "http.error_rate_percent": (http["error_rate_percent"], "percent"),
        "http.latency_p95_ms": (http["latency_p95_ms"], "milliseconds"),
        "http.latency_p99_ms": (http["latency_p99_ms"], "milliseconds"),
        "jobs.active": (float(active_jobs), "count"),
        "jobs.failed_24h": (float(failed_jobs), "count"),
        "jobs.failure_rate_percent": (round(job_failure_rate, 3), "percent"),
        "workers.active": (float(active_workers), "count"),
        "incidents.open": (float(open_incidents), "count"),
        "alerts.open": (float(open_alerts), "count"),
    }
    return metrics


async def persist_metric_snapshots(session: AsyncSession, organization_id: UUID) -> dict[str, tuple[float, str]]:
    metrics = await collect_operational_metrics(session, organization_id)
    for name, (value, unit) in metrics.items():
        session.add(OperationalMetricSnapshot(
            organization_id=organization_id,
            metric_name=name,
            metric_value=value,
            unit=unit,
            labels={},
            source="educode-runtime",
        ))
    await session.flush()
    return metrics


async def evaluate_slos(session: AsyncSession, organization_id: UUID) -> list[dict[str, Any]]:
    definitions = list((await session.scalars(select(SLODefinition).where(
        SLODefinition.organization_id == organization_id,
        SLODefinition.is_active.is_(True),
    ).order_by(SLODefinition.name))).all())
    results: list[dict[str, Any]] = []
    now = utcnow()
    for slo in definitions:
        cutoff = now - timedelta(minutes=slo.window_minutes)
        values = list((await session.scalars(select(OperationalMetricSnapshot.metric_value).where(
            OperationalMetricSnapshot.organization_id == organization_id,
            OperationalMetricSnapshot.metric_name == slo.metric_name,
            OperationalMetricSnapshot.measured_at >= cutoff,
        ).order_by(OperationalMetricSnapshot.measured_at))).all())
        if len(values) < slo.minimum_samples:
            status = "insufficient_data"
            observed = None
            remaining = None
        else:
            observed = float(sum(values) / len(values))
            status = "met" if compare(observed, slo.comparator, slo.target_value) else "violated"
            if slo.target_value == 0:
                remaining = 100.0 if status == "met" else 0.0
            elif slo.comparator in {">", ">="}:
                remaining = max(0.0, min(100.0, observed / slo.target_value * 100))
            else:
                remaining = max(0.0, min(100.0, (2 - observed / slo.target_value) * 100))
        results.append({
            "slo_id": slo.id,
            "slo_key": slo.slo_key,
            "name": slo.name,
            "metric_name": slo.metric_name,
            "target_value": slo.target_value,
            "observed_value": observed,
            "comparator": slo.comparator,
            "sample_count": len(values),
            "status": status,
            "error_budget_remaining_percent": round(remaining, 2) if remaining is not None else None,
            "window_minutes": slo.window_minutes,
        })
    return results


async def evaluate_alert_rules(session: AsyncSession, organization_id: UUID) -> list[OperationalAlertEvent]:
    metrics = await collect_operational_metrics(session, organization_id)
    rules = list((await session.scalars(select(OperationalAlertRule).where(
        OperationalAlertRule.organization_id == organization_id,
        OperationalAlertRule.is_active.is_(True),
    ))).all())
    created: list[OperationalAlertEvent] = []
    now = utcnow()
    for rule in rules:
        metric = metrics.get(rule.metric_name)
        if metric is None or not compare(metric[0], rule.comparator, rule.threshold_value):
            continue
        cooldown_cutoff = now - timedelta(minutes=rule.cooldown_minutes)
        existing = await session.scalar(select(OperationalAlertEvent).where(
            OperationalAlertEvent.organization_id == organization_id,
            OperationalAlertEvent.rule_id == rule.id,
            OperationalAlertEvent.status.in_(["open", "acknowledged"]),
            OperationalAlertEvent.opened_at >= cooldown_cutoff,
        ).order_by(OperationalAlertEvent.opened_at.desc()))
        if existing is not None:
            continue
        event = OperationalAlertEvent(
            organization_id=organization_id,
            rule_id=rule.id,
            metric_name=rule.metric_name,
            observed_value=metric[0],
            threshold_value=rule.threshold_value,
            severity=rule.severity,
            title=rule.name,
            description=rule.description or f"A métrica {rule.metric_name} atingiu {metric[0]:.2f}.",
            evidence={"comparator": rule.comparator, "unit": metric[1], "evaluated_at": now.isoformat()},
        )
        session.add(event)
        created.append(event)
    await session.flush()
    return created


async def calculate_quota_usage(session: AsyncSession, organization_id: UUID) -> list[dict[str, Any]]:
    quotas = list((await session.scalars(select(OrganizationQuota).where(
        OrganizationQuota.organization_id == organization_id,
        OrganizationQuota.is_active.is_(True),
    ).order_by(OrganizationQuota.quota_key))).all())
    usage_values: dict[str, float] = {
        "users.total": float(await session.scalar(select(func.count(Membership.id)).where(
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )) or 0),
        "projects.total": float(await session.scalar(select(func.count(Project.id)).where(Project.organization_id == organization_id)) or 0),
        "classrooms.total": float(await session.scalar(select(func.count(Classroom.id)).where(Classroom.organization_id == organization_id)) or 0),
        "documents.total": float(await session.scalar(select(func.count(Document.id)).where(Document.organization_id == organization_id)) or 0),
        "assessments.total": float(await session.scalar(select(func.count(Assessment.id)).where(Assessment.organization_id == organization_id)) or 0),
        "jobs.active": float(await session.scalar(select(func.count(BackgroundJob.id)).where(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.status.in_(["pending", "queued", "processing", "waiting_provider", "validating", "retrying"]),
        )) or 0),
        "ai.cost.monthly": float(await session.scalar(select(func.coalesce(func.sum(AIUsageRecord.estimated_cost), 0.0)).where(
            AIUsageRecord.organization_id == organization_id,
            AIUsageRecord.created_at >= utcnow() - timedelta(days=30),
        )) or 0.0),
    }
    results: list[dict[str, Any]] = []
    for quota in quotas:
        used = usage_values.get(quota.quota_key, float(quota.configuration.get("manual_usage", 0.0)))
        percentage = used / quota.limit_value * 100 if quota.limit_value else 0.0
        if percentage >= 100:
            status = "exceeded"
        elif percentage >= quota.critical_percentage:
            status = "critical"
        elif percentage >= quota.warning_percentage:
            status = "warning"
        else:
            status = "normal"
        results.append({
            "quota_key": quota.quota_key,
            "limit_value": quota.limit_value,
            "used_value": round(used, 4),
            "usage_percentage": round(percentage, 2),
            "status": status,
            "enforcement_mode": quota.enforcement_mode,
            "period": quota.period,
        })
    return results


async def run_diagnostics(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    request_id: str,
    settings: Settings | None = None,
) -> DiagnosticRun:
    settings = settings or get_settings()
    started = time.perf_counter()
    db_state, db_latency, db_details = await database_status(session)
    redis_state, redis_latency, redis_details = await redis_status(settings)
    storage = storage_status(settings)
    workers = await worker_status(session)
    migration = await current_migration(session)
    checks = {
        "postgresql": {"status": db_state, "latency_ms": db_latency, **db_details},
        "redis": {"status": redis_state, "latency_ms": redis_latency, **redis_details},
        "storage": storage,
        "workers": workers,
        "migration": {"current": migration, "expected": "0025_ops_observability", "status": "healthy" if migration == "0025_ops_observability" else "degraded"},
    }
    healthy = db_state == "healthy" and redis_state == "healthy" and all(v.get("writable") for v in storage.values())
    warnings = configuration_warnings(settings)
    if workers.get("active", 0) < workers.get("total", 0):
        warnings.append("Há workers sem heartbeat recente.")
    run = DiagnosticRun(
        organization_id=organization_id,
        requested_by_user_id=user_id,
        status="completed" if healthy else "degraded",
        checks=checks,
        warnings=warnings,
        duration_ms=int((time.perf_counter() - started) * 1000),
        request_id=request_id,
        completed_at=utcnow(),
    )
    session.add(run)
    await session.flush()
    return run


async def run_reconciliation(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    run_type: str,
    repair_safe_findings: bool,
) -> DataReconciliationRun:
    run = DataReconciliationRun(
        organization_id=organization_id,
        requested_by_user_id=user_id,
        run_type=run_type,
        status="running",
        started_at=utcnow(),
    )
    session.add(run)
    await session.flush()
    findings = await integrity_report(session, organization_id)
    selected = findings if run_type == "full" else [item for item in findings if run_type in item.get("code", "")]
    repaired = 0
    # A Sprint 13.1 não corrige dados educacionais automaticamente. Somente estados operacionais seguros.
    if repair_safe_findings and run_type in {"full", "jobs"}:
        stale_cutoff = utcnow() - timedelta(minutes=30)
        stale_jobs = list((await session.scalars(select(BackgroundJob).where(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.status == "processing",
            BackgroundJob.started_at < stale_cutoff,
        ))).all())
        for job in stale_jobs:
            job.status = "pending"
            job.current_step = "Recuperado pela reconciliação"
            repaired += 1
    run.findings_count = sum(int(item.get("count", 0)) for item in selected)
    run.repaired_count = repaired
    run.summary = {"findings": selected, "repair_safe_findings": repair_safe_findings}
    run.status = "completed"
    run.completed_at = utcnow()
    return run


async def operational_overview(session: AsyncSession, organization_id: UUID, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    metrics = await persist_metric_snapshots(session, organization_id)
    await evaluate_alert_rules(session, organization_id)
    slo_results = await evaluate_slos(session, organization_id)
    quotas = await calculate_quota_usage(session, organization_id)
    db_state, db_latency, _ = await database_status(session)
    redis_state, redis_latency, _ = await redis_status(settings)
    workers = await worker_status(session)
    job_counts: dict[str, int] = {
        str(row[0]): int(row[1])
        for row in (
            await session.execute(
                select(BackgroundJob.status, func.count(BackgroundJob.id))
                .where(BackgroundJob.organization_id == organization_id)
                .group_by(BackgroundJob.status)
            )
        ).all()
    }
    incident_counts: dict[str, int] = {
        str(row[0]): int(row[1])
        for row in (
            await session.execute(
                select(SystemIncident.status, func.count(SystemIncident.id))
                .where(SystemIncident.organization_id == organization_id)
                .group_by(SystemIncident.status)
            )
        ).all()
    }
    alert_counts: dict[str, int] = {
        str(row[0]): int(row[1])
        for row in (
            await session.execute(
                select(OperationalAlertEvent.status, func.count(OperationalAlertEvent.id))
                .where(OperationalAlertEvent.organization_id == organization_id)
                .group_by(OperationalAlertEvent.status)
            )
        ).all()
    }
    slo_summary = {"met": 0, "violated": 0, "insufficient_data": 0}
    for result in slo_results:
        slo_summary[result["status"]] += 1
    dependencies = {
        "postgresql": {"status": db_state, "latency_ms": db_latency},
        "redis": {"status": redis_state, "latency_ms": redis_latency},
    }
    platform_status = "healthy"
    if db_state != "healthy" or redis_state != "healthy" or slo_summary["violated"]:
        platform_status = "degraded"
    return {
        "generated_at": utcnow(),
        "platform_status": platform_status,
        "request_metrics": REQUEST_METRICS.summary(),
        "jobs": {"status_counts": {str(k): int(v) for k, v in job_counts.items()}, "metrics": {k: v[0] for k, v in metrics.items() if k.startswith("jobs.")}},
        "workers": workers,
        "dependencies": dependencies,
        "incidents": {str(k): int(v) for k, v in incident_counts.items()},
        "alerts": {str(k): int(v) for k, v in alert_counts.items()},
        "quotas": quotas,
        "slo_summary": slo_summary,
    }
