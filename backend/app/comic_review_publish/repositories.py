from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from . import models


async def list_review_sessions(session: Any, organization_id: uuid.UUID, comic_project_id: uuid.UUID | None = None):
    query = select(models.ComicEditorialReviewSession).where(
        models.ComicEditorialReviewSession.organization_id == organization_id
    )
    if comic_project_id:
        query = query.where(models.ComicEditorialReviewSession.comic_project_id == comic_project_id)
    result = await session.execute(query.order_by(models.ComicEditorialReviewSession.created_at.desc()))
    return list(result.scalars().all())


async def list_threads(session: Any, organization_id: uuid.UUID, review_session_id: uuid.UUID):
    result = await session.execute(
        select(models.ComicEditorialThread)
        .where(
            models.ComicEditorialThread.organization_id == organization_id,
            models.ComicEditorialThread.review_session_id == review_session_id,
        )
        .order_by(models.ComicEditorialThread.created_at)
    )
    return list(result.scalars().all())


async def list_releases(session: Any, organization_id: uuid.UUID, comic_project_id: uuid.UUID):
    result = await session.execute(
        select(models.ComicEditorialRelease)
        .where(
            models.ComicEditorialRelease.organization_id == organization_id,
            models.ComicEditorialRelease.comic_project_id == comic_project_id,
        )
        .order_by(models.ComicEditorialRelease.release_number.desc())
    )
    return list(result.scalars().all())
