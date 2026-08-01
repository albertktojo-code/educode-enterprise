from __future__ import annotations

from typing import Any

from sqlalchemy import select

from . import models


async def list_characters(session: Any, organization_id: Any, library_id: Any | None = None):
    statement = select(models.ComicCharacter).where(models.ComicCharacter.organization_id == organization_id)
    if library_id:
        statement = statement.where(models.ComicCharacter.library_id == library_id)
    result = await session.execute(statement.order_by(models.ComicCharacter.name))
    return list(result.scalars().all())


async def list_scenarios(session: Any, organization_id: Any, library_id: Any | None = None):
    statement = select(models.ComicScenario).where(models.ComicScenario.organization_id == organization_id)
    if library_id:
        statement = statement.where(models.ComicScenario.library_id == library_id)
    result = await session.execute(statement.order_by(models.ComicScenario.name))
    return list(result.scalars().all())
