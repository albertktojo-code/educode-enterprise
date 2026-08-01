from __future__ import annotations

from typing import Any

from sqlalchemy import select

from . import models


async def document_layers(session: Any, organization_id: Any, document_id: Any):
    result = await session.execute(
        select(models.HQCanvasLayer)
        .where(
            models.HQCanvasLayer.organization_id == organization_id,
            models.HQCanvasLayer.document_id == document_id,
        )
        .order_by(models.HQCanvasLayer.z_index)
    )
    return list(result.scalars().all())


async def document_guides(session: Any, organization_id: Any, document_id: Any):
    result = await session.execute(
        select(models.HQCanvasGuide)
        .where(
            models.HQCanvasGuide.organization_id == organization_id,
            models.HQCanvasGuide.document_id == document_id,
        )
        .order_by(models.HQCanvasGuide.orientation, models.HQCanvasGuide.position)
    )
    return list(result.scalars().all())
