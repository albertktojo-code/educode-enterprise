from __future__ import annotations

import argparse
import asyncio
from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.operations import WorkerHeartbeat


async def change_workers(action: str, queue: str) -> int:
    async with AsyncSessionFactory() as session:
        workers = list((await session.scalars(select(WorkerHeartbeat))).all())
        selected = [item for item in workers if queue == "all" or item.queue_name == queue]
        for item in selected:
            if action == "drain":
                item.status = "draining"
            elif action == "resume":
                item.status = "idle"
        await session.commit()
        for item in selected:
            print(f"{item.worker_name}: {item.status} ({item.queue_name})")
        return len(selected)


async def show_status(queue: str) -> int:
    async with AsyncSessionFactory() as session:
        workers = list((await session.scalars(select(WorkerHeartbeat))).all())
        selected = [item for item in workers if queue == "all" or item.queue_name == queue]
        for item in selected:
            print(f"{item.worker_name}: {item.status} queue={item.queue_name} current_job={item.current_job_id}")
        return len(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="Drenagem controlada dos workers")
    parser.add_argument("action", choices=["drain", "resume", "status"])
    parser.add_argument("--queue", default="all", choices=["all", "ai", "documents", "analytics", "default", "observability"])
    args = parser.parse_args()
    count = asyncio.run(show_status(args.queue) if args.action == "status" else change_workers(args.action, args.queue))
    print(f"workers={count}")


if __name__ == "__main__":
    main()
