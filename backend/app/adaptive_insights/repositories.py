from __future__ import annotations

import uuid
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
    session: AsyncSession,
    model: type[T],
    organization_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> T | None:
    result = await session.execute(
        select(model).where(model.id == entity_id, model.organization_id == organization_id)
    )
    return result.scalar_one_or_none()


async def list_for_organization(
    session: AsyncSession,
    model: type[T],
    organization_id: uuid.UUID,
    *,
    order_by: Any | None = None,
) -> list[T]:
    statement = select(model).where(model.organization_id == organization_id)
    if order_by is not None:
        statement = statement.order_by(order_by)
    result = await session.execute(statement)
    return list(result.scalars().all())
