from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.object_storage import storage_from_settings
from app.services.platform import database_status, redis_status, storage_status

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "alive", "service": settings.project_name, "version": settings.app_version}


@router.get("/health/ready")
async def readiness(
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    db_state, db_latency, _ = await database_status(db)
    redis_state, redis_latency, _ = await redis_status(settings)
    storage = storage_status(settings)
    storage_ready = all(bool(value.get("writable")) for value in storage.values())
    object_storage = await storage_from_settings(settings).healthcheck()
    object_storage_ready = object_storage.get("status") == "healthy"
    ready = db_state == "healthy" and redis_state == "healthy" and storage_ready and object_storage_ready
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "database": {"status": db_state, "latency_ms": db_latency},
        "redis": {"status": redis_state, "latency_ms": redis_latency},
        "storage": "healthy" if storage_ready else "unavailable",
        "object_storage": object_storage,
        "maintenance_mode": settings.maintenance_mode,
    }


@router.get("/health/dependencies")
async def dependency_health(
    response: Response,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    db_state, db_latency, db_details = await database_status(db)
    redis_state, redis_latency, redis_details = await redis_status(settings)
    storage = storage_status(settings)
    object_storage = await storage_from_settings(settings).healthcheck()
    degraded = db_state != "healthy" or redis_state != "healthy" or not all(v.get("writable") for v in storage.values()) or object_storage.get("status") != "healthy"
    if degraded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "degraded" if degraded else "healthy",
        "dependencies": {
            "postgresql": {"status": db_state, "latency_ms": db_latency, **db_details},
            "redis": {"status": redis_state, "latency_ms": redis_latency, **redis_details},
            "storage": storage,
            "object_storage": object_storage,
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    await db.execute(text("SELECT 1"))
    return HealthResponse(
        status="healthy",
        service=settings.project_name,
        environment=settings.environment,
        database="connected",
        ai_provider=f"ai-fabric:{settings.ai_execution_mode}",
    )
