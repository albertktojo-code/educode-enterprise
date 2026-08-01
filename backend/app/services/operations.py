from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

try:
    from redis.asyncio import Redis
    from redis.exceptions import RedisError
except ImportError:  # Allows diagnostics before optional worker dependencies are installed.
    Redis = Any  # type: ignore[misc,assignment]

    class RedisError(RuntimeError):
        pass

    class _MissingRedisClient:
        async def ping(self):
            raise RedisError("Pacote redis não instalado")

        async def lpush(self, *args, **kwargs):
            raise RedisError("Pacote redis não instalado")

        async def publish(self, *args, **kwargs):
            raise RedisError("Pacote redis não instalado")

        async def aclose(self):
            return None


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.ai_runtime import AIGenerationRequest, AIGenerationResult
from app.models.observability import OrganizationQuota
from app.models.operations import (
    BackgroundJob,
    BackgroundJobEvent,
    JobDependency,
    JobNotification,
    ResourceReservation,
    SemanticCacheEntry,
)

TERMINAL_STATUSES = {"completed", "failed", "cancelled", "expired"}
ACTIVE_STATUSES = {"pending", "queued", "processing", "waiting_provider", "validating", "retrying"}
SUPPORTED_JOB_TYPES = {
    "ai_generation",
    "media_generation",
    "anime_render",
    "accessibility_generation",
    "document_processing",
    "document_indexing",
    "analytics_refresh",
    "assessment_recalculation",
    "intervention_refresh",
    "statistical_report",
    "assessment_import",
    "file_export",
    "generic_operation",
    "platform_backup",
    "platform_restore_test",
    "platform_integrity",
}
TRANSIENT_MARKERS = (
    "timeout",
    "temporarily unavailable",
    "connection reset",
    "connection refused",
    "rate limit",
    "redis",
    "503",
    "502",
    "504",
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def queue_for_job_type(job_type: str) -> str:
    normalized = job_type.lower()
    if normalized.startswith("ai_") or normalized in {
        "media_generation",
        "accessibility_generation",
    }:
        return "ai"
    if normalized in {
        "document_processing",
        "document_indexing",
        "statistical_report",
        "assessment_import",
        "file_export",
    }:
        return "documents"
    if normalized in {"analytics_refresh", "assessment_recalculation", "intervention_refresh"}:
        return "analytics"
    return "default"


def build_idempotency_key(
    *,
    organization_id: UUID,
    job_type: str,
    entity_id: UUID | None,
    input_snapshot: dict[str, Any],
) -> str:
    payload = {
        "organization_id": str(organization_id),
        "job_type": job_type,
        "entity_id": str(entity_id) if entity_id else None,
        "input": input_snapshot,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"{job_type}:{digest}"


def retry_delay_seconds(retry_count: int) -> int:
    schedule = (0, 30, 120, 600, 1800, 3600)
    return schedule[min(max(retry_count, 0), len(schedule) - 1)]


def is_transient_error(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in message for marker in TRANSIENT_MARKERS)


def priority_bucket(priority: int) -> str:
    if priority >= 90:
        return "urgent"
    if priority >= 70:
        return "high"
    if priority < 30:
        return "low"
    return "normal"


def redis_key(queue_name: str, bucket: str = "normal") -> str:
    settings = get_settings()
    return f"{settings.job_queue_prefix}:queue:{queue_name}:{bucket}"


def redis_event_channel(job_id: UUID) -> str:
    settings = get_settings()
    return f"{settings.job_queue_prefix}:events:{job_id}"


def get_redis() -> Redis:
    if hasattr(Redis, "from_url"):
        return Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _MissingRedisClient()


async def redis_is_available() -> bool:
    client = get_redis()
    try:
        return bool(await client.ping())
    except RedisError:
        return False
    finally:
        await client.aclose()


async def create_job(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    job_type: str,
    module_name: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    ai_flow_id: str | None = None,
    priority: int = 50,
    total_steps: int = 1,
    max_retries: int = 3,
    idempotency_key: str | None = None,
    input_snapshot: dict[str, Any] | None = None,
    estimated_cost: float = 0.0,
    depends_on_job_ids: list[UUID] | None = None,
) -> tuple[BackgroundJob, bool]:
    if job_type not in SUPPORTED_JOB_TYPES:
        raise ValueError("Tipo de tarefa não suportado")
    snapshot = input_snapshot or {}
    key = idempotency_key or build_idempotency_key(
        organization_id=organization_id,
        job_type=job_type,
        entity_id=entity_id,
        input_snapshot=snapshot,
    )
    existing = await session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.idempotency_key == key,
        )
    )
    if existing is not None:
        return existing, False
    active_count = await session.scalar(
        select(func.count(BackgroundJob.id)).where(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.requested_by_user_id == user_id,
            BackgroundJob.status.in_(list(ACTIVE_STATUSES)),
        )
    )
    active_count_value = int(active_count or 0)
    if active_count_value >= get_settings().max_concurrent_jobs_per_user:
        raise ValueError("Limite de tarefas simultâneas do usuário atingido")
    organization_active_count = int(
        await session.scalar(
            select(func.count(BackgroundJob.id)).where(
                BackgroundJob.organization_id == organization_id,
                BackgroundJob.status.in_(list(ACTIVE_STATUSES)),
            )
        )
        or 0
    )
    active_jobs_quota = await session.scalar(
        select(OrganizationQuota).where(
            OrganizationQuota.organization_id == organization_id,
            OrganizationQuota.quota_key == "jobs.active",
            OrganizationQuota.is_active.is_(True),
        )
    )
    if (
        active_jobs_quota is not None
        and active_jobs_quota.enforcement_mode == "block"
        and organization_active_count >= active_jobs_quota.limit_value
    ):
        raise ValueError("Quota institucional de tarefas simultâneas atingida")
    if estimated_cost > 0:
        cost_quota = await session.scalar(
            select(OrganizationQuota).where(
                OrganizationQuota.organization_id == organization_id,
                OrganizationQuota.quota_key == "ai.cost.monthly",
                OrganizationQuota.is_active.is_(True),
            )
        )
        if cost_quota is not None and cost_quota.enforcement_mode == "block":
            month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            reserved_cost = float(
                await session.scalar(
                    select(func.coalesce(func.sum(ResourceReservation.reserved_cost), 0.0)).where(
                        ResourceReservation.organization_id == organization_id,
                        ResourceReservation.created_at >= month_start,
                        ResourceReservation.status.in_(["reserved", "consumed"]),
                    )
                )
                or 0.0
            )
            if reserved_cost + estimated_cost > cost_quota.limit_value:
                raise ValueError("Quota mensal de custo de IA excedida")
    queue_name = queue_for_job_type(job_type)
    job = BackgroundJob(
        organization_id=organization_id,
        requested_by_user_id=user_id,
        job_type=job_type,
        queue_name=queue_name,
        module_name=module_name,
        entity_type=entity_type,
        entity_id=entity_id,
        ai_flow_id=ai_flow_id,
        status="pending",
        priority=priority,
        total_steps=total_steps,
        idempotency_key=key,
        input_snapshot=snapshot,
        max_retries=max_retries,
    )
    session.add(job)
    await session.flush()
    for dependency_id in depends_on_job_ids or []:
        dependency = await session.get(BackgroundJob, dependency_id)
        if dependency is None or dependency.organization_id != organization_id:
            raise ValueError("Dependência de tarefa inválida")
        session.add(
            JobDependency(
                organization_id=organization_id,
                job_id=job.id,
                depends_on_job_id=dependency_id,
            )
        )
    if estimated_cost > 0:
        session.add(
            ResourceReservation(
                organization_id=organization_id,
                job_id=job.id,
                resource_type="ai_budget",
                reserved_cost=estimated_cost,
                expires_at=utcnow() + timedelta(hours=6),
            )
        )
    await add_job_event(
        session,
        job=job,
        event_type="job.created",
        event_data={"queue": queue_name, "priority": priority},
        publish=False,
    )
    return job, True


async def add_job_event(
    session: AsyncSession,
    *,
    job: BackgroundJob,
    event_type: str,
    event_data: dict[str, Any] | None = None,
    publish: bool = True,
) -> BackgroundJobEvent:
    event = BackgroundJobEvent(
        organization_id=job.organization_id,
        job_id=job.id,
        event_type=event_type,
        event_data=event_data or {},
    )
    session.add(event)
    await session.flush()
    if publish:
        client = get_redis()
        try:
            await client.publish(
                redis_event_channel(job.id),
                json.dumps(
                    {
                        "id": str(event.id),
                        "job_id": str(job.id),
                        "event_type": event_type,
                        "event_data": event.event_data,
                        "created_at": utcnow().isoformat(),
                    },
                    default=str,
                    ensure_ascii=False,
                ),
            )
        except RedisError:
            pass
        finally:
            await client.aclose()
    return event


async def push_job(job: BackgroundJob) -> bool:
    client = get_redis()
    try:
        payload = json.dumps({"job_id": str(job.id), "priority": job.priority}, ensure_ascii=False)
        await client.lpush(redis_key(job.queue_name, priority_bucket(job.priority)), payload)
        return True
    except RedisError:
        return False
    finally:
        await client.aclose()


async def mark_queued(session: AsyncSession, job: BackgroundJob) -> bool:
    available = await push_job(job)
    job.status = "queued" if available else "pending"
    job.queued_at = utcnow() if available else None
    job.current_step = "Na fila" if available else "Aguardando Redis"
    await add_job_event(
        session,
        job=job,
        event_type="job.queued" if available else "job.queue_unavailable",
        event_data={"queue": job.queue_name},
        publish=available,
    )
    return available


async def create_job_notification(
    session: AsyncSession,
    *,
    job: BackgroundJob,
    notification_type: str,
    title: str,
    message: str,
) -> JobNotification:
    notification = JobNotification(
        organization_id=job.organization_id,
        user_id=job.requested_by_user_id,
        job_id=job.id,
        notification_type=notification_type,
        title=title,
        message=message,
        action_path=f"/tarefas/{job.id}",
    )
    session.add(notification)
    return notification


async def dependencies_satisfied(session: AsyncSession, job_id: UUID) -> bool:
    rows = list(
        (await session.scalars(select(JobDependency).where(JobDependency.job_id == job_id))).all()
    )
    for row in rows:
        dependency = await session.get(BackgroundJob, row.depends_on_job_id)
        if dependency is None or dependency.status != row.required_status:
            return False
    return True


def semantic_cache_key(request: AIGenerationRequest) -> str:
    fingerprint = {
        "organization_id": str(request.organization_id),
        "module_name": request.module_name,
        "action_name": request.action_name,
        "request_type": request.request_type,
        "model_id": str(request.model_id) if request.model_id else None,
        "prompt_template_id": str(request.prompt_template_id)
        if request.prompt_template_id
        else None,
        "rag_context_id": str(request.rag_context_id) if request.rag_context_id else None,
        "input": request.input_snapshot,
        "parameters": {
            key: value
            for key, value in request.parameters.items()
            if key not in {"priority", "max_retries", "reuse_cache"}
        },
    }
    return hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


async def find_cached_result(
    session: AsyncSession, request: AIGenerationRequest
) -> AIGenerationResult | None:
    key = semantic_cache_key(request)
    now = utcnow()
    entry = await session.scalar(
        select(SemanticCacheEntry).where(
            SemanticCacheEntry.organization_id == request.organization_id,
            SemanticCacheEntry.cache_key == key,
            (SemanticCacheEntry.expires_at.is_(None)) | (SemanticCacheEntry.expires_at > now),
        )
    )
    if entry is None or entry.result_id is None:
        return None
    result = await session.get(AIGenerationResult, entry.result_id)
    if result is None or (entry.approved_only and result.review_status != "approved"):
        return None
    entry.hit_count += 1
    return result


async def register_cached_result(
    session: AsyncSession, request: AIGenerationRequest, result: AIGenerationResult
) -> SemanticCacheEntry:
    key = semantic_cache_key(request)
    entry = await session.scalar(
        select(SemanticCacheEntry).where(
            SemanticCacheEntry.organization_id == request.organization_id,
            SemanticCacheEntry.cache_key == key,
        )
    )
    if entry is None:
        entry = SemanticCacheEntry(
            organization_id=request.organization_id,
            module_name=request.module_name,
            action_name=request.action_name,
            cache_key=key,
            request_fingerprint={
                "request_type": request.request_type,
                "model_id": str(request.model_id) if request.model_id else None,
                "prompt_template_id": str(request.prompt_template_id)
                if request.prompt_template_id
                else None,
                "rag_context_id": str(request.rag_context_id) if request.rag_context_id else None,
            },
            result_id=result.id,
            approved_only=True,
            expires_at=utcnow() + timedelta(days=30),
        )
        session.add(entry)
    else:
        entry.result_id = result.id
        entry.expires_at = utcnow() + timedelta(days=30)
    return entry


async def average_completion_seconds(session: AsyncSession, organization_id: UUID) -> float:
    rows = list(
        (
            await session.scalars(
                select(BackgroundJob)
                .where(
                    BackgroundJob.organization_id == organization_id,
                    BackgroundJob.status == "completed",
                    BackgroundJob.started_at.is_not(None),
                    BackgroundJob.completed_at.is_not(None),
                )
                .limit(500)
            )
        ).all()
    )
    durations = [
        (row.completed_at - row.started_at).total_seconds()
        for row in rows
        if row.completed_at and row.started_at
    ]
    return round(sum(durations) / len(durations), 2) if durations else 0.0


async def status_counts(session: AsyncSession, organization_id: UUID) -> dict[str, int]:
    result = await session.execute(
        select(BackgroundJob.status, func.count(BackgroundJob.id))
        .where(BackgroundJob.organization_id == organization_id)
        .group_by(BackgroundJob.status)
    )
    return {status: int(count) for status, count in result.all()}
