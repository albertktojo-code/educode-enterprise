from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext
from app.models.operations import BackgroundJob
from app.services.operations import add_job_event, create_job, mark_queued


async def enqueue_domain_job(
    session: AsyncSession,
    *,
    actor: ActorContext,
    module_name: str,
    entity_type: str,
    entity_id: UUID,
    job_type: str,
    total_steps: int,
    input_snapshot: dict[str, Any],
    priority: int = 50,
) -> BackgroundJob:
    job, created = await create_job(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        job_type=job_type,
        module_name=module_name,
        entity_type=entity_type,
        entity_id=entity_id,
        priority=priority,
        total_steps=max(total_steps, 1),
        idempotency_key=f"{module_name}:{entity_type}:{entity_id}",
        input_snapshot=input_snapshot,
    )
    if created:
        await mark_queued(session, job)
    return job


async def runtime_job_for_domain(
    session: AsyncSession,
    *,
    organization_id: UUID,
    module_name: str,
    entity_type: str,
    entity_id: UUID,
) -> BackgroundJob | None:
    return await session.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.module_name == module_name,
            BackgroundJob.entity_type == entity_type,
            BackgroundJob.entity_id == entity_id,
        )
        .order_by(BackgroundJob.created_at.desc())
        .limit(1)
    )


async def cancel_domain_job(
    session: AsyncSession,
    *,
    organization_id: UUID,
    module_name: str,
    entity_type: str,
    entity_id: UUID,
) -> BackgroundJob | None:
    job = await runtime_job_for_domain(
        session,
        organization_id=organization_id,
        module_name=module_name,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if job is None:
        return None
    if job.status not in {"completed", "failed", "cancelled", "expired"}:
        job.cancel_requested = True
        job.current_step = "Cancelamento solicitado"
        if job.status in {"pending", "queued", "retrying"}:
            job.status = "cancelled"
            job.completed_at = datetime.now(UTC)
        await add_job_event(session, job=job, event_type="job.cancel_requested")
    return job


def domain_status(runtime_status: str) -> str:
    return {
        "pending": "QUEUED",
        "queued": "QUEUED",
        "retrying": "QUEUED",
        "processing": "RUNNING",
        "waiting_provider": "RUNNING",
        "validating": "RUNNING",
        "completed": "COMPLETED",
        "failed": "FAILED",
        "cancelled": "CANCELLED",
        "expired": "FAILED",
    }.get(runtime_status, "QUEUED")


def synchronize_simple_domain_job(domain: Any, runtime: BackgroundJob) -> None:
    mapped = domain_status(runtime.status)
    domain.status = mapped
    domain.progress_percent = int(runtime.progress_percent)
    if hasattr(domain, "error_message"):
        domain.error_message = runtime.error_message or None
    if mapped == "RUNNING" and hasattr(domain, "started_at"):
        domain.started_at = domain.started_at or runtime.started_at or datetime.now(UTC)
    if mapped in {"COMPLETED", "FAILED", "CANCELLED"} and hasattr(domain, "finished_at"):
        domain.finished_at = runtime.completed_at or datetime.now(UTC)
