from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .policies import publication_readiness, stable_release_hash


async def review_readiness(
    session: AsyncSession,
    *,
    organization_id: UUID,
    review_session_id: UUID,
    snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    workflow = await session.scalar(
        select(models.ComicEditorialWorkflow).where(
            models.ComicEditorialWorkflow.organization_id == organization_id,
            models.ComicEditorialWorkflow.review_session_id == review_session_id,
        )
    )
    unresolved_threads = int(
        await session.scalar(
            select(func.count(models.ComicEditorialThread.id)).where(
                models.ComicEditorialThread.organization_id == organization_id,
                models.ComicEditorialThread.review_session_id == review_session_id,
                models.ComicEditorialThread.status.in_(["OPEN", "REOPENED"]),
            )
        )
        or 0
    )
    open_change_requests = int(
        await session.scalar(
            select(func.count(models.ComicEditorialChangeRequest.id)).where(
                models.ComicEditorialChangeRequest.organization_id == organization_id,
                models.ComicEditorialChangeRequest.review_session_id == review_session_id,
                models.ComicEditorialChangeRequest.status.in_(["OPEN", "ACCEPTED"]),
            )
        )
        or 0
    )
    blocked_checklists = int(
        await session.scalar(
            select(func.count(models.ComicEditorialChecklist.id)).where(
                models.ComicEditorialChecklist.organization_id == organization_id,
                models.ComicEditorialChecklist.review_session_id == review_session_id,
                models.ComicEditorialChecklist.is_blocked.is_(True),
            )
        )
        or 0
    )
    release_hash = stable_release_hash(snapshot) if snapshot else None
    readiness = publication_readiness(
        workflow_status=workflow.status if workflow else "MISSING",
        unresolved_threads=unresolved_threads,
        open_change_requests=open_change_requests,
        checklist_blocked=blocked_checklists > 0,
        release_hash=release_hash,
    )
    return {
        **readiness,
        "workflow_status": workflow.status if workflow else "MISSING",
        "unresolved_threads": unresolved_threads,
        "open_change_requests": open_change_requests,
        "blocked_checklists": blocked_checklists,
        "release_hash": release_hash,
    }
