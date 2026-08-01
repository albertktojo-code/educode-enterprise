from __future__ import annotations

import asyncio
import json
import sys

from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.services.platform import (
    configuration_warnings,
    database_status,
    redis_status,
    storage_status,
)


async def run() -> int:
    settings = get_settings()
    async with AsyncSessionFactory() as session:
        db_state, db_latency, db_details = await database_status(session)
    redis_state, redis_latency, redis_details = await redis_status(settings)
    storage = storage_status(settings)
    warnings = configuration_warnings(settings)
    checks = {
        "postgresql": {"status": db_state, "latency_ms": db_latency, **db_details},
        "redis": {"status": redis_state, "latency_ms": redis_latency, **redis_details},
        "storage": storage,
    }
    ready = (
        db_state == "healthy"
        and redis_state == "healthy"
        and all(bool(item.get("writable")) for item in storage.values())
        and not warnings
    )
    print(json.dumps({"ready": ready, "checks": checks, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
