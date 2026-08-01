from __future__ import annotations

from typing import Any

from sqlalchemy import select

from . import models


async def project_pages(session: Any, organization_id: Any, project_id: Any):
    result = await session.execute(
        select(models.HQEditorPage)
        .where(models.HQEditorPage.organization_id == organization_id, models.HQEditorPage.comic_project_id == project_id)
        .order_by(models.HQEditorPage.page_number)
    )
    return list(result.scalars().all())
