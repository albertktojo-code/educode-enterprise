from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import User
from app.models.comic import (
    BalloonType,
    ComicBalloon,
    ComicEditOperation,
    ComicGenerationRun,
    ComicPage,
    ComicPanel,
    ComicStatus,
    ComicVersion,
    ComicVersionScope,
    GeneratedComic,
    GenerationRunStatus,
    GenerationScope,
    LayoutMode,
    PageFormat,
    PageOrientation,
    PanelShape,
    PanelSize,
    PanelStatus,
    ReadingDirection,
    PreviewReviewStatus,
)
from app.models.creative import (
    CreativeItemKind,
    GenerationProjectCreativeItem,
)
from app.models.pedagogy import GenerationProject
from app.models.rag import RagContext, RagContextStatus, RagReviewStatus
from app.schemas.comic import ComicCreate, RegenerateRequest
from app.services.comics.continuity import ContinuityFinding, validate_payload
from app.services.comics.generator import (
    GeneratedBalloon,
    GeneratedPanel,
    StoryInput,
    build_story,
    regenerate_panel_content,
)
from app.services.comics.layouts import PanelLayout, layout_for, recommended_template


class ComicManagerError(ValueError):
    pass


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


async def load_comic(
    session: AsyncSession, *, organization_id: UUID, comic_id: UUID
) -> GeneratedComic | None:
    result = await session.scalar(
        select(GeneratedComic)
        .where(
            GeneratedComic.id == comic_id,
            GeneratedComic.organization_id == organization_id,
        )
        .options(
            selectinload(GeneratedComic.pages)
            .selectinload(ComicPage.panels)
            .selectinload(ComicPanel.balloons),
            selectinload(GeneratedComic.versions),
            selectinload(GeneratedComic.generation_runs),
            selectinload(GeneratedComic.review_comments),
            selectinload(GeneratedComic.review_approvals),
            selectinload(GeneratedComic.regeneration_proposals),
            selectinload(GeneratedComic.edit_operations),
        )
    )
    return result


async def create_comic(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    user_name: str,
    data: ComicCreate,
) -> GeneratedComic:
    project = await session.scalar(
        select(GenerationProject)
        .where(
            GenerationProject.id == data.generation_project_id,
            GenerationProject.organization_id == organization_id,
        )
        .options(selectinload(GenerationProject.pillars))
    )
    if project is None:
        raise ComicManagerError("Planejamento pedagógico não encontrado")
    context = await session.scalar(
        select(RagContext)
        .where(
            RagContext.id == data.rag_context_id,
            RagContext.organization_id == organization_id,
            RagContext.generation_project_id == project.id,
        )
        .options(selectinload(RagContext.facts), selectinload(RagContext.rules))
    )
    if context is None:
        raise ComicManagerError("Contexto RAG não encontrado para este planejamento")
    if context.status != RagContextStatus.APPROVED:
        raise ComicManagerError("O contexto RAG precisa estar aprovado antes da geração")

    creative_links = list(
        (
            await session.scalars(
                select(GenerationProjectCreativeItem)
                .where(GenerationProjectCreativeItem.generation_project_id == project.id)
                .options(selectinload(GenerationProjectCreativeItem.creative_item))
                .order_by(GenerationProjectCreativeItem.position)
            )
        ).all()
    )
    characters = [
        link.creative_item.name
        for link in creative_links
        if link.creative_item.kind == CreativeItemKind.CHARACTER
    ]
    scenes = [
        link.creative_item.name
        for link in creative_links
        if link.creative_item.kind == CreativeItemKind.SCENE
    ]
    creative_snapshot: dict[str, list[dict[str, Any]]] = {
        "characters": [],
        "scenes": [],
        "styles": [],
    }
    kind_keys = {
        CreativeItemKind.CHARACTER: "characters",
        CreativeItemKind.SCENE: "scenes",
        CreativeItemKind.STYLE: "styles",
    }
    for link in creative_links:
        key = kind_keys[link.creative_item.kind]
        creative_snapshot[key].append(
            {
                "creative_item_id": str(link.creative_item_id),
                "creative_version_id": (
                    str(link.creative_version_id) if link.creative_version_id else None
                ),
                "name": link.creative_item.name,
                "canonical_prompt": link.creative_item.canonical_prompt,
                "negative_prompt": link.creative_item.negative_prompt,
                "profile_data": dict(link.creative_item.profile_data),
                "narrative_role": link.narrative_role,
                "is_primary": link.is_primary,
            }
        )
    facts = [
        fact.statement
        for fact in sorted(context.facts, key=lambda item: item.order_index)
        if fact.review_status != RagReviewStatus.REJECTED and fact.is_mandatory
    ]
    pillar_codes = [link.pillar.code for link in project.pillars]
    page_configs = _page_configurations(data)
    panel_total = sum(config["panel_count"] for config in page_configs)
    story = build_story(
        StoryInput(
            title=data.title,
            topic=project.topic,
            disciplinary_objective=project.disciplinary_objective
            or f"Compreender os conceitos centrais de {project.topic}.",
            ct_objective=project.computational_thinking_objective
            or "Aplicar os pilares do Pensamento Computacional na resolução do desafio.",
            facts=facts,
            pillar_codes=pillar_codes,
            characters=characters,
            scenes=scenes,
            narrative_profile=data.narrative_profile.model_dump(),
        ),
        panel_total,
    )
    synopsis = _build_synopsis(data.title, project.topic, data.narrative_profile.model_dump())
    comic = GeneratedComic(
        organization_id=organization_id,
        generation_project_id=project.id,
        rag_context_id=context.id,
        created_by_user_id=user_id,
        created_by_name_snapshot=user_name,
        title=data.title,
        synopsis=synopsis,
        status=ComicStatus.IN_REVIEW,
        narrative_profile=data.narrative_profile.model_dump(),
        layout_preferences={
            "page_count": data.page_count,
            "default_panels_per_page": data.default_panels_per_page,
            "page_format": data.page_format.value,
            "orientation": data.orientation.value,
        },
        story_state={
            "facts_used": facts,
            "characters": characters,
            "scenes": scenes,
            "creative_assets": creative_snapshot,
            "open_questions": [],
        },
        notes=data.notes,
        art_direction=data.art_direction,
        canvas_config={"snap": True, "guides": True, "grid_size": 2},
        review_state={
            "narrative": "pending",
            "pedagogical": "pending",
            "visual": "pending",
            "accessibility": "pending",
        },
        last_saved_at=datetime.now(UTC),
    )
    session.add(comic)
    await session.flush()

    panel_cursor = 0
    for config in page_configs:
        page = ComicPage(
            comic_id=comic.id,
            page_number=config["page_number"],
            page_format=PageFormat(config["page_format"]),
            orientation=PageOrientation(config["orientation"]),
            layout_mode=LayoutMode(config["layout_mode"]),
            layout_template=config["layout_template"],
            reading_direction=ReadingDirection(config["reading_direction"]),
            panel_count=config["panel_count"],
            page_role=config.get("page_role", "story"),
            background_config={},
            guides_config={"snap": True, "grid": 2, "safe_margin": 3},
            width=297.0 if config["orientation"] == PageOrientation.LANDSCAPE.value else 210.0,
            height=210.0 if config["orientation"] == PageOrientation.LANDSCAPE.value else 297.0,
            margins={"top": 8, "right": 8, "bottom": 8, "left": 8},
        )
        session.add(page)
        await session.flush()
        layout = layout_for(config["layout_template"], config["panel_count"])
        for local_index, geometry in enumerate(layout, start=1):
            generated = story[panel_cursor]
            panel_cursor += 1
            panel = _panel_from_generated(
                page.id,
                local_index,
                generated,
                geometry,
                creative_snapshot,
            )
            session.add(panel)
            await session.flush()
            for balloon_data in generated["balloons"]:
                session.add(_balloon_from_generated(panel.id, balloon_data))

    await session.flush()
    await session.refresh(comic)
    loaded = await load_comic(session, organization_id=organization_id, comic_id=comic.id)
    if loaded is None:
        raise ComicManagerError("Falha ao recuperar a HQ criada")
    score, _ = validate_payload(snapshot_pages(loaded))
    loaded.continuity_score = score
    loaded.pedagogical_score = _pedagogical_score(loaded, facts)
    loaded.current_version = 1
    await _create_version(
        session,
        comic=loaded,
        user_id=user_id,
        scope=ComicVersionScope.INITIAL,
        description="Geração inicial estruturada da HQ",
    )
    session.add(
        ComicGenerationRun(
            comic_id=loaded.id,
            requested_by_user_id=user_id,
            scope=GenerationScope.COMIC,
            status=GenerationRunStatus.COMPLETED,
            provider="mock",
            model="narrative-mock-v1",
            configuration=data.model_dump(mode="json"),
            result_summary={
                "pages": len(loaded.pages),
                "panels": sum(len(page.panels) for page in loaded.pages),
                "continuity_score": score,
            },
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
    )
    await session.commit()
    result = await load_comic(session, organization_id=organization_id, comic_id=loaded.id)
    if result is None:
        raise ComicManagerError("Falha ao finalizar a HQ")
    return result


def _page_configurations(data: ComicCreate) -> list[dict[str, Any]]:
    overrides = {layout.page_number: layout for layout in data.page_layouts}
    configurations: list[dict[str, Any]] = []
    for page_number in range(1, data.page_count + 1):
        override = overrides.get(page_number)
        panel_count = override.panel_count if override else data.default_panels_per_page
        template = (
            override.layout_template
            if override
            else recommended_template(panel_count, page_number, data.page_count)
        )
        configurations.append(
            {
                "page_number": page_number,
                "panel_count": panel_count,
                "page_format": (override.page_format if override else data.page_format).value,
                "orientation": (override.orientation if override else data.orientation).value,
                "layout_mode": (override.layout_mode if override else LayoutMode.RECOMMENDED).value,
                "layout_template": template,
                "reading_direction": (
                    override.reading_direction if override else ReadingDirection.LEFT_TO_RIGHT
                ).value,
                "page_role": override.page_role if override else "story",
            }
        )
    return configurations


def _panel_from_generated(
    page_id: UUID,
    local_index: int,
    generated: GeneratedPanel,
    geometry: PanelLayout,
    frozen_assets: dict[str, list[dict[str, Any]]],
) -> ComicPanel:
    return ComicPanel(
        page_id=page_id,
        panel_number=local_index,
        reading_order=local_index,
        shape=PanelShape(str(geometry["shape"])),
        size_category=PanelSize(str(geometry["size_category"])),
        position_x=float(geometry["position_x"]),
        position_y=float(geometry["position_y"]),
        width=float(geometry["width"]),
        height=float(geometry["height"]),
        z_index=int(geometry["z_index"]),
        narrative_goal=generated["narrative_goal"],
        pedagogical_goal=generated["pedagogical_goal"],
        ct_pillar_codes=list(generated["ct_pillar_codes"]),
        scene_description=generated["scene_description"],
        previous_panel_summary=generated["previous_panel_summary"],
        next_panel_hook=generated["next_panel_hook"],
        initial_state=dict(generated["initial_state"]),
        final_state=dict(generated["final_state"]),
        emotion=generated["emotion"],
        plot_function=generated["plot_function"],
        locked_elements=[],
        visual_prompt=_default_visual_prompt(generated),
        frozen_assets={key: list(value) for key, value in frozen_assets.items()},
        pacing=_pacing_for_plot(generated["plot_function"]),
        alt_text=generated["scene_description"],
        audio_description=generated["scene_description"],
        text_word_limit=80,
    )


def _balloon_from_generated(panel_id: UUID, data: GeneratedBalloon) -> ComicBalloon:
    return ComicBalloon(
        panel_id=panel_id,
        sequence_number=data["sequence_number"],
        speaker_name_snapshot=data["speaker_name_snapshot"],
        balloon_type=BalloonType(data["balloon_type"]),
        text=data["text"],
        emotion=data["emotion"],
        pedagogical_function=data["pedagogical_function"],
        position_x=data["position_x"],
        position_y=data["position_y"],
        width=data["width"],
        height=data["height"],
        is_locked=False,
        layer_config={"layer": "balloon", "editable": True},
    )


def _build_synopsis(title: str, topic: str, profile: dict[str, Any]) -> str:
    genre = str(profile.get("main_genre", "aventura"))
    ending = str(profile.get("ending_type", "surpreendente"))
    return (
        f"Em {title}, uma situação de {genre} transforma {topic} em uma missão pedagógica. "
        f"Pistas, erros produtivos e uma reviravolta conduzem a um final {ending}."
    )


def snapshot_pages(comic: GeneratedComic) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for page in sorted(comic.pages, key=lambda item: item.page_number):
        panels: list[dict[str, Any]] = []
        for panel in sorted(page.panels, key=lambda item: item.reading_order):
            balloons = [
                {
                    "id": str(balloon.id),
                    "sequence_number": balloon.sequence_number,
                    "speaker_character_id": (
                        str(balloon.speaker_character_id) if balloon.speaker_character_id else None
                    ),
                    "speaker_name_snapshot": balloon.speaker_name_snapshot,
                    "balloon_type": _enum_value(balloon.balloon_type),
                    "text": balloon.text,
                    "emotion": balloon.emotion,
                    "responds_to_balloon_id": (
                        str(balloon.responds_to_balloon_id)
                        if balloon.responds_to_balloon_id
                        else None
                    ),
                    "pedagogical_function": balloon.pedagogical_function,
                    "position_x": balloon.position_x or 0.0,
                    "position_y": balloon.position_y or 0.0,
                    "width": balloon.width or 40.0,
                    "height": balloon.height or 20.0,
                    "is_locked": bool(balloon.is_locked),
                    "layer_config": dict(balloon.layer_config or {}),
                }
                for balloon in sorted(panel.balloons, key=lambda item: item.sequence_number)
            ]
            panels.append(
                {
                    "id": str(panel.id),
                    "panel_number": panel.panel_number,
                    "reading_order": panel.reading_order,
                    "shape": _enum_value(panel.shape),
                    "size_category": _enum_value(panel.size_category),
                    "position_x": panel.position_x or 0.0,
                    "position_y": panel.position_y or 0.0,
                    "width": panel.width or 48.0,
                    "height": panel.height or 48.0,
                    "border_style": panel.border_style,
                    "border_width": panel.border_width or 2.0,
                    "rotation": panel.rotation or 0.0,
                    "z_index": panel.z_index or 0,
                    "is_full_bleed": bool(panel.is_full_bleed),
                    "clipping_mode": panel.clipping_mode,
                    "narrative_goal": panel.narrative_goal,
                    "pedagogical_goal": panel.pedagogical_goal,
                    "ct_pillar_codes": list(panel.ct_pillar_codes or []),
                    "scene_description": panel.scene_description,
                    "previous_panel_summary": panel.previous_panel_summary,
                    "next_panel_hook": panel.next_panel_hook,
                    "initial_state": dict(panel.initial_state or {}),
                    "final_state": dict(panel.final_state or {}),
                    "emotion": panel.emotion,
                    "plot_function": panel.plot_function,
                    "continuity_notes": list(panel.continuity_notes or []),
                    "status": _enum_value(panel.status),
                    "locked_elements": list(panel.locked_elements or []),
                    "visual_prompt": dict(panel.visual_prompt or {}),
                    "frozen_assets": dict(panel.frozen_assets or {}),
                    "pacing": panel.pacing,
                    "image_asset_path": panel.image_asset_path,
                    "alt_text": panel.alt_text,
                    "audio_description": panel.audio_description,
                    "text_word_limit": panel.text_word_limit or 80,
                    "preview_review_status": _enum_value(panel.preview_review_status),
                    "preview_reviewed_by_user_id": str(panel.preview_reviewed_by_user_id) if panel.preview_reviewed_by_user_id else None,
                    "preview_reviewed_at": panel.preview_reviewed_at.isoformat() if panel.preview_reviewed_at else None,
                    "preview_review_notes": panel.preview_review_notes,
                    "balloons": balloons,
                }
            )
        pages.append(
            {
                "id": str(page.id),
                "page_number": page.page_number,
                "title": page.title,
                "page_format": _enum_value(page.page_format),
                "orientation": _enum_value(page.orientation),
                "layout_mode": _enum_value(page.layout_mode),
                "layout_template": page.layout_template,
                "reading_direction": _enum_value(page.reading_direction),
                "panel_count": page.panel_count or len(page.panels),
                "width": page.width or 210.0,
                "height": page.height or 297.0,
                "margins": dict(page.margins or {}),
                "notes": page.notes,
                "page_role": page.page_role,
                "background_config": page.background_config,
                "guides_config": page.guides_config,
                "preview_review_status": _enum_value(page.preview_review_status),
                "preview_reviewed_by_user_id": str(page.preview_reviewed_by_user_id) if page.preview_reviewed_by_user_id else None,
                "preview_reviewed_at": page.preview_reviewed_at.isoformat() if page.preview_reviewed_at else None,
                "preview_review_notes": page.preview_review_notes,
                "panels": panels,
            }
        )
    return pages


def snapshot_comic(comic: GeneratedComic) -> dict[str, Any]:
    return {
        "schema_version": "educode.comic.v1",
        "id": str(comic.id),
        "generation_project_id": str(comic.generation_project_id),
        "rag_context_id": str(comic.rag_context_id),
        "title": comic.title,
        "synopsis": comic.synopsis,
        "status": _enum_value(comic.status),
        "narrative_profile": dict(comic.narrative_profile),
        "layout_preferences": dict(comic.layout_preferences),
        "story_state": dict(comic.story_state),
        "continuity_score": comic.continuity_score,
        "pedagogical_score": comic.pedagogical_score,
        "notes": comic.notes,
        "review_state": dict(comic.review_state),
        "autosave_revision": comic.autosave_revision,
        "last_saved_at": comic.last_saved_at.isoformat() if comic.last_saved_at else None,
        "edit_revision": comic.edit_revision,
        "last_editor_user_id": str(comic.last_editor_user_id) if comic.last_editor_user_id else None,
        "last_editor_name_snapshot": comic.last_editor_name_snapshot,
        "last_editor_at": comic.last_editor_at.isoformat() if comic.last_editor_at else None,
        "canvas_readiness_status": comic.canvas_readiness_status,
        "preview_status": _enum_value(comic.preview_status),
        "preview_checked_at": comic.preview_checked_at.isoformat() if comic.preview_checked_at else None,
        "pages": snapshot_pages(comic),
    }


async def create_version_after_change(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    user_id: UUID,
    scope: ComicVersionScope,
    description: str,
    target_page_id: UUID | None = None,
    target_panel_id: UUID | None = None,
    target_balloon_id: UUID | None = None,
    reset_preview: bool = True,
) -> GeneratedComic:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    score, _ = validate_payload(snapshot_pages(comic))
    comic.continuity_score = score
    comic.current_version += 1
    previous_snapshot = (
        dict(comic.versions[0].snapshot_json) if comic.versions else snapshot_comic(comic)
    )
    await _create_version(
        session,
        comic=comic,
        user_id=user_id,
        scope=scope,
        description=description,
        target_page_id=target_page_id,
        target_panel_id=target_panel_id,
        target_balloon_id=target_balloon_id,
    )
    comic.autosave_revision += 1
    comic.edit_revision += 1
    comic.last_saved_at = datetime.now(UTC)
    comic.last_editor_user_id = user_id
    comic.last_editor_name_snapshot = await session.scalar(
        select(User.full_name).where(User.id == user_id)
    )
    comic.last_editor_at = datetime.now(UTC)
    comic.canvas_readiness_status = "not_ready"
    comic.canvas_readiness_checked_at = None
    if reset_preview:
        comic.preview_status = PreviewReviewStatus.NOT_REVIEWED
        comic.preview_checked_at = None
        if scope == ComicVersionScope.COMIC:
            for page in comic.pages:
                page.preview_review_status = PreviewReviewStatus.NOT_REVIEWED
                page.preview_reviewed_at = None
                page.preview_reviewed_by_user_id = None
                for panel in page.panels:
                    panel.preview_review_status = PreviewReviewStatus.NOT_REVIEWED
                    panel.preview_reviewed_at = None
                    panel.preview_reviewed_by_user_id = None
        elif target_page_id is not None:
            page = next((item for item in comic.pages if item.id == target_page_id), None)
            if page is not None:
                page.preview_review_status = PreviewReviewStatus.NOT_REVIEWED
                page.preview_reviewed_at = None
                page.preview_reviewed_by_user_id = None
                for panel in page.panels:
                    panel.preview_review_status = PreviewReviewStatus.NOT_REVIEWED
                    panel.preview_reviewed_at = None
                    panel.preview_reviewed_by_user_id = None
        elif target_panel_id is not None:
            for page in comic.pages:
                panel = next((item for item in page.panels if item.id == target_panel_id), None)
                if panel is not None:
                    panel.preview_review_status = PreviewReviewStatus.NOT_REVIEWED
                    panel.preview_reviewed_at = None
                    panel.preview_reviewed_by_user_id = None
                    page.preview_review_status = PreviewReviewStatus.IN_REVIEW
                    break
    session.add(
        ComicEditOperation(
            comic_id=comic.id,
            actor_user_id=user_id,
            operation_type=description,
            target_page_id=target_page_id,
            target_panel_id=target_panel_id,
            target_balloon_id=target_balloon_id,
            before_snapshot=previous_snapshot,
            after_snapshot=snapshot_comic(comic),
        )
    )
    await session.commit()
    refreshed = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if refreshed is None:
        raise ComicManagerError("Falha ao atualizar a versão")
    return refreshed


async def _create_version(
    session: AsyncSession,
    *,
    comic: GeneratedComic,
    user_id: UUID,
    scope: ComicVersionScope,
    description: str,
    target_page_id: UUID | None = None,
    target_panel_id: UUID | None = None,
    target_balloon_id: UUID | None = None,
) -> ComicVersion:
    version = ComicVersion(
        comic_id=comic.id,
        version_number=comic.current_version,
        scope=scope,
        target_page_id=target_page_id,
        target_panel_id=target_panel_id,
        target_balloon_id=target_balloon_id,
        change_description=description,
        snapshot_json=snapshot_comic(comic),
        created_by_user_id=user_id,
    )
    session.add(version)
    await session.flush()
    return version


async def regenerate(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    user_id: UUID,
    data: RegenerateRequest,
) -> GeneratedComic:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    run = ComicGenerationRun(
        comic_id=comic.id,
        requested_by_user_id=user_id,
        scope=data.scope,
        target_page_id=data.page_id,
        target_panel_id=data.panel_id,
        status=GenerationRunStatus.RUNNING,
        provider="mock",
        model="narrative-mock-v1",
        configuration=data.model_dump(mode="json"),
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()
    targets = _regeneration_targets(comic, data)
    if not targets:
        run.status = GenerationRunStatus.FAILED
        run.error_message = "Nenhum quadro corresponde ao escopo solicitado"
        run.finished_at = datetime.now(UTC)
        await session.commit()
        raise ComicManagerError(run.error_message)

    for panel in targets:
        generated = _generated_from_model(panel)
        updated = regenerate_panel_content(
            generated,
            scope=data.scope.value,
            instruction=data.change_instruction,
            preserve_dialogue=data.preserve_dialogue,
            preserve_scene=data.preserve_scene,
        )
        _apply_locked_regeneration(panel, updated, data.scope)
        panel.continuity_notes = [
            "Conteúdo regenerado de forma granular respeitando bloqueios.",
            "Revisar impacto nos quadros seguintes antes da aprovação.",
        ]
    await session.flush()
    run.status = GenerationRunStatus.COMPLETED
    run.result_summary = {"affected_panels": len(targets), "scope": data.scope.value}
    run.finished_at = datetime.now(UTC)
    comic.current_version += 1
    refreshed_before_version = await load_comic(
        session, organization_id=organization_id, comic_id=comic_id
    )
    if refreshed_before_version is None:
        raise ComicManagerError("Falha ao reconstruir a HQ")
    score, _ = validate_payload(snapshot_pages(refreshed_before_version))
    refreshed_before_version.continuity_score = score
    await _create_version(
        session,
        comic=refreshed_before_version,
        user_id=user_id,
        scope=ComicVersionScope.PANEL
        if data.scope != GenerationScope.PAGE
        else ComicVersionScope.PAGE,
        description=f"Regeneração parcial: {data.scope.value}",
        target_page_id=data.page_id,
        target_panel_id=data.panel_id,
    )
    await session.commit()
    result = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if result is None:
        raise ComicManagerError("Falha ao finalizar a regeneração")
    return result


def _regeneration_targets(comic: GeneratedComic, data: RegenerateRequest) -> list[ComicPanel]:
    all_panels = [
        panel
        for page in sorted(comic.pages, key=lambda item: item.page_number)
        for panel in sorted(page.panels, key=lambda item: item.reading_order)
    ]
    if data.scope == GenerationScope.COMIC:
        return all_panels
    if data.scope == GenerationScope.PAGE:
        return [panel for page in comic.pages if page.id == data.page_id for panel in page.panels]
    selected_index = next(
        (index for index, panel in enumerate(all_panels) if panel.id == data.panel_id), None
    )
    if selected_index is None:
        return []
    if data.scope == GenerationScope.FROM_PANEL:
        return all_panels[selected_index:]
    return [all_panels[selected_index]]


def _generated_from_model(panel: ComicPanel) -> GeneratedPanel:
    balloons: list[GeneratedBalloon] = [
        {
            "sequence_number": balloon.sequence_number,
            "speaker_name_snapshot": balloon.speaker_name_snapshot,
            "balloon_type": _enum_value(balloon.balloon_type),
            "text": balloon.text,
            "emotion": balloon.emotion,
            "pedagogical_function": balloon.pedagogical_function,
            "position_x": balloon.position_x or 0.0,
            "position_y": balloon.position_y or 0.0,
            "width": balloon.width or 40.0,
            "height": balloon.height or 20.0,
        }
        for balloon in sorted(panel.balloons, key=lambda item: item.sequence_number)
    ]
    return {
        "narrative_goal": panel.narrative_goal,
        "pedagogical_goal": panel.pedagogical_goal,
        "ct_pillar_codes": list(panel.ct_pillar_codes or []),
        "scene_description": panel.scene_description,
        "previous_panel_summary": panel.previous_panel_summary,
        "next_panel_hook": panel.next_panel_hook,
        "initial_state": dict(panel.initial_state or {}),
        "final_state": dict(panel.final_state or {}),
        "emotion": panel.emotion,
        "plot_function": panel.plot_function,
        "balloons": balloons,
    }


def validate_comic(comic: GeneratedComic) -> tuple[float, list[ContinuityFinding]]:
    return validate_payload(snapshot_pages(comic))


def canvas_export(comic: GeneratedComic) -> dict[str, object]:
    document = snapshot_comic(comic)
    document["canvas"] = {
        "coordinate_system": "percentage",
        "unit": "%",
        "editable_layers": ["page", "panel", "balloon", "caption"],
        "reading_order_locked": False,
        "external_editor_ready": True,
    }
    return {
        "schema_version": "educode.canvas.v1",
        "editor": "EduCode Canvas / external editor bridge",
        "document": cast(dict[str, object], document),
    }


def _pedagogical_score(comic: GeneratedComic, facts: list[str]) -> float:
    dialogue_text = " ".join(
        balloon.text.lower()
        for page in comic.pages
        for panel in page.panels
        for balloon in panel.balloons
    )
    if not facts:
        return 70.0
    matches = sum(
        1
        for fact in facts
        if any(word in dialogue_text for word in fact.lower().split() if len(word) > 5)
    )
    return min(100.0, 60.0 + (40.0 * matches / len(facts)))


async def resize_page(
    session: AsyncSession,
    *,
    comic: GeneratedComic,
    page: ComicPage,
    panel_count: int,
    layout_template: str,
) -> None:
    ordered = sorted(page.panels, key=lambda item: item.reading_order)
    if panel_count < len(ordered):
        for panel in ordered[panel_count:]:
            await session.delete(panel)
        ordered = ordered[:panel_count]
    elif panel_count > len(ordered):
        previous = ordered[-1] if ordered else None
        for index in range(len(ordered) + 1, panel_count + 1):
            panel = ComicPanel(
                page_id=page.id,
                panel_number=index,
                reading_order=index,
                narrative_goal="Desenvolver a continuidade da cena adicionada.",
                pedagogical_goal=(
                    previous.pedagogical_goal
                    if previous is not None
                    else "Consolidar o objetivo pedagógico da página."
                ),
                ct_pillar_codes=(list(previous.ct_pillar_codes) if previous is not None else []),
                scene_description="Novo quadro adicionado para edição do professor.",
                previous_panel_summary=(
                    previous.narrative_goal if previous is not None else "Início da página."
                ),
                next_panel_hook="Defina o gancho para o próximo quadro.",
                initial_state=(dict(previous.final_state) if previous is not None else {}),
                final_state=(dict(previous.final_state) if previous is not None else {}),
                emotion="curiosity",
                plot_function="development",
                locked_elements=[],
                visual_prompt=(
                    dict(previous.visual_prompt)
                    if previous is not None
                    else {
                        "shot_type": "medium_shot",
                        "image_without_balloons": True,
                        "must_avoid": ["embedded_text"],
                    }
                ),
                frozen_assets=(dict(previous.frozen_assets) if previous is not None else {}),
                pacing="moderate",
                alt_text="Novo quadro adicionado para edição do professor.",
                audio_description="Novo quadro adicionado para edição do professor.",
                text_word_limit=80,
            )
            session.add(panel)
            await session.flush()
            session.add(
                ComicBalloon(
                    panel_id=panel.id,
                    sequence_number=1,
                    balloon_type=BalloonType.CAPTION,
                    text="Edite esta nova cena e conecte-a ao quadro anterior.",
                    pedagogical_function="editor_placeholder",
                    is_locked=False,
                    layer_config={"layer": "balloon", "editable": True},
                )
            )
            ordered.append(panel)
            previous = panel
    layout = layout_for(layout_template, panel_count)
    for index, (panel, geometry) in enumerate(zip(ordered, layout, strict=True), start=1):
        panel.panel_number = index
        panel.reading_order = index
        panel.shape = PanelShape(str(geometry["shape"]))
        panel.size_category = PanelSize(str(geometry["size_category"]))
        panel.position_x = float(geometry["position_x"])
        panel.position_y = float(geometry["position_y"])
        panel.width = float(geometry["width"])
        panel.height = float(geometry["height"])
        panel.z_index = int(geometry["z_index"])
    page.panel_count = panel_count
    page.layout_template = layout_template
    page.layout_mode = LayoutMode.TEMPLATE
    await session.flush()


async def restore_version(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    version_id: UUID,
    user_id: UUID,
    description: str,
) -> GeneratedComic:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    version = await session.scalar(
        select(ComicVersion).where(
            ComicVersion.id == version_id,
            ComicVersion.comic_id == comic.id,
        )
    )
    if version is None:
        raise ComicManagerError("Versão não encontrada")
    snapshot = version.snapshot_json
    pages_data = snapshot.get("pages", [])
    if not isinstance(pages_data, list):
        raise ComicManagerError("A versão armazenada possui estrutura inválida")

    comic.title = str(snapshot.get("title", comic.title))
    comic.synopsis = str(snapshot.get("synopsis", comic.synopsis))
    comic.narrative_profile = _dict_value(snapshot.get("narrative_profile"))
    comic.layout_preferences = _dict_value(snapshot.get("layout_preferences"))
    comic.story_state = _dict_value(snapshot.get("story_state"))
    comic.notes = str(snapshot["notes"]) if snapshot.get("notes") is not None else None
    comic.review_state = _dict_value(snapshot.get("review_state"))
    for page in list(comic.pages):
        await session.delete(page)
    await session.flush()

    for page_data_raw in pages_data:
        if not isinstance(page_data_raw, dict):
            continue
        page_data = cast(dict[str, Any], page_data_raw)
        page = ComicPage(
            comic_id=comic.id,
            page_number=int(page_data.get("page_number", 1)),
            title=_optional_str(page_data.get("title")),
            page_format=PageFormat(str(page_data.get("page_format", PageFormat.A4.value))),
            orientation=PageOrientation(
                str(page_data.get("orientation", PageOrientation.PORTRAIT.value))
            ),
            layout_mode=LayoutMode(str(page_data.get("layout_mode", LayoutMode.TEMPLATE.value))),
            layout_template=str(page_data.get("layout_template", "grid_2x2")),
            reading_direction=ReadingDirection(
                str(page_data.get("reading_direction", ReadingDirection.LEFT_TO_RIGHT.value))
            ),
            panel_count=int(page_data.get("panel_count", 1)),
            width=float(page_data.get("width", 210.0)),
            height=float(page_data.get("height", 297.0)),
            margins=_dict_value(page_data.get("margins")),
            notes=_optional_str(page_data.get("notes")),
        )
        session.add(page)
        await session.flush()
        panels_data = page_data.get("panels", [])
        if not isinstance(panels_data, list):
            continue
        for panel_data_raw in panels_data:
            if not isinstance(panel_data_raw, dict):
                continue
            panel_data = cast(dict[str, Any], panel_data_raw)
            panel = ComicPanel(
                page_id=page.id,
                panel_number=int(panel_data.get("panel_number", 1)),
                reading_order=int(panel_data.get("reading_order", 1)),
                shape=PanelShape(str(panel_data.get("shape", PanelShape.RECTANGLE.value))),
                size_category=PanelSize(
                    str(panel_data.get("size_category", PanelSize.MEDIUM.value))
                ),
                position_x=float(panel_data.get("position_x", 0.0)),
                position_y=float(panel_data.get("position_y", 0.0)),
                width=float(panel_data.get("width", 48.0)),
                height=float(panel_data.get("height", 48.0)),
                border_style=str(panel_data.get("border_style", "solid")),
                border_width=float(panel_data.get("border_width", 2.0)),
                rotation=float(panel_data.get("rotation", 0.0)),
                z_index=int(panel_data.get("z_index", 0)),
                is_full_bleed=bool(panel_data.get("is_full_bleed", False)),
                clipping_mode=str(panel_data.get("clipping_mode", "cover")),
                narrative_goal=str(panel_data.get("narrative_goal", "")),
                pedagogical_goal=str(panel_data.get("pedagogical_goal", "")),
                ct_pillar_codes=_list_str_value(panel_data.get("ct_pillar_codes")),
                scene_description=str(panel_data.get("scene_description", "")),
                previous_panel_summary=str(panel_data.get("previous_panel_summary", "")),
                next_panel_hook=str(panel_data.get("next_panel_hook", "")),
                initial_state=_dict_value(panel_data.get("initial_state")),
                final_state=_dict_value(panel_data.get("final_state")),
                emotion=str(panel_data.get("emotion", "curiosity")),
                plot_function=str(panel_data.get("plot_function", "development")),
                continuity_notes=_list_str_value(panel_data.get("continuity_notes")),
                locked_elements=_list_str_value(panel_data.get("locked_elements")),
                visual_prompt=_dict_value(panel_data.get("visual_prompt")),
                frozen_assets=_dict_value(panel_data.get("frozen_assets")),
                pacing=str(panel_data.get("pacing", "moderate")),
                image_asset_path=_optional_str(panel_data.get("image_asset_path")),
                alt_text=_optional_str(panel_data.get("alt_text")),
                audio_description=_optional_str(panel_data.get("audio_description")),
                text_word_limit=int(panel_data.get("text_word_limit", 80)),
            )
            session.add(panel)
            await session.flush()
            balloons_data = panel_data.get("balloons", [])
            if not isinstance(balloons_data, list):
                continue
            for balloon_data_raw in balloons_data:
                if not isinstance(balloon_data_raw, dict):
                    continue
                balloon_data = cast(dict[str, Any], balloon_data_raw)
                session.add(
                    ComicBalloon(
                        panel_id=panel.id,
                        sequence_number=int(balloon_data.get("sequence_number", 1)),
                        speaker_name_snapshot=_optional_str(
                            balloon_data.get("speaker_name_snapshot")
                        ),
                        balloon_type=BalloonType(
                            str(balloon_data.get("balloon_type", BalloonType.SPEECH.value))
                        ),
                        text=str(balloon_data.get("text", "Texto restaurado")),
                        emotion=_optional_str(balloon_data.get("emotion")),
                        pedagogical_function=_optional_str(
                            balloon_data.get("pedagogical_function")
                        ),
                        position_x=float(balloon_data.get("position_x", 10.0)),
                        position_y=float(balloon_data.get("position_y", 10.0)),
                        width=float(balloon_data.get("width", 40.0)),
                        height=float(balloon_data.get("height", 20.0)),
                        is_locked=bool(balloon_data.get("is_locked", False)),
                        layer_config=_dict_value(balloon_data.get("layer_config")),
                    )
                )
    await session.flush()
    comic.current_version += 1
    restored = await load_comic(session, organization_id=organization_id, comic_id=comic.id)
    if restored is None:
        raise ComicManagerError("Falha ao restaurar a versão")
    score, _ = validate_payload(snapshot_pages(restored))
    restored.continuity_score = score
    await _create_version(
        session,
        comic=restored,
        user_id=user_id,
        scope=ComicVersionScope.RESTORE,
        description=description,
    )
    await session.commit()
    result = await load_comic(session, organization_id=organization_id, comic_id=comic.id)
    if result is None:
        raise ComicManagerError("Falha ao finalizar a restauração")
    return result


def _default_visual_prompt(generated: GeneratedPanel) -> dict[str, Any]:
    state = generated.get("final_state", {})
    characters = state.get("characters_present", []) if isinstance(state, dict) else []
    return {
        "shot_type": "medium_shot",
        "characters": list(characters) if isinstance(characters, list) else [],
        "action": generated["narrative_goal"],
        "expressions": {"dominant": generated["emotion"]},
        "scene": generated["scene_description"],
        "lighting": "educational_cinematic",
        "must_include": [],
        "must_avoid": ["embedded_text", "extra_characters"],
        "image_without_balloons": True,
    }


def _pacing_for_plot(plot_function: str) -> str:
    return {
        "opening": "moderate",
        "comedy": "fast",
        "clue": "pause",
        "failure": "impactful",
        "emotional": "slow",
        "plot_twist": "revelation",
        "resolution": "moderate",
    }.get(plot_function, "moderate")


def _apply_locked_regeneration(
    panel: ComicPanel, updated: GeneratedPanel, scope: GenerationScope
) -> None:
    locks = set(panel.locked_elements)
    if scope in {GenerationScope.SCENE, GenerationScope.PANEL, GenerationScope.FROM_PANEL}:
        if "scene" not in locks and "panel" not in locks:
            panel.scene_description = updated["scene_description"]
            panel.visual_prompt = _default_visual_prompt(updated)
    if (
        scope
        in {
            GenerationScope.BALLOONS,
            GenerationScope.DIALOGUE,
            GenerationScope.PANEL,
            GenerationScope.FROM_PANEL,
        }
        and "dialogue" not in locks
        and "balloons" not in locks
        and "panel" not in locks
    ):
        generated_balloons = list(updated["balloons"])
        current = sorted(panel.balloons, key=lambda item: item.sequence_number)
        for index, balloon in enumerate(current):
            if balloon.is_locked or index >= len(generated_balloons):
                continue
            proposal = generated_balloons[index]
            balloon.text = str(proposal["text"])
            balloon.emotion = _optional_str(proposal.get("emotion"))
            balloon.pedagogical_function = _optional_str(proposal.get("pedagogical_function"))
    panel.status = PanelStatus.NEEDS_REVIEW


def _dict_value(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _list_str_value(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None
