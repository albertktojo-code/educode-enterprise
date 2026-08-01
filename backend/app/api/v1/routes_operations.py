from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import AsyncSessionFactory, get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.operations import (
    BackgroundJob,
    BackgroundJobEvent,
    JobNotification,
    ProviderCircuitState,
    WorkerHeartbeat,
)
from app.schemas.operations import (
    CircuitRead,
    CircuitUpdate,
    JobCreate,
    JobEventRead,
    JobNotificationRead,
    JobRead,
    OperationOverview,
    WorkerRead,
)
from app.services.operations import (
    add_job_event,
    average_completion_seconds,
    create_job,
    mark_queued,
    redis_is_available,
    status_counts,
    utcnow,
)

router = APIRouter(tags=["background-operations"])
ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.TEACHER)
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def organization_id(membership: Membership) -> UUID:
    return membership.organization_id


def can_manage_all(membership: Membership) -> bool:
    return membership.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}


async def get_visible_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    membership: Membership,
    user: User,
) -> BackgroundJob:
    job = await session.get(BackgroundJob, job_id)
    if job is None or job.organization_id != organization_id(membership):
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if not can_manage_all(membership) and job.requested_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="A tarefa pertence a outro usuário")
    return job


@router.post("/jobs", response_model=JobRead, status_code=201)
async def create_background_job(
    data: JobCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> BackgroundJob:
    try:
        job, created = await create_job(
            session,
            organization_id=organization_id(membership),
            user_id=user.id,
            job_type=data.job_type,
            module_name=data.module_name,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            ai_flow_id=data.ai_flow_id,
            priority=data.priority if can_manage_all(membership) else min(data.priority, 89),
            total_steps=data.total_steps,
            max_retries=data.max_retries,
            idempotency_key=data.idempotency_key,
            input_snapshot=data.input_snapshot,
            estimated_cost=data.estimated_cost,
            depends_on_job_ids=data.depends_on_job_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    if created:
        await mark_queued(session, job)
        await session.commit()
    await session.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(
    status: str | None = Query(default=None),
    queue_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> list[BackgroundJob]:
    statement = (
        select(BackgroundJob)
        .where(BackgroundJob.organization_id == organization_id(membership))
        .order_by(BackgroundJob.created_at.desc())
        .limit(limit)
    )
    if not can_manage_all(membership):
        statement = statement.where(BackgroundJob.requested_by_user_id == user.id)
    if status:
        statement = statement.where(BackgroundJob.status == status)
    if queue_name:
        statement = statement.where(BackgroundJob.queue_name == queue_name)
    return list((await session.scalars(statement)).all())


@router.get("/jobs/{job_id}", response_model=JobRead)
async def read_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> BackgroundJob:
    return await get_visible_job(session, job_id=job_id, membership=membership, user=user)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
async def cancel_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> BackgroundJob:
    job = await get_visible_job(session, job_id=job_id, membership=membership, user=user)
    if job.status in {"completed", "failed", "cancelled", "expired"}:
        raise HTTPException(status_code=422, detail="A tarefa já foi encerrada")
    job.cancel_requested = True
    job.current_step = "Cancelamento solicitado"
    if job.status in {"pending", "queued", "retrying"}:
        job.status = "cancelled"
        job.completed_at = utcnow()
    await add_job_event(session, job=job, event_type="job.cancel_requested")
    await session.commit()
    await session.refresh(job)
    return job


@router.post("/jobs/{job_id}/retry", response_model=JobRead)
async def retry_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> BackgroundJob:
    job = await get_visible_job(session, job_id=job_id, membership=membership, user=user)
    if job.status not in {"failed", "cancelled"}:
        raise HTTPException(status_code=422, detail="Apenas tarefas falhas ou canceladas podem ser reenviadas")
    job.status = "pending"
    job.cancel_requested = False
    job.completed_at = None
    job.error_code = ""
    job.error_message = ""
    job.current_step = "Preparando nova tentativa"
    await mark_queued(session, job)
    await session.commit()
    await session.refresh(job)
    return job


@router.get("/jobs/{job_id}/events", response_model=list[JobEventRead])
async def job_events(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> list[BackgroundJobEvent]:
    await get_visible_job(session, job_id=job_id, membership=membership, user=user)
    return list(
        (
            await session.scalars(
                select(BackgroundJobEvent)
                .where(BackgroundJobEvent.job_id == job_id)
                .order_by(BackgroundJobEvent.created_at)
            )
        ).all()
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_events(
    job_id: UUID,
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    async with AsyncSessionFactory() as session:
        await get_visible_job(session, job_id=job_id, membership=membership, user=user)

    async def generator():
        last_created_at = datetime.min.replace(tzinfo=UTC)
        while True:
            async with AsyncSessionFactory() as stream_session:
                rows = list(
                    (
                        await stream_session.scalars(
                            select(BackgroundJobEvent)
                            .where(
                                BackgroundJobEvent.job_id == job_id,
                                BackgroundJobEvent.created_at > last_created_at,
                            )
                            .order_by(BackgroundJobEvent.created_at)
                        )
                    ).all()
                )
                for event in rows:
                    last_created_at = event.created_at
                    payload = {
                        "id": str(event.id),
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "created_at": event.created_at.isoformat(),
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                job = await stream_session.get(BackgroundJob, job_id)
                if job and job.status in {"completed", "failed", "cancelled", "expired"}:
                    yield f"event: terminal\ndata: {json.dumps({'status': job.status})}\n\n"
                    break
            await asyncio.sleep(1)

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/notifications", response_model=list[JobNotificationRead])
async def notifications(
    unread_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> list[JobNotification]:
    statement = (
        select(JobNotification)
        .where(
            JobNotification.organization_id == organization_id(membership),
            JobNotification.user_id == user.id,
        )
        .order_by(JobNotification.created_at.desc())
        .limit(100)
    )
    if unread_only:
        statement = statement.where(JobNotification.status == "unread")
    return list((await session.scalars(statement)).all())


@router.patch("/notifications/{notification_id}/read", response_model=JobNotificationRead)
async def read_notification(
    notification_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ROLES)),
    user: User = Depends(get_current_user),
) -> JobNotification:
    notification = await session.get(JobNotification, notification_id)
    if (
        notification is None
        or notification.organization_id != organization_id(membership)
        or notification.user_id != user.id
    ):
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    notification.status = "read"
    notification.read_at = utcnow()
    await session.commit()
    await session.refresh(notification)
    return notification


@router.get("/operations/overview", response_model=OperationOverview)
async def operations_overview(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> OperationOverview:
    org = organization_id(membership)
    now = utcnow()
    heartbeats = list((await session.scalars(select(WorkerHeartbeat))).all())
    active_workers = sum(
        1 for row in heartbeats if row.last_seen_at >= now - timedelta(seconds=45)
    )
    counts = await status_counts(session, org)
    queue_result = await session.execute(
        select(BackgroundJob.queue_name, func.count(BackgroundJob.id))
        .where(
            BackgroundJob.organization_id == org,
            BackgroundJob.status.in_(["pending", "queued", "retrying"]),
        )
        .group_by(BackgroundJob.queue_name)
    )
    failed = await session.scalar(
        select(func.count(BackgroundJob.id)).where(
            BackgroundJob.organization_id == org,
            BackgroundJob.status == "failed",
            BackgroundJob.completed_at >= now - timedelta(hours=24),
        )
    )
    circuits = await session.scalar(
        select(func.count(ProviderCircuitState.id)).where(
            ProviderCircuitState.organization_id == org,
            ProviderCircuitState.state == "open",
        )
    )
    return OperationOverview(
        redis_available=await redis_is_available(),
        worker_count=len(heartbeats),
        active_workers=active_workers,
        queue_counts={name: int(count) for name, count in queue_result.all()},
        status_counts=counts,
        failed_last_24h=int(failed or 0),
        average_completion_seconds=await average_completion_seconds(session, org),
        circuit_open_count=int(circuits or 0),
    )


@router.get("/operations/workers", response_model=list[WorkerRead])
async def workers(
    session: AsyncSession = Depends(get_db_session),
    _: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[WorkerHeartbeat]:
    return list((await session.scalars(select(WorkerHeartbeat).order_by(WorkerHeartbeat.queue_name))).all())


@router.get("/operations/failures", response_model=list[JobRead])
async def failed_jobs(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[BackgroundJob]:
    return list(
        (
            await session.scalars(
                select(BackgroundJob)
                .where(
                    BackgroundJob.organization_id == organization_id(membership),
                    BackgroundJob.status == "failed",
                )
                .order_by(BackgroundJob.completed_at.desc())
                .limit(200)
            )
        ).all()
    )


@router.get("/operations/circuits", response_model=list[CircuitRead])
async def circuits(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[ProviderCircuitState]:
    return list(
        (
            await session.scalars(
                select(ProviderCircuitState).where(
                    ProviderCircuitState.organization_id == organization_id(membership)
                )
            )
        ).all()
    )


@router.patch("/operations/circuits/{circuit_id}", response_model=CircuitRead)
async def update_circuit(
    circuit_id: UUID,
    data: CircuitUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> ProviderCircuitState:
    circuit = await session.get(ProviderCircuitState, circuit_id)
    if circuit is None or circuit.organization_id != organization_id(membership):
        raise HTTPException(status_code=404, detail="Circuito não encontrado")
    circuit.state = data.state
    if data.consecutive_failures is not None:
        circuit.consecutive_failures = data.consecutive_failures
    if data.last_error is not None:
        circuit.last_error = data.last_error
    circuit.opened_at = utcnow() if data.state == "open" else None
    circuit.next_probe_at = utcnow() + timedelta(minutes=5) if data.state == "open" else None
    await session.commit()
    await session.refresh(circuit)
    return circuit
