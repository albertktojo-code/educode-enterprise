from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_runtime import (
    AIGenerationRequest,
    AIGenerationResult,
)
from app.schemas.ai_runtime import AIGenerationCreate
from app.services.ai.orchestrator import (
    AIOrchestrationError,
    create_generation_request,
)

from . import models
from .compat import ActorContext
from .policies import (
    COVER_COMPOSITIONS,
    cover_generation_payload,
    default_cover_layers,
    stable_hash,
)


async def special_page(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    page_type: str,
    lock: bool = False,
) -> models.HQEditorPage | None:
    statement = select(models.HQEditorPage).where(
        models.HQEditorPage.organization_id == organization_id,
        models.HQEditorPage.comic_project_id == project_id,
        models.HQEditorPage.page_type == page_type,
    )
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


def cover_payload(page: models.HQEditorPage) -> dict[str, Any]:
    settings = page.background_settings or {}
    return {
        "id": str(page.id),
        "comic_project_id": str(page.comic_project_id),
        "page_number": page.page_number,
        "page_type": page.page_type,
        "title": page.title or "",
        "composition_code": settings.get(
            "composition_code",
            "CINEMATIC",
        ),
        "subtitle": settings.get("subtitle", ""),
        "author": settings.get("author", ""),
        "school": settings.get("school", ""),
        "classroom": settings.get("classroom", ""),
        "discipline": settings.get("discipline", ""),
        "theme": settings.get("theme", ""),
        "school_year": settings.get("school_year", ""),
        "background_asset_reference": settings.get(
            "background_asset_reference"
        ),
        "focal_point": settings.get(
            "focal_point",
            {"x": 0.5, "y": 0.5},
        ),
        "scale": settings.get("scale", 1.0),
        "bleed_enabled": settings.get("bleed_enabled", True),
        "safe_area_enabled": settings.get(
            "safe_area_enabled",
            True,
        ),
        "spine_enabled": settings.get("spine_enabled", False),
        "content_layers": page.content_layers,
        "preservation_settings": page.preservation_settings,
        "continuity_metadata": page.continuity_metadata,
        "accessibility_settings": page.accessibility_settings,
        "cover_generation": page.cover_generation,
        "revision_number": page.revision_number,
        "updated_at": page.updated_at,
    }


async def ensure_cover(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
) -> models.HQEditorPage:
    page = await special_page(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        page_type="COVER",
        lock=True,
    )
    if page is not None:
        return page
    page = models.HQEditorPage(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        layout_template_id=None,
        page_number=0,
        page_type="COVER",
        title="",
        status="DRAFT",
        page_width=1200,
        page_height=1600,
        background_settings={
            "composition_code": "CINEMATIC",
            "background_asset_reference": None,
            "focal_point": {"x": 0.5, "y": 0.5},
            "scale": 1.0,
            "bleed_enabled": True,
            "safe_area_enabled": True,
            "spine_enabled": False,
        },
        accessibility_settings={},
        content_layers=default_cover_layers(),
        preservation_settings={
            "scope": "PROJECT",
            "elements": [
                "character",
                "outfit",
                "scenario",
                "palette",
                "style",
            ],
        },
        continuity_metadata={},
        cover_generation={},
        revision_number=1,
        created_by_user_id=actor.user_id,
    )
    session.add(page)
    await session.flush()
    return page


async def upsert_cover(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    data: Any,
) -> models.HQEditorPage:
    page = await ensure_cover(
        session,
        actor=actor,
        project_id=project_id,
    )
    page.title = data.title
    page.layout_template_id = None
    page.page_type = "COVER"
    page.background_settings = {
        **(page.background_settings or {}),
        "composition_code": data.composition_code,
        "subtitle": data.subtitle,
        "author": data.author,
        "school": data.school,
        "classroom": data.classroom,
        "discipline": data.discipline,
        "theme": data.theme,
        "school_year": data.school_year,
        "background_asset_reference": (
            data.background_asset_reference
        ),
        "focal_point": data.focal_point,
        "scale": data.scale,
        "bleed_enabled": data.bleed_enabled,
        "safe_area_enabled": data.safe_area_enabled,
        "spine_enabled": data.spine_enabled,
        "composition": COVER_COMPOSITIONS[
            data.composition_code
        ],
    }
    page.content_layers = [
        item.model_dump(mode="json")
        for item in data.content_layers
    ]
    page.preservation_settings = data.preservation_settings
    page.continuity_metadata = data.continuity_metadata
    page.accessibility_settings = data.accessibility_settings
    page.revision_number += 1
    await session.flush()
    return page


async def create_back_cover(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    title: str | None,
) -> models.HQEditorPage:
    existing = await special_page(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        page_type="BACK_COVER",
        lock=True,
    )
    if existing:
        return existing
    maximum = await session.scalar(
        select(models.HQEditorPage.page_number)
        .where(
            models.HQEditorPage.organization_id
            == actor.organization_id,
            models.HQEditorPage.comic_project_id == project_id,
        )
        .order_by(models.HQEditorPage.page_number.desc())
        .limit(1)
    )
    page = models.HQEditorPage(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        layout_template_id=None,
        page_number=int(maximum or 0) + 1,
        page_type="BACK_COVER",
        title=title or "Contracapa",
        status="DRAFT",
        page_width=1200,
        page_height=1600,
        background_settings={
            "composition_code": "BACK_COVER_EDUCATIONAL",
            "bleed_enabled": True,
            "safe_area_enabled": True,
        },
        accessibility_settings={},
        content_layers=[
            {
                "id": "back-cover-summary",
                "layer_type": "SUMMARY",
                "content": "",
                "x": 0.1,
                "y": 0.12,
                "width": 0.8,
                "height": 0.42,
                "visible": True,
                "style": {
                    "font_size": 28,
                    "color": "#1f2937",
                    "align": "left",
                },
            },
            {
                "id": "back-cover-credits",
                "layer_type": "CREDITS",
                "content": "",
                "x": 0.1,
                "y": 0.72,
                "width": 0.8,
                "height": 0.16,
                "visible": True,
                "style": {
                    "font_size": 18,
                    "color": "#475569",
                    "align": "left",
                },
            },
        ],
        preservation_settings={},
        continuity_metadata={},
        cover_generation={},
        revision_number=1,
        created_by_user_id=actor.user_id,
    )
    session.add(page)
    await session.flush()
    return page


async def request_cover_variations(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    cover: models.HQEditorPage,
    story_plan: models.HQStoryPlan | None,
    data: Any,
) -> AIGenerationRequest:
    settings = cover.background_settings or {}
    generation = AIGenerationCreate(
        module_name="comics",
        action_name="generate_image",
        request_type="image",
        target_type="project",
        target_id=project_id,
        model_id=data.model_id,
        prompt_template_id=data.prompt_template_id,
        input_data=cover_generation_payload(
            composition_code=data.composition_code,
            title=cover.title or "",
            summary=(
                story_plan.short_summary
                if story_plan
                else ""
            ),
            discipline=str(settings.get("discipline", "")),
            theme=str(settings.get("theme", "")),
            continuity=cover.continuity_metadata,
            preservation=cover.preservation_settings,
            variation_count=data.variation_count,
            additional_instructions=(
                data.additional_instructions
            ),
        ),
        parameters={
            "image_count": data.variation_count,
            "orientation": "portrait",
            "aspect_ratio": "3:4",
            "human_review_required": True,
            "forbid_text_in_image": True,
        },
        queue_immediately=True,
    )
    try:
        request = await create_generation_request(
            session,
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            data=generation,
        )
    except AIOrchestrationError as error:
        raise HTTPException(409, str(error)) from error
    cover.cover_generation = {
        **(cover.cover_generation or {}),
        "request_id": str(request.id),
        "status": request.status,
        "variation_count": data.variation_count,
        "composition_code": data.composition_code,
        "requested_at": request.created_at.isoformat()
        if request.created_at
        else None,
    }
    cover.revision_number += 1
    await session.flush()
    return request


async def apply_cover_result(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    cover: models.HQEditorPage,
    result_id: uuid.UUID,
) -> AIGenerationResult:
    result = await session.scalar(
        select(AIGenerationResult).where(
            AIGenerationResult.organization_id
            == actor.organization_id,
            AIGenerationResult.id == result_id,
        )
    )
    if result is None:
        raise HTTPException(404, "Variação de capa não encontrada.")
    request = await session.scalar(
        select(AIGenerationRequest).where(
            AIGenerationRequest.organization_id
            == actor.organization_id,
            AIGenerationRequest.id == result.request_id,
            AIGenerationRequest.target_type == "project",
            AIGenerationRequest.target_id == project_id,
            AIGenerationRequest.module_name == "comics",
            AIGenerationRequest.action_name == "generate_image",
        )
    )
    if request is None:
        raise HTTPException(
            409,
            "A variação não pertence a esta HQ.",
        )
    if result.review_status == "rejected":
        raise HTTPException(
            409,
            "A variação foi rejeitada e não pode ser aplicada.",
        )
    asset_reference = (
        result.storage_reference
        or result.structured_content.get("asset_reference")
        or result.structured_content.get("url")
    )
    if not asset_reference:
        raise HTTPException(
            409,
            "O resultado não possui uma imagem aplicável.",
        )
    previous = (cover.background_settings or {}).get(
        "background_asset_reference"
    )
    cover.background_settings = {
        **(cover.background_settings or {}),
        "background_asset_reference": asset_reference,
    }
    cover.cover_generation = {
        **(cover.cover_generation or {}),
        "applied_result_id": str(result.id),
        "previous_asset_reference": previous,
        "selected_asset_reference": asset_reference,
        "comparison_required": True,
    }
    cover.revision_number += 1
    result.applied_to_module = True
    result.application_snapshot = {
        "page_id": str(cover.id),
        "previous_asset_reference": previous,
        "selected_asset_reference": asset_reference,
    }
    await session.flush()
    return result
