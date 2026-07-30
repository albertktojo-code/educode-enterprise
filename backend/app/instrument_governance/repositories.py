from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


async def add_and_refresh(session: AsyncSession, entity: T) -> T:
    session.add(entity)
    await session.flush()
    await session.refresh(entity)
    return entity


async def get_for_organization(
    session: AsyncSession, model: Any, organization_id: Any, entity_id: Any
) -> Any | None:
    result = await session.execute(
        select(model).where(model.organization_id == organization_id, model.id == entity_id)
    )
    return result.scalar_one_or_none()
