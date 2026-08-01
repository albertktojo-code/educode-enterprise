from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import AsyncSessionFactory, engine
from app.models.auth import Organization
from app.models.observability import OperationalMetricSnapshot
from app.services.observability import evaluate_alert_rules, persist_metric_snapshots

logger = logging.getLogger("educode.observability.worker")
settings = get_settings()


async def collect_once() -> None:
    async with AsyncSessionFactory() as session:
        organization_ids = list((await session.scalars(select(Organization.id).where(Organization.is_active.is_(True)))).all())
        for organization_id in organization_ids:
            await persist_metric_snapshots(session, organization_id)
            await evaluate_alert_rules(session, organization_id)
        cutoff = datetime.now(UTC) - timedelta(days=settings.metric_retention_days)
        await session.execute(delete(OperationalMetricSnapshot).where(OperationalMetricSnapshot.measured_at < cutoff))
        await session.commit()
        logger.info("Snapshots coletados para %s organizações", len(organization_ids))


async def main() -> None:
    logger.info("Worker de observabilidade iniciado; intervalo=%ss", settings.metric_snapshot_interval_seconds)
    try:
        while True:
            try:
                await collect_once()
            except Exception:
                logger.exception("Falha ao coletar métricas operacionais")
            await asyncio.sleep(settings.metric_snapshot_interval_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
