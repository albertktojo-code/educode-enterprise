from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comic import (
    ComicBalloon,
    ComicPage,
    ComicPanel,
    ComicVersionScope,
    GeneratedComic,
    PanelShape,
    PanelSize,
)
from app.models.studio import (
    ArtDirectionPreset,
    PackageMaterial,
    PackageMaterialStatus,
    PackageStatus,
    PedagogicalPackage,
    PublicationPreparation,
    PublicationReadiness,
    StudioDraftStatus,
    StudioMaterialType,
    TeacherStudioDraft,
)
from app.schemas.comic import ComicCreate, NarrativeProfile, PageLayoutInput
from app.schemas.studio import (
    CanvasBulkUpdate,
    PackageCreateRequest,
    PageCreateRequest,
    RecommendPagesRequest,
    TeacherStudioDraftCreate,
)
from app.services.comics.layouts import layout_for, recommended_template
from app.services.comics.manager import create_comic, create_version_after_change


SYSTEM_ART_PRESETS: list[dict[str, Any]] = [
    {
        "code": "manga_educational",
        "name": "Mangá educativo",
        "category": "manga",
        "description": "Ritmo dinâmico, expressões fortes e leitura visual clara.",
        "preview_config": {"color_mode": "black_white", "line_weight": "expressive", "energy": 4},
        "visual_rules": {"panel_rhythm": "dynamic", "expressions": "strong", "text_in_image": False},
        "age_groups": ["anos_finais", "ensino_medio"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "american_comic",
        "name": "HQ americana",
        "category": "american",
        "description": "Composição impactante, ação visual e cores intensas.",
        "preview_config": {"color_mode": "color", "line_weight": "bold", "energy": 5},
        "visual_rules": {"panel_rhythm": "cinematic", "expressions": "medium", "text_in_image": False},
        "age_groups": ["anos_finais", "ensino_medio"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "european_comic",
        "name": "Quadrinho europeu",
        "category": "european",
        "description": "Cenários detalhados, narrativa contemplativa e composição elegante.",
        "preview_config": {"color_mode": "color", "line_weight": "fine", "energy": 2},
        "visual_rules": {"panel_rhythm": "measured", "background_detail": "high", "text_in_image": False},
        "age_groups": ["anos_finais", "ensino_medio"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "cartoon_educational",
        "name": "Cartoon educativo",
        "category": "cartoon",
        "description": "Traço amigável, cores vivas e leitura simples para uso escolar.",
        "preview_config": {"color_mode": "color", "line_weight": "rounded", "energy": 3},
        "visual_rules": {"panel_rhythm": "clear", "expressions": "clear", "text_in_image": False},
        "age_groups": ["anos_iniciais", "anos_finais"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "anime_school",
        "name": "Anime escolar",
        "category": "anime",
        "description": "Personagens expressivos, atmosfera juvenil e cenas escolares acolhedoras.",
        "preview_config": {"color_mode": "color", "lighting": "soft", "energy": 3},
        "visual_rules": {"camera": "character_focused", "expressions": "high", "text_in_image": False},
        "age_groups": ["anos_finais", "ensino_medio"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "anime_adventure",
        "name": "Anime de aventura",
        "category": "anime",
        "description": "Cenas cinematográficas, ação, mistério e emoção em alta intensidade.",
        "preview_config": {"color_mode": "color", "lighting": "dramatic", "energy": 5},
        "visual_rules": {"camera": "cinematic", "motion": "high", "text_in_image": False},
        "age_groups": ["anos_finais", "ensino_medio"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "children_educational",
        "name": "Infantil lúdico",
        "category": "children",
        "description": "Formas arredondadas, alto contraste e pouco texto por quadro.",
        "preview_config": {"color_mode": "color", "line_weight": "soft", "energy": 2},
        "visual_rules": {"shapes": "rounded", "visual_density": "low", "text_in_image": False},
        "age_groups": ["educacao_infantil", "anos_iniciais"],
        "is_system": True,
        "is_active": True,
    },
    {
        "code": "sci_fi_educational",
        "name": "Ficção científica educativa",
        "category": "sci_fi",
        "description": "Tecnologia, exploração e cenários futuristas para missões pedagógicas.",
        "preview_config": {"color_mode": "color", "lighting": "neon_soft", "energy": 4},
        "visual_rules": {"background_detail": "medium", "technology": "friendly", "text_in_image": False},
        "age_groups": ["anos_finais", "ensino_medio"],
        "is_system": True,
        "is_active": True,
    },
]


STUDIO_TEMPLATES: list[dict[str, Any]] = [
    {"code": "comic_short", "name": "HQ curta", "description": "Capa, quatro páginas e atividade.", "outputs": ["comic", "exercise", "answer_key"], "story_pages": 4},
    {"code": "comic_mystery", "name": "HQ de mistério", "description": "Seis páginas com pistas e reviravolta.", "outputs": ["comic", "quiz", "answer_key"], "story_pages": 6},
    {"code": "review_pack", "name": "Pacote de revisão", "description": "HQ, quiz e atividade prática.", "outputs": ["comic", "quiz", "activity", "answer_key"], "story_pages": 4},
    {"code": "complete_sequence", "name": "Sequência completa", "description": "Plano de aula, HQ, exercício e guia docente.", "outputs": ["lesson_plan", "comic", "exercise", "answer_key", "teacher_guide"], "story_pages": 6},
]


def recommend_page_plan(data: RecommendPagesRequest) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    number = 1
    if data.include_cover:
        pages.append({"page_number": number, "role": "cover", "panel_count": 1, "layout_template": "single_full", "narrative_function": "presentation"})
        number += 1
    functions = ["context", "problem", "investigation", "complication", "clue", "plot_twist", "application", "resolution"]
    for index in range(data.story_pages):
        function = functions[min(index * len(functions) // max(data.story_pages, 1), len(functions) - 1)]
        panel_count = 3 if function in {"context", "plot_twist", "resolution"} else 4 if index % 2 == 0 else 5
        pages.append({
            "page_number": number,
            "role": "story",
            "panel_count": panel_count,
            "layout_template": recommended_template(panel_count, index + 1, data.story_pages),
            "narrative_function": function,
        })
        number += 1
    if data.include_exercises:
        pages.append({"page_number": number, "role": "exercises", "panel_count": 2, "layout_template": "two_horizontal", "narrative_function": "practice"})
        number += 1
    if data.include_answer_key:
        pages.append({"page_number": number, "role": "answer_key", "panel_count": 1, "layout_template": "single_full", "narrative_function": "feedback"})
        number += 1
    if data.include_teacher_guide:
        pages.append({"page_number": number, "role": "teacher_guide", "panel_count": 1, "layout_template": "single_full", "narrative_function": "teacher_orientation"})
    return pages


def material_content(material_type: StudioMaterialType, draft: TeacherStudioDraft) -> dict[str, Any]:
    common = {"topic": draft.topic, "objective": draft.objective, "school_year": draft.school_year, "subject": draft.subject_name}
    if material_type == StudioMaterialType.QUIZ:
        return {**common, "question_count": 5, "question_types": ["multiple_choice"], "feedback": "immediate_mock"}
    if material_type == StudioMaterialType.EXERCISE:
        return {**common, "exercise_count": 6, "difficulty_progression": ["basic", "intermediate", "application"]}
    if material_type == StudioMaterialType.ACTIVITY:
        return {**common, "format": "collaborative", "estimated_minutes": 25}
    if material_type == StudioMaterialType.GAME:
        return {**common, "game_loop": ["challenge", "feedback", "progress"], "scoring": "mock"}
    if material_type == StudioMaterialType.LESSON_PLAN:
        return {**common, "duration_minutes": 50, "phases": ["opening", "development", "assessment"]}
    if material_type == StudioMaterialType.ANSWER_KEY:
        return {**common, "answers": [], "teacher_only": True}
    if material_type == StudioMaterialType.TEACHER_GUIDE:
        return {**common, "guidance": ["learning goals", "CT integration", "adaptations"]}
    if material_type == StudioMaterialType.TEACHING_SEQUENCE:
        return {**common, "steps": ["diagnostic", "comic", "practice", "assessment"]}
    return {**common, "page_plan": draft.page_plan, "art_direction": draft.art_direction}


def publication_checklist(package: PedagogicalPackage, comic: GeneratedComic | None) -> tuple[PublicationReadiness, list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    def add(code: str, label: str, passed: bool, blocking: bool = True) -> None:
        items.append({"code": code, "label": label, "passed": passed, "blocking": blocking})
    add("materials", "Todos os materiais foram gerados", bool(package.materials))
    add("shared_context", "Contexto pedagógico compartilhado registrado", bool(package.shared_context))
    add("art_direction", "Direção de arte definida", bool(package.art_direction_snapshot), False)
    if comic is not None:
        add("comic_pages", "HQ possui páginas", bool(comic.pages))
        add("canvas", "HQ pronta para o canvas", comic.canvas_readiness_status in {"ready", "ready_with_warnings"})
        add("balloons_separate", "Balões permanecem separados das imagens", True)
    blockers = [item for item in items if item["blocking"] and not item["passed"]]
    warnings = [item for item in items if not item["blocking"] and not item["passed"]]
    readiness = PublicationReadiness.NOT_READY if blockers else PublicationReadiness.READY_WITH_WARNINGS if warnings else PublicationReadiness.READY
    return readiness, items


async def get_draft(session: AsyncSession, organization_id: UUID, draft_id: UUID) -> TeacherStudioDraft | None:
    return await session.scalar(select(TeacherStudioDraft).where(TeacherStudioDraft.id == draft_id, TeacherStudioDraft.organization_id == organization_id))


async def get_package(session: AsyncSession, organization_id: UUID, package_id: UUID) -> PedagogicalPackage | None:
    return await session.scalar(
        select(PedagogicalPackage)
        .where(PedagogicalPackage.id == package_id, PedagogicalPackage.organization_id == organization_id)
        .options(selectinload(PedagogicalPackage.materials), selectinload(PedagogicalPackage.publication_preparations))
    )


async def create_package(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    user_name: str,
    draft: TeacherStudioDraft,
    request: PackageCreateRequest,
) -> PedagogicalPackage:
    output_values = [
        item.value if isinstance(item, StudioMaterialType) else str(item)
        for item in (request.outputs or draft.selected_outputs)
    ]
    comic_id = request.comic_id
    if (
        comic_id is None
        and StudioMaterialType.COMIC.value in output_values
        and draft.generation_project_id is not None
        and draft.rag_context_id is not None
    ):
        page_plan = draft.page_plan or recommend_page_plan(RecommendPagesRequest())
        page_layouts = [
            PageLayoutInput(
                page_number=int(item.get("page_number", index)),
                panel_count=int(item.get("panel_count", 4)),
                layout_template=str(item.get("layout_template", "grid_2x2")),
                page_role=str(item.get("role", "story")),
            )
            for index, item in enumerate(page_plan, start=1)
        ]
        profile_data = draft.wizard_data.get("narrative_profile", {})
        narrative_profile = NarrativeProfile.model_validate(profile_data or {})
        comic = await create_comic(
            session,
            organization_id=organization_id,
            user_id=user_id,
            user_name=user_name,
            data=ComicCreate(
                generation_project_id=draft.generation_project_id,
                rag_context_id=draft.rag_context_id,
                title=draft.title,
                page_count=len(page_layouts),
                default_panels_per_page=4,
                narrative_profile=narrative_profile,
                art_direction=draft.art_direction,
                page_layouts=page_layouts,
                notes="Gerada pelo Estúdio do Professor.",
            ),
        )
        comic_id = comic.id
    package = PedagogicalPackage(
        organization_id=organization_id,
        draft_id=draft.id,
        generation_project_id=draft.generation_project_id,
        comic_id=comic_id,
        created_by_user_id=user_id,
        created_by_name_snapshot=user_name,
        title=draft.title,
        outputs=output_values,
        shared_context={"topic": draft.topic, "objective": draft.objective, "subject": draft.subject_name, "school_year": draft.school_year},
        art_direction_snapshot=draft.art_direction,
        status=PackageStatus.READY,
        preparation_report={"generated_by": "deterministic-mock-v1", "generated_at": datetime.now(UTC).isoformat()},
    )
    session.add(package)
    await session.flush()
    for position, output in enumerate(output_values, start=1):
        material_type = StudioMaterialType(output)
        package.materials.append(PackageMaterial(
            material_type=material_type,
            title=f"{draft.title} — {material_type.value.replace('_', ' ').title()}",
            content=material_content(material_type, draft),
            status=PackageMaterialStatus.READY,
            position=position,
        ))
    draft.status = StudioDraftStatus.READY
    await session.flush()
    return await get_package(session, organization_id, package.id) or package


async def apply_canvas_bulk(
    session: AsyncSession,
    *,
    comic: GeneratedComic,
    data: CanvasBulkUpdate,
    user_id: UUID,
) -> GeneratedComic:
    if data.expected_revision is not None and data.expected_revision != comic.edit_revision:
        raise ValueError(f"Revisão desatualizada. Servidor: {comic.edit_revision}")
    page = next((item for item in comic.pages if item.id == data.page_id), None)
    if page is None:
        raise ValueError("Página não encontrada")
    panels = {panel.id: panel for panel in page.panels}
    balloons = {balloon.id: balloon for panel in page.panels for balloon in panel.balloons}
    for placement in data.panels:
        panel = panels.get(placement.panel_id)
        if panel is None:
            continue
        for field in ("position_x", "position_y", "width", "height", "rotation", "z_index"):
            setattr(panel, field, getattr(placement, field))
    for placement in data.balloons:
        balloon = balloons.get(placement.balloon_id)
        if balloon is None or balloon.is_locked:
            continue
        for field in ("position_x", "position_y", "width", "height", "layer_config"):
            setattr(balloon, field, getattr(placement, field))
    comic.canvas_config = data.canvas_config
    await session.flush()
    return await create_version_after_change(
        session,
        organization_id=comic.organization_id,
        comic_id=comic.id,
        user_id=user_id,
        scope=ComicVersionScope.PAGE,
        description=f"Composição visual da página {page.page_number}",
        target_page_id=page.id,
    )


async def add_page(session: AsyncSession, comic: GeneratedComic, data: PageCreateRequest) -> GeneratedComic:
    number = len(comic.pages) + 1
    page = ComicPage(
        comic_id=comic.id,
        page_number=number,
        title=data.title,
        page_role=data.role,
        layout_template=data.layout_template,
        panel_count=data.panel_count,
        margins={"top": 3, "right": 3, "bottom": 3, "left": 3},
        guides_config={"snap": True, "grid": 2, "safe_margin": 3},
    )
    comic.pages.append(page)
    await session.flush()
    for index, placement in enumerate(layout_for(data.layout_template, data.panel_count), start=1):
        page.panels.append(ComicPanel(
            page_id=page.id,
            panel_number=index,
            reading_order=index,
            shape=PanelShape(placement["shape"]),
            size_category=PanelSize(placement["size_category"]),
            position_x=placement["position_x"],
            position_y=placement["position_y"],
            width=placement["width"],
            height=placement["height"],
            z_index=placement["z_index"],
            narrative_goal="Nova cena",
            pedagogical_goal="",
            scene_description="Descreva ou gere esta cena.",
            previous_panel_summary="",
            next_panel_hook="",
        ))
    await session.flush()
    return comic


async def duplicate_page(session: AsyncSession, comic: GeneratedComic, page_id: UUID) -> GeneratedComic:
    source = next((page for page in comic.pages if page.id == page_id), None)
    if source is None:
        raise ValueError("Página não encontrada")
    request = PageCreateRequest(role=source.page_role, panel_count=source.panel_count, layout_template=source.layout_template, title=f"{source.title or 'Página'} (cópia)")
    await add_page(session, comic, request)
    target = max(comic.pages, key=lambda item: item.page_number)
    for source_panel, target_panel in zip(source.panels, target.panels, strict=False):
        for field in ("narrative_goal", "pedagogical_goal", "ct_pillar_codes", "scene_description", "previous_panel_summary", "next_panel_hook", "initial_state", "final_state", "emotion", "plot_function", "continuity_notes", "visual_prompt", "frozen_assets", "pacing", "alt_text", "audio_description"):
            setattr(target_panel, field, getattr(source_panel, field))
        for balloon in source_panel.balloons:
            target_panel.balloons.append(ComicBalloon(
                sequence_number=balloon.sequence_number,
                speaker_character_id=balloon.speaker_character_id,
                speaker_name_snapshot=balloon.speaker_name_snapshot,
                balloon_type=balloon.balloon_type,
                text=balloon.text,
                emotion=balloon.emotion,
                pedagogical_function=balloon.pedagogical_function,
                position_x=balloon.position_x,
                position_y=balloon.position_y,
                width=balloon.width,
                height=balloon.height,
                layer_config=balloon.layer_config,
            ))
    await session.flush()
    return comic
