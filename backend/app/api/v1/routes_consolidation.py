from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext, resolve_actor_context
from app.db.model_registry import registered_table_names
from app.db.session import get_db_session
from app.models.operations import BackgroundJob, WorkerHeartbeat
from app.services.platform import current_migration

router = APIRouter(prefix="/consolidation", tags=["consolidation"])


@router.get("/health")
async def consolidation_health() -> dict[str, object]:
    tables = registered_table_names()
    return {
        "status": "ok",
        "sprint": "16.4.1",
        "module": "architectural-consolidation",
        "registered_tables": len(tables),
    }


@router.get("/diagnostics")
async def consolidation_diagnostics(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> dict[str, object]:
    active_jobs = int(
        await session.scalar(
            select(func.count(BackgroundJob.id)).where(
                BackgroundJob.organization_id == actor.organization_id,
                BackgroundJob.status.in_(
                    ["pending", "queued", "processing", "waiting_provider", "validating", "retrying"]
                ),
            )
        )
        or 0
    )
    workers = list((await session.scalars(select(WorkerHeartbeat))).all())
    table_names = registered_table_names()
    return {
        "status": "ok",
        "sprint": "16.4.1",
        "migration": await current_migration(session),
        "organization_id": str(actor.organization_id),
        "roles": sorted(actor.roles),
        "metadata": {
            "table_count": len(table_names),
            "incremental_tables": sum(
                1
                for name in table_names
                if name.startswith(
                    (
                        "adaptive_",
                        "assessment_hub_",
                        "assessment_delivery_",
                        "instrument_",
                        "assessment_review_",
                        "assessment_analytics_",
                        "hq_",
                        "comic_visual_",
                        "comic_editorial_",
                    )
                )
            ),
        },
        "jobs": {
            "active": active_jobs,
            "workers_total": len(workers),
            "worker_queues": sorted({item.queue_name for item in workers}),
        },
        "frontend": {
            "route_registry": True,
            "authenticated_api_clients": 11,
        },
    }
