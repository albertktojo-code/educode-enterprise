from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models

ModelT = TypeVar("ModelT")


async def add_and_refresh(session: AsyncSession, entity: ModelT) -> ModelT:
    session.add(entity)
    await session.flush()
    await session.refresh(entity)
    return entity


async def list_for_organization(
    session: AsyncSession,
    model: type[ModelT],
    organization_id: uuid.UUID,
    *,
    offset: int = 0,
    limit: int = 100,
    filters: dict[str, Any] | None = None,
    order_by: Any | None = None,
) -> Sequence[ModelT]:
    statement: Select[Any] = select(model).where(model.organization_id == organization_id)
    for field_name, value in (filters or {}).items():
        if value is not None:
            statement = statement.where(getattr(model, field_name) == value)
    if order_by is not None:
        statement = statement.order_by(order_by)
    statement = statement.offset(max(0, offset)).limit(min(max(1, limit), 500))
    result = await session.execute(statement)
    return result.scalars().all()


async def get_for_organization(
    session: AsyncSession,
    model: type[ModelT],
    organization_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> ModelT | None:
    statement = select(model).where(model.id == entity_id, model.organization_id == organization_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def next_accessible_version_number(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    source_resource_type: str,
    source_resource_id: uuid.UUID,
    adaptation_type: str,
) -> int:
    statement = (
        select(models.AccessibleResourceVersion.version)
        .where(
            models.AccessibleResourceVersion.organization_id == organization_id,
            models.AccessibleResourceVersion.source_resource_type == source_resource_type,
            models.AccessibleResourceVersion.source_resource_id == source_resource_id,
            models.AccessibleResourceVersion.adaptation_type == adaptation_type,
        )
        .order_by(models.AccessibleResourceVersion.version.desc())
        .limit(1)
    )
    result = await session.execute(statement)
    current = result.scalar_one_or_none()
    return int(current or 0) + 1
