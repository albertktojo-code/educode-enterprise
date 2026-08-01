from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_runtime import AIGenerationRequest, AIGenerationResult
from app.schemas.ai_runtime import AIGenerationCreate
from app.services.ai.orchestrator import (
    AIOrchestrationError,
    create_generation_request,
)

from . import models
from .compat import ActorContext
from .policies import (
    aspect_ratio_for_panel,
    build_story_distribution,
    merge_panel_content,
    narrative_stage,
    recommended_layout_code,
    stable_hash,
    story_generation_payload,
)


async def story_plan_for_project(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    lock: bool = False,
) -> models.HQStoryPlan | None:
    statement = select(models.HQStoryPlan).where(
        models.HQStoryPlan.organization_id == organization_id,
        models.HQStoryPlan.comic_project_id == project_id,
    )
    if lock:
        statement = statement.with_for_update()
    return await session.scalar(statement)


async def upsert_story_plan(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    data: Any,
) -> models.HQStoryPlan:
    item = await story_plan_for_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        lock=True,
    )
    snapshot = data.model_dump(mode="json")
    content_hash = stable_hash(snapshot)
    if item is None:
        item = models.HQStoryPlan(
            organization_id=actor.organization_id,
            comic_project_id=project_id,
            created_by_user_id=actor.user_id,
            updated_by_user_id=actor.user_id,
        )
        session.add(item)
    else:
        item.revision_number += 1
        item.updated_by_user_id = actor.user_id

    item.source_mode = data.source_mode
    item.total_pages = data.total_pages
    item.narrative_pacing = data.narrative_pacing
    item.distribution_mode = data.distribution_mode
    item.short_summary = data.short_summary
    item.full_script = data.full_script
    item.continuity_constraints = data.continuity_constraints
    item.generation_instructions = data.generation_instructions
    item.content_hash = content_hash
    item.generation_status = "DRAFT"
    await session.flush()
    return item


async def layout_by_code(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    code: str,
) -> models.HQLayoutTemplate:
    item = await session.scalar(
        select(models.HQLayoutTemplate)
        .where(
            models.HQLayoutTemplate.code == code,
            (
                (models.HQLayoutTemplate.organization_id == organization_id)
                | (models.HQLayoutTemplate.is_system.is_(True))
            ),
            models.HQLayoutTemplate.status != "ARCHIVED",
        )
        .order_by(
            models.HQLayoutTemplate.organization_id.is_not(None).desc(),
            models.HQLayoutTemplate.version.desc(),
        )
        .limit(1)
    )
    if item is None:
        raise HTTPException(409, f"Grid institucional não encontrado: {code}")
    return item


async def panels_for_page(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    page_id: uuid.UUID,
) -> list[models.HQEditorPanel]:
    return list(
        (
            await session.scalars(
                select(models.HQEditorPanel)
                .where(
                    models.HQEditorPanel.organization_id == organization_id,
                    models.HQEditorPanel.page_id == page_id,
                )
                .order_by(models.HQEditorPanel.panel_order)
            )
        ).all()
    )


async def apply_layout(
    session: AsyncSession,
    *,
    actor: ActorContext,
    page: models.HQEditorPage,
    layout: models.HQLayoutTemplate,
    preserve_content: bool,
) -> list[models.HQEditorPanel]:
    current = await panels_for_page(
        session,
        organization_id=actor.organization_id,
        page_id=page.id,
    )
    previous = [
        {
            "scene_summary": item.scene_summary,
            "visual_prompt": item.visual_prompt,
            "locked_elements": item.locked_elements,
            "pedagogical_metadata": item.pedagogical_metadata,
            "accessibility_metadata": item.accessibility_metadata,
        }
        for item in current
    ]
    rectangles = list(layout.grid_definition.get("panels", []))
    merged = merge_panel_content(
        previous,
        rectangles,
        preserve_content,
    )
    result: list[models.HQEditorPanel] = []
    for index, data in enumerate(merged):
        panel = (
            current[index]
            if index < len(current)
            else models.HQEditorPanel(
                organization_id=actor.organization_id,
                page_id=page.id,
                panel_order=index + 1,
            )
        )
        panel.panel_order = data["panel_order"]
        panel.shape = data.get("shape", "RECTANGLE")
        panel.x = float(data["x"])
        panel.y = float(data["y"])
        panel.width = float(data["width"])
        panel.height = float(data["height"])
        panel.aspect_ratio = aspect_ratio_for_panel(
            float(data["width"]),
            float(data["height"]),
        )
        panel.scene_summary = data["scene_summary"]
        panel.visual_prompt = data["visual_prompt"]
        panel.locked_elements = data["locked_elements"]
        panel.pedagogical_metadata = data["pedagogical_metadata"]
        panel.accessibility_metadata = data["accessibility_metadata"]
        if index >= len(current):
            session.add(panel)
        result.append(panel)

    excess = current[len(merged):]
    if excess:
        excess_ids = [item.id for item in excess]
        await session.execute(
            delete(models.HQPanelTextLayer).where(
                models.HQPanelTextLayer.organization_id
                == actor.organization_id,
                models.HQPanelTextLayer.panel_id.in_(excess_ids),
            )
        )
        await session.execute(
            delete(models.HQEditorPanel).where(
                models.HQEditorPanel.organization_id
                == actor.organization_id,
                models.HQEditorPanel.id.in_(excess_ids),
            )
        )
    page.layout_template_id = layout.id
    page.revision_number += 1
    await session.flush()
    return result


async def ensure_story_pages(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    total_pages: int,
    narrative_pacing: str,
) -> list[models.HQEditorPage]:
    pages = list(
        (
            await session.scalars(
                select(models.HQEditorPage)
                .where(
                    models.HQEditorPage.organization_id
                    == actor.organization_id,
                    models.HQEditorPage.comic_project_id == project_id,
                    models.HQEditorPage.page_type == "STORY",
                )
                .order_by(models.HQEditorPage.page_number)
                .with_for_update()
            )
        ).all()
    )
    if (
        len(pages) > total_pages
        or any(page.page_number > total_pages for page in pages)
    ):
        raise HTTPException(
            409,
            {
                "code": "HQ_HAS_MORE_PAGES_THAN_STORY_PLAN",
                "existing_pages": len(pages),
                "configured_pages": total_pages,
                "message": (
                    "Reduza manualmente as páginas excedentes ou aumente "
                    "o total configurado. Nenhuma página será apagada automaticamente."
                ),
            },
        )
    existing_numbers = {page.page_number for page in pages}
    for page_number in range(1, total_pages + 1):
        if page_number in existing_numbers:
            continue
        stage = narrative_stage(
            page_number,
            total_pages,
            narrative_pacing,
        )
        layout = await layout_by_code(
            session,
            organization_id=actor.organization_id,
            code=recommended_layout_code(stage),
        )
        page = models.HQEditorPage(
            organization_id=actor.organization_id,
            comic_project_id=project_id,
            layout_template_id=layout.id,
            page_number=page_number,
            page_type="STORY",
            title=f"Página {page_number}",
            status="DRAFT",
            page_width=1200,
            page_height=1600,
            background_settings={
                "narrative_stage": stage,
                "layout_source": "automatic_recommendation",
            },
            accessibility_settings={},
            revision_number=1,
            created_by_user_id=actor.user_id,
        )
        session.add(page)
        await session.flush()
        for order, rect in enumerate(
            layout.grid_definition.get("panels", []),
            start=1,
        ):
            session.add(
                models.HQEditorPanel(
                    organization_id=actor.organization_id,
                    page_id=page.id,
                    panel_order=order,
                    shape=rect.get("shape", "RECTANGLE"),
                    x=float(rect["x"]),
                    y=float(rect["y"]),
                    width=float(rect["width"]),
                    height=float(rect["height"]),
                    aspect_ratio=aspect_ratio_for_panel(
                        float(rect["width"]),
                        float(rect["height"]),
                    ),
                    scene_summary="",
                    visual_prompt="",
                    generation_status="PENDING",
                    locked_elements=[],
                )
            )
        pages.append(page)
        existing_numbers.add(page_number)
    await session.flush()
    return sorted(pages, key=lambda item: item.page_number)


async def page_capacities(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    pages: list[models.HQEditorPage],
) -> list[int]:
    capacities: list[int] = []
    for page in pages:
        panels = await panels_for_page(
            session,
            organization_id=organization_id,
            page_id=page.id,
        )
        capacities.append(max(1, len(panels)))
    return capacities


async def distribute_story(
    session: AsyncSession,
    *,
    actor: ActorContext,
    story_plan: models.HQStoryPlan,
    ensure_total_pages: bool,
    preserve_existing_summaries: bool,
    apply_layout_recommendations: bool,
) -> list[dict[str, Any]]:
    pages = (
        await ensure_story_pages(
            session,
            actor=actor,
            project_id=story_plan.comic_project_id,
            total_pages=story_plan.total_pages,
            narrative_pacing=story_plan.narrative_pacing,
        )
        if ensure_total_pages
        else list(
            (
                await session.scalars(
                    select(models.HQEditorPage)
                    .where(
                        models.HQEditorPage.organization_id
                        == actor.organization_id,
                        models.HQEditorPage.comic_project_id
                        == story_plan.comic_project_id,
                        models.HQEditorPage.page_type == "STORY",
                    )
                    .order_by(models.HQEditorPage.page_number)
                )
            ).all()
        )
    )
    if not pages:
        raise HTTPException(409, "A HQ não possui páginas para distribuir.")

    if apply_layout_recommendations:
        for page in pages:
            stage = narrative_stage(
                page.page_number,
                len(pages),
                story_plan.narrative_pacing,
            )
            layout = await layout_by_code(
                session,
                organization_id=actor.organization_id,
                code=recommended_layout_code(stage),
            )
            await apply_layout(
                session,
                actor=actor,
                page=page,
                layout=layout,
                preserve_content=True,
            )

    capacities = await page_capacities(
        session,
        organization_id=actor.organization_id,
        pages=pages,
    )
    source_text = (
        story_plan.full_script.strip()
        or story_plan.short_summary.strip()
    )
    plan = build_story_distribution(
        source_text=source_text,
        page_capacities=capacities,
        narrative_pacing=story_plan.narrative_pacing,
    )

    for page, page_plan in zip(pages, plan, strict=True):
        page.background_settings = {
            **page.background_settings,
            "narrative_stage": page_plan["stage"],
            "recommended_layout_code": page_plan[
                "recommended_layout_code"
            ],
        }
        panels = await panels_for_page(
            session,
            organization_id=actor.organization_id,
            page_id=page.id,
        )
        for panel, panel_plan in zip(
            panels,
            page_plan["panels"],
            strict=True,
        ):
            if (
                not preserve_existing_summaries
                or not panel.scene_summary.strip()
            ):
                panel.scene_summary = panel_plan["scene_summary"]
            panel.pedagogical_metadata = {
                **panel.pedagogical_metadata,
                "narrative_function": panel_plan[
                    "narrative_function"
                ],
                "global_panel_order": panel_plan[
                    "global_panel_order"
                ],
                "story_plan_revision": story_plan.revision_number,
            }

    story_plan.page_plan = plan
    story_plan.generation_status = "DISTRIBUTED"
    story_plan.content_hash = stable_hash(
        {
            "source_mode": story_plan.source_mode,
            "total_pages": story_plan.total_pages,
            "narrative_pacing": story_plan.narrative_pacing,
            "distribution_mode": story_plan.distribution_mode,
            "short_summary": story_plan.short_summary,
            "full_script": story_plan.full_script,
            "page_plan": plan,
        }
    )
    story_plan.updated_by_user_id = actor.user_id
    await session.flush()
    return plan


async def request_ai_story(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    data: Any,
) -> tuple[models.HQStoryPlan, AIGenerationRequest]:
    class StoryData:
        source_mode = "AI_SUMMARY"
        full_script = ""

    story_data = StoryData()
    story_data.total_pages = data.total_pages
    story_data.narrative_pacing = data.narrative_pacing
    story_data.distribution_mode = data.distribution_mode
    story_data.short_summary = data.short_summary
    story_data.continuity_constraints = data.continuity_constraints
    story_data.generation_instructions = data.generation_instructions
    story_data.model_dump = lambda mode="json": {
        "source_mode": story_data.source_mode,
        "total_pages": story_data.total_pages,
        "narrative_pacing": story_data.narrative_pacing,
        "distribution_mode": story_data.distribution_mode,
        "short_summary": story_data.short_summary,
        "full_script": story_data.full_script,
        "continuity_constraints": story_data.continuity_constraints,
        "generation_instructions": story_data.generation_instructions,
    }
    plan = await upsert_story_plan(
        session,
        actor=actor,
        project_id=project_id,
        data=story_data,
    )
    pages = await ensure_story_pages(
        session,
        actor=actor,
        project_id=project_id,
        total_pages=data.total_pages,
        narrative_pacing=data.narrative_pacing,
    )
    capacities = await page_capacities(
        session,
        organization_id=actor.organization_id,
        pages=pages,
    )
    request_data = AIGenerationCreate(
        module_name="comics",
        action_name="generate_script",
        request_type="structured_text",
        target_type="project",
        target_id=project_id,
        model_id=data.model_id,
        prompt_template_id=data.prompt_template_id,
        input_data=story_generation_payload(
            summary=data.short_summary,
            total_pages=data.total_pages,
            page_capacities=capacities,
            narrative_pacing=data.narrative_pacing,
            continuity_constraints=data.continuity_constraints,
            generation_instructions=data.generation_instructions,
        ),
        parameters={
            "temperature": 0.7,
            "response_format": "json",
            "human_review_required": True,
        },
        queue_immediately=True,
    )
    try:
        request = await create_generation_request(
            session,
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            data=request_data,
        )
    except AIOrchestrationError as error:
        raise HTTPException(409, str(error)) from error

    plan.ai_generation_request_id = request.id
    plan.generation_status = "AI_QUEUED"
    plan.page_plan = build_story_distribution(
        source_text=data.short_summary,
        page_capacities=capacities,
        narrative_pacing=data.narrative_pacing,
    )
    plan.content_hash = stable_hash(
        {
            "request_id": request.id,
            "summary": data.short_summary,
            "page_plan": plan.page_plan,
        }
    )
    await session.flush()
    return plan, request


async def apply_ai_result(
    session: AsyncSession,
    *,
    actor: ActorContext,
    story_plan: models.HQStoryPlan,
    result_id: uuid.UUID,
    distribute_after_apply: bool,
) -> models.HQStoryPlan:
    result = await session.scalar(
        select(AIGenerationResult).where(
            AIGenerationResult.organization_id == actor.organization_id,
            AIGenerationResult.id == result_id,
        )
    )
    if result is None:
        raise HTTPException(404, "Resultado de IA não encontrado.")
    request = await session.scalar(
        select(AIGenerationRequest).where(
            AIGenerationRequest.organization_id == actor.organization_id,
            AIGenerationRequest.id == result.request_id,
            AIGenerationRequest.target_type == "project",
            AIGenerationRequest.target_id == story_plan.comic_project_id,
        )
    )
    if request is None:
        raise HTTPException(
            409,
            "O resultado não pertence ao projeto desta HQ.",
        )
    if result.review_status == "rejected":
        raise HTTPException(409, "O resultado de IA foi rejeitado.")

    content = result.structured_content or {}
    full_script = str(
        content.get("full_script")
        or result.text_content
        or ""
    ).strip()
    pages = content.get("pages")
    if not full_script and not isinstance(pages, list):
        raise HTTPException(
            409,
            "O resultado não contém roteiro estruturado aplicável.",
        )

    story_plan.full_script = full_script or story_plan.full_script
    if isinstance(pages, list):
        story_plan.page_plan = pages
    story_plan.source_mode = "AI_SUMMARY"
    story_plan.generation_status = "AI_DRAFT_APPLIED"
    story_plan.ai_generation_request_id = request.id
    story_plan.revision_number += 1
    story_plan.updated_by_user_id = actor.user_id
    story_plan.content_hash = stable_hash(
        {
            "result_id": result.id,
            "full_script": story_plan.full_script,
            "page_plan": story_plan.page_plan,
        }
    )
    if distribute_after_apply:
        await distribute_story(
            session,
            actor=actor,
            story_plan=story_plan,
            ensure_total_pages=True,
            preserve_existing_summaries=False,
            apply_layout_recommendations=False,
        )
    await session.flush()
    return story_plan
