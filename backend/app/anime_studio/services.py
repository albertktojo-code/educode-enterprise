from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.anime_studio.models import (
    AnimeAudioTrack,
    AnimeCaptionCue,
    AnimeProject,
    AnimeRender,
    AnimeScene,
)
from app.anime_studio.schemas import (
    AnimeAudioTrackCreate,
    AnimeAudioTrackUpdate,
    AnimeCaptionCreate,
    AnimeCaptionUpdate,
    AnimeMediaGenerationCreate,
    AnimeMediaGenerationReview,
    AnimeProjectCreate,
    AnimeProjectUpdate,
    AnimePublicationCreate,
    AnimePublicationLibraryItem,
    AnimePublicationRead,
    AnimePublicationRendition,
    AnimePublicationTranscriptCue,
    AnimeRenderCreate,
    AnimeRenderReview,
    AnimeSceneCreate,
    AnimeSceneSplit,
    AnimeSceneUpdate,
    AnimeStoryboardImport,
    AnimeTimelineReorder,
)
from app.api.actor_context import ActorContext
from app.models.assets import (
    InstitutionalAsset,
    InstitutionalAssetAudit,
    InstitutionalAssetFile,
    InstitutionalAssetStatus,
)
from app.models.comic import ComicPage, ComicPanel, GeneratedComic
from app.models.education import Classroom, ClassroomEnrollment
from app.models.operations import BackgroundJob
from app.models.pedagogy import GenerationProject
from app.models.rag import RagContext
from app.models.studio import TeacherStudioDraft
from app.services.comics.manager import load_comic
from app.services.comics.preview import build_storyboard
from app.services.consolidated_audit import append_domain_audit
from app.services.operations import create_job, mark_queued

EDITOR_ROLES = {"OWNER", "ADMIN", "ORG_ADMIN", "TEACHER", "EDITOR"}
REVIEWER_ROLES = {"OWNER", "ADMIN", "ORG_ADMIN", "TEACHER", "REVIEWER"}
MEDIA_GENERATION_RATES = {
    "image": 0.04,
    "animation": 0.02,
    "voice": 0.006,
    "lip_sync": 0.012,
    "music": 0.01,
    "sfx": 0.005,
}
PROJECT_LOAD_OPTIONS = (
    selectinload(AnimeProject.scenes),
    selectinload(AnimeProject.audio_tracks),
    selectinload(AnimeProject.captions),
    selectinload(AnimeProject.renders),
)


def utcnow() -> datetime:
    return datetime.now(UTC)


def require_editor(actor: ActorContext) -> None:
    if not actor.roles.intersection(EDITOR_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")


def require_reviewer(actor: ActorContext) -> None:
    if not actor.roles.intersection(REVIEWER_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")


async def _validate_project_links(
    session: AsyncSession,
    *,
    organization_id: UUID,
    generation_project_id: UUID | None = None,
    rag_context_id: UUID | None = None,
    teacher_studio_draft_id: UUID | None = None,
) -> None:
    checks: tuple[tuple[Any, UUID | None, str], ...] = (
        (GenerationProject, generation_project_id, "Projeto pedagógico"),
        (RagContext, rag_context_id, "Contexto RAG"),
        (TeacherStudioDraft, teacher_studio_draft_id, "Rascunho do estúdio"),
    )
    for model, record_id, label in checks:
        if record_id is None:
            continue
        linked_id = await session.scalar(
            select(model.id).where(
                model.id == record_id,
                model.organization_id == organization_id,
            )
        )
        if linked_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{label} inválido para a organização atual",
            )


async def _validate_comic_sources(
    session: AsyncSession,
    *,
    organization_id: UUID,
    source_comic_page_id: UUID | None,
    source_comic_panel_id: UUID | None,
) -> None:
    if source_comic_page_id is None and source_comic_panel_id is None:
        return
    if source_comic_page_id is not None:
        valid_page_id = await session.scalar(
            select(ComicPage.id)
            .join(GeneratedComic, ComicPage.comic_id == GeneratedComic.id)
            .where(
                ComicPage.id == source_comic_page_id,
                GeneratedComic.organization_id == organization_id,
            )
        )
        if valid_page_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Página de HQ inválida para a organização atual",
            )
    if source_comic_panel_id is not None:
        panel_page_id = await session.scalar(
            select(ComicPanel.page_id)
            .join(ComicPage, ComicPanel.page_id == ComicPage.id)
            .join(GeneratedComic, ComicPage.comic_id == GeneratedComic.id)
            .where(
                ComicPanel.id == source_comic_panel_id,
                GeneratedComic.organization_id == organization_id,
            )
        )
        if panel_page_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Quadro de HQ inválido para a organização atual",
            )
        if source_comic_page_id is not None and panel_page_id != source_comic_page_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="O quadro selecionado não pertence à página de HQ informada",
            )


async def get_project(
    session: AsyncSession,
    *,
    organization_id: UUID,
    project_id: UUID,
    for_update: bool = False,
) -> AnimeProject:
    statement = (
        select(AnimeProject)
        .where(
            AnimeProject.id == project_id,
            AnimeProject.organization_id == organization_id,
        )
        .options(*PROJECT_LOAD_OPTIONS)
    )
    if for_update:
        statement = statement.with_for_update()
    project = await session.scalar(statement)
    if project is None:
        raise HTTPException(status_code=404, detail="Produção de anime não encontrada")
    return project


async def list_projects(
    session: AsyncSession, *, organization_id: UUID, include_archived: bool = False
) -> list[AnimeProject]:
    statement = select(AnimeProject).where(AnimeProject.organization_id == organization_id)
    if not include_archived:
        statement = statement.where(AnimeProject.status != "archived")
    return list((await session.scalars(statement.order_by(AnimeProject.updated_at.desc()))).all())


async def _validate_asset_file(
    session: AsyncSession,
    *,
    organization_id: UUID,
    asset_file_id: UUID | None,
    expected_prefix: str,
) -> InstitutionalAssetFile | None:
    if asset_file_id is None:
        return None
    file = await session.scalar(
        select(InstitutionalAssetFile)
        .join(InstitutionalAssetFile.asset)
        .where(
            InstitutionalAssetFile.id == asset_file_id,
            InstitutionalAssetFile.asset.has(organization_id=organization_id),
        )
    )
    if file is None:
        raise HTTPException(status_code=422, detail="Arquivo institucional inválido")
    if not file.mime_type.lower().startswith(expected_prefix):
        label = "visual" if expected_prefix in {"image/", "video/"} else "áudio"
        raise HTTPException(status_code=422, detail=f"O arquivo selecionado não é {label}")
    return file


async def _validate_visual_file(
    session: AsyncSession, *, organization_id: UUID, asset_file_id: UUID | None
) -> InstitutionalAssetFile | None:
    if asset_file_id is None:
        return None
    file = await session.scalar(
        select(InstitutionalAssetFile)
        .where(InstitutionalAssetFile.id == asset_file_id)
        .options(selectinload(InstitutionalAssetFile.asset))
    )
    if file is None or file.asset.organization_id != organization_id:
        raise HTTPException(status_code=422, detail="Arquivo visual institucional inválido")
    if not file.mime_type.lower().startswith(("image/", "video/")):
        raise HTTPException(status_code=422, detail="A cena exige uma imagem ou um vídeo")
    return file


async def create_project(
    session: AsyncSession, *, actor: ActorContext, data: AnimeProjectCreate
) -> AnimeProject:
    require_editor(actor)
    await _validate_project_links(
        session,
        organization_id=actor.organization_id,
        generation_project_id=data.generation_project_id,
        rag_context_id=data.rag_context_id,
        teacher_studio_draft_id=data.teacher_studio_draft_id,
    )
    project = AnimeProject(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **data.model_dump(),
    )
    session.add(project)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.project.created",
        entity_type="anime_project",
        entity_id=project.id,
        details={"title": project.title, "style_preset_code": project.style_preset_code},
    )
    await session.commit()
    return await get_project(session, organization_id=actor.organization_id, project_id=project.id)


async def update_project(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeProjectUpdate,
) -> AnimeProject:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    changes = data.model_dump(exclude_unset=True)
    await _validate_project_links(
        session,
        organization_id=actor.organization_id,
        generation_project_id=changes.get("generation_project_id"),
        rag_context_id=changes.get("rag_context_id"),
    )
    if "status" in changes and changes["status"] == "approved":
        require_reviewer(actor)
        project.approved_by_user_id = actor.user_id
        project.approved_at = utcnow()
    elif changes:
        project.approved_by_user_id = None
        project.approved_at = None
    for key, value in changes.items():
        setattr(project, key, value)
    if changes:
        project.revision += 1
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.project.updated",
        entity_type="anime_project",
        entity_id=project.id,
        details={"fields": sorted(changes)},
    )
    await session.commit()
    return await get_project(session, organization_id=actor.organization_id, project_id=project.id)


async def archive_project(
    session: AsyncSession, *, actor: ActorContext, project_id: UUID
) -> AnimeProject:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    project.status = "archived"
    project.revision += 1
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.project.archived",
        entity_type="anime_project",
        entity_id=project.id,
    )
    await session.commit()
    return project


async def create_scene(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeSceneCreate,
) -> AnimeScene:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    await _validate_visual_file(
        session,
        organization_id=actor.organization_id,
        asset_file_id=data.visual_asset_file_id,
    )
    await _validate_comic_sources(
        session,
        organization_id=actor.organization_id,
        source_comic_page_id=data.source_comic_page_id,
        source_comic_panel_id=data.source_comic_panel_id,
    )
    scene = AnimeScene(
        organization_id=actor.organization_id,
        project_id=project.id,
        created_by_user_id=actor.user_id,
        **data.model_dump(),
    )
    project.revision += 1
    project.status = "draft"
    session.add(scene)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Já existe uma cena nessa posição") from exc
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.scene.created",
        entity_type="anime_scene",
        entity_id=scene.id,
        details={"project_id": str(project.id), "position": scene.position},
    )
    await session.commit()
    await session.refresh(scene)
    return scene


def storyboard_scene_inputs(
    storyboard: dict[str, Any],
    *,
    start_position: int = 1,
    excluded_panel_ids: set[UUID] | None = None,
) -> tuple[list[AnimeSceneCreate], int]:
    """Translate the canonical HQ storyboard into canonical Anime scenes."""
    excluded = excluded_panel_ids or set()
    scenes: list[AnimeSceneCreate] = []
    skipped = 0
    continuity_keys = (
        "page_number",
        "panel_number",
        "emotion",
        "pacing",
        "plot_function",
        "previous_panel_summary",
        "next_panel_hook",
        "initial_state",
        "final_state",
        "alt_text",
        "audio_description",
    )
    for source in storyboard.get("scenes", []):
        panel_id = UUID(str(source["panel_id"]))
        if panel_id in excluded:
            skipped += 1
            continue
        summary = str(source.get("scene_summary") or "Cena importada da HQ").strip()
        dialogue = "\n".join(
            f"{item.get('speaker') or 'Narrador'}: {item.get('text') or ''}"
            for item in source.get("dialogue", [])
            if item.get("text")
        )
        continuity = {key: source.get(key) for key in continuity_keys}
        continuity["source_comic_id"] = storyboard.get("comic_id")
        scenes.append(
            AnimeSceneCreate(
                position=start_position + len(scenes),
                title=f"Cena {source.get('sequence_number') or len(scenes) + 1}: {summary}"[:180],
                duration_ms=int(source.get("estimated_duration_seconds") or 5) * 1000,
                source_comic_page_id=UUID(str(source["page_id"])),
                source_comic_panel_id=panel_id,
                screenplay_text=summary if not dialogue else f"{summary}\n\n{dialogue}",
                visual_prompt=str(source.get("action") or summary),
                camera_settings={
                    "shot_type": source.get("shot_type") or "medium",
                    "movement": source.get("camera_direction") or "static",
                },
                transition_settings={"type": source.get("transition") or "cut"},
                continuity_data=continuity,
                pedagogical_metadata={
                    key: source.get(key)
                    for key in (
                        "narrative_goal",
                        "pedagogical_goal",
                        "ct_pillar_codes",
                    )
                },
            )
        )
    return scenes, skipped


async def import_comic_storyboard(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeStoryboardImport,
) -> dict[str, Any]:
    require_editor(actor)
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    comic = await load_comic(
        session,
        organization_id=actor.organization_id,
        comic_id=data.comic_id,
    )
    if comic is None:
        raise HTTPException(status_code=404, detail="HQ nao encontrada")
    existing_panel_ids = {
        scene.source_comic_panel_id
        for scene in project.scenes
        if scene.source_comic_panel_id is not None
    }
    inputs, skipped = storyboard_scene_inputs(
        build_storyboard(comic),
        start_position=max((scene.position for scene in project.scenes), default=0) + 1,
        excluded_panel_ids=existing_panel_ids,
    )
    created = [
        AnimeScene(
            organization_id=actor.organization_id,
            project_id=project.id,
            created_by_user_id=actor.user_id,
            **scene.model_dump(),
        )
        for scene in inputs
    ]
    session.add_all(created)
    if created:
        project.revision += 1
        project.status = "draft"
        if project.generation_project_id is None:
            project.generation_project_id = comic.generation_project_id
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.storyboard.imported",
        entity_type="anime_project",
        entity_id=project.id,
        details={
            "comic_id": str(comic.id),
            "imported_count": len(created),
            "skipped_count": skipped,
        },
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Conflito na timeline do storyboard") from exc
    return {
        "source_comic_id": comic.id,
        "imported_count": len(created),
        "skipped_count": skipped,
        "total_duration_ms": sum(scene.duration_ms for scene in created),
        "scenes": created,
    }


async def _get_scene(session: AsyncSession, *, project: AnimeProject, scene_id: UUID) -> AnimeScene:
    scene = await session.scalar(
        select(AnimeScene).where(
            AnimeScene.id == scene_id,
            AnimeScene.project_id == project.id,
            AnimeScene.organization_id == project.organization_id,
        )
    )
    if scene is None:
        raise HTTPException(status_code=404, detail="Cena não encontrada")
    return scene


async def update_scene(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    scene_id: UUID,
    data: AnimeSceneUpdate,
) -> AnimeScene:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    scene = await _get_scene(session, project=project, scene_id=scene_id)
    changes = data.model_dump(exclude_unset=True)
    if "visual_asset_file_id" in changes:
        await _validate_visual_file(
            session,
            organization_id=actor.organization_id,
            asset_file_id=changes["visual_asset_file_id"],
        )
    await _validate_comic_sources(
        session,
        organization_id=actor.organization_id,
        source_comic_page_id=changes.get("source_comic_page_id", scene.source_comic_page_id),
        source_comic_panel_id=changes.get("source_comic_panel_id", scene.source_comic_panel_id),
    )
    if changes.get("status") == "approved":
        require_reviewer(actor)
        scene.approved_by_user_id = actor.user_id
        scene.approved_at = utcnow()
    elif changes:
        scene.approved_by_user_id = None
        scene.approved_at = None
    for key, value in changes.items():
        setattr(scene, key, value)
    if changes:
        scene.revision += 1
        project.revision += 1
        project.status = "draft"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.scene.updated",
        entity_type="anime_scene",
        entity_id=scene.id,
        details={"project_id": str(project.id), "fields": sorted(changes)},
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Já existe uma cena nessa posição") from exc
    await session.refresh(scene)
    return scene


async def reorder_timeline(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeTimelineReorder,
) -> AnimeProject:
    require_editor(actor)
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    scenes_by_id = {scene.id: scene for scene in project.scenes}
    if set(data.scene_ids) != set(scenes_by_id):
        raise HTTPException(
            status_code=422,
            detail="A reordenacao deve conter todas as cenas da timeline uma unica vez",
        )
    for temporary_position, scene_id in enumerate(data.scene_ids, start=1):
        scenes_by_id[scene_id].position = -temporary_position
    await session.flush()
    for position, scene_id in enumerate(data.scene_ids, start=1):
        scenes_by_id[scene_id].position = position
    project.revision += 1
    project.status = "draft"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.timeline.reordered",
        entity_type="anime_project",
        entity_id=project.id,
        details={"scene_ids": [str(scene_id) for scene_id in data.scene_ids]},
    )
    await session.commit()
    return await get_project(session, organization_id=actor.organization_id, project_id=project.id)


async def split_scene(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    scene_id: UUID,
    data: AnimeSceneSplit,
) -> tuple[AnimeScene, AnimeScene]:
    require_editor(actor)
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    scene = await _get_scene(session, project=project, scene_id=scene_id)
    second_duration = scene.duration_ms - data.split_at_ms
    if second_duration < 500:
        raise HTTPException(status_code=422, detail="Cada parte da cena deve ter ao menos 500 ms")
    later_scenes = sorted(
        (item for item in project.scenes if item.position > scene.position),
        key=lambda item: item.position,
        reverse=True,
    )
    for later in later_scenes:
        later.position += 1
        await session.flush()
    scene.duration_ms = data.split_at_ms
    scene.revision += 1
    second = AnimeScene(
        organization_id=actor.organization_id,
        project_id=project.id,
        position=scene.position + 1,
        title=data.second_title or f"{scene.title} - parte 2",
        duration_ms=second_duration,
        visual_asset_file_id=scene.visual_asset_file_id,
        source_comic_page_id=scene.source_comic_page_id,
        source_comic_panel_id=scene.source_comic_panel_id,
        screenplay_text=scene.screenplay_text,
        visual_prompt=scene.visual_prompt,
        negative_prompt=scene.negative_prompt,
        camera_settings=dict(scene.camera_settings),
        transition_settings=dict(scene.transition_settings),
        continuity_data={**dict(scene.continuity_data), "split_from_scene_id": str(scene.id)},
        pedagogical_metadata=dict(scene.pedagogical_metadata),
        created_by_user_id=actor.user_id,
    )
    session.add(second)
    project.revision += 1
    project.status = "draft"
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.scene.split",
        entity_type="anime_scene",
        entity_id=scene.id,
        details={
            "project_id": str(project.id),
            "second_scene_id": str(second.id),
            "split_at_ms": data.split_at_ms,
        },
    )
    await session.commit()
    await session.refresh(scene)
    await session.refresh(second)
    return scene, second


async def delete_scene(
    session: AsyncSession, *, actor: ActorContext, project_id: UUID, scene_id: UUID
) -> None:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    scene = await _get_scene(session, project=project, scene_id=scene_id)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.scene.deleted",
        entity_type="anime_scene",
        entity_id=scene.id,
        details={"project_id": str(project.id), "position": scene.position},
    )
    project.revision += 1
    project.status = "draft"
    await session.delete(scene)
    await session.commit()


def estimate_media_generation_cost(kind: str, duration_ms: int | None) -> float:
    units = 1.0 if kind == "image" else max((duration_ms or 5000) / 1000, 1)
    return round(MEDIA_GENERATION_RATES[kind] * units, 4)


def media_generation_read(job: BackgroundJob) -> dict[str, Any]:
    snapshot = dict(job.input_snapshot or {})
    result = dict(job.result_reference or {})
    review = dict(result.get("human_review") or {})
    return {
        "id": job.id,
        "project_id": UUID(str(snapshot["project_id"])),
        "scene_id": UUID(str(snapshot["scene_id"])) if snapshot.get("scene_id") else None,
        "kind": snapshot["kind"],
        "status": job.status,
        "progress_percent": job.progress_percent,
        "current_step": job.current_step,
        "estimated_cost": float(snapshot.get("estimated_cost") or 0),
        "review_required": bool(snapshot.get("review_required", True)),
        "review_decision": str(review.get("decision") or "pending"),
        "output_asset_id": result.get("output_asset_id"),
        "output_asset_file_id": result.get("output_asset_file_id"),
        "provider": str(result.get("provider") or ""),
        "error_message": job.error_message,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


async def request_media_generation(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeMediaGenerationCreate,
) -> dict[str, Any]:
    require_editor(actor)
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    scene = (
        await _get_scene(session, project=project, scene_id=data.scene_id)
        if data.scene_id
        else None
    )
    if data.kind in {"image", "animation", "voice", "lip_sync"} and scene is None:
        raise HTTPException(status_code=422, detail="Selecione uma cena para este tipo de midia")
    duration_ms = data.duration_ms or (scene.duration_ms if scene else 5000)
    prompt = data.prompt.strip()
    if not prompt and scene is not None:
        prompt = scene.visual_prompt or scene.screenplay_text
    if not prompt:
        prompt = project.synopsis or project.title
    estimated_cost = estimate_media_generation_cost(data.kind, duration_ms)
    step_labels = {
        "image": [
            "Preparando referencias",
            "Gerando imagem",
            "Validando seguranca",
            "Aguardando revisao",
        ],
        "animation": [
            "Preparando quadro",
            "Gerando movimento",
            "Validando continuidade",
            "Aguardando revisao",
        ],
        "voice": ["Preparando roteiro", "Gerando voz", "Validando pronuncia", "Aguardando revisao"],
        "lip_sync": [
            "Analisando fonemas",
            "Sincronizando labios",
            "Validando tempo",
            "Aguardando revisao",
        ],
        "music": [
            "Preparando direcao musical",
            "Gerando trilha",
            "Normalizando audio",
            "Aguardando revisao",
        ],
        "sfx": ["Preparando efeito", "Gerando audio", "Normalizando audio", "Aguardando revisao"],
    }
    snapshot = {
        "project_id": str(project.id),
        "scene_id": str(scene.id) if scene else None,
        "kind": data.kind,
        "prompt": prompt,
        "duration_ms": duration_ms,
        "voice_name": data.voice_name,
        "settings": data.settings,
        "estimated_cost": estimated_cost,
        "review_required": True,
        "steps": step_labels[data.kind],
    }
    try:
        job, created = await create_job(
            session,
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            job_type="media_generation",
            module_name="anime_studio",
            entity_type="anime_project",
            entity_id=project.id,
            priority=65,
            total_steps=len(step_labels[data.kind]),
            max_retries=2,
            idempotency_key=data.idempotency_key,
            input_snapshot=snapshot,
            estimated_cost=estimated_cost,
        )
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    if created:
        await mark_queued(session, job)
        await append_domain_audit(
            session,
            actor=actor,
            module_name="anime_studio",
            action="anime.media_generation.queued",
            entity_type="background_job",
            entity_id=job.id,
            details={
                "project_id": str(project.id),
                "scene_id": snapshot["scene_id"],
                "kind": data.kind,
                "estimated_cost": estimated_cost,
            },
        )
    await session.commit()
    return media_generation_read(job)


async def list_media_generations(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
) -> list[dict[str, Any]]:
    require_editor(actor)
    await get_project(session, organization_id=actor.organization_id, project_id=project_id)
    jobs = list(
        (
            await session.scalars(
                select(BackgroundJob)
                .where(
                    BackgroundJob.organization_id == actor.organization_id,
                    BackgroundJob.module_name == "anime_studio",
                    BackgroundJob.entity_type == "anime_project",
                    BackgroundJob.entity_id == project_id,
                    BackgroundJob.job_type == "media_generation",
                )
                .order_by(BackgroundJob.created_at.desc())
            )
        ).all()
    )
    return [media_generation_read(job) for job in jobs]


async def review_media_generation(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    job_id: UUID,
    data: AnimeMediaGenerationReview,
) -> dict[str, Any]:
    require_reviewer(actor)
    await get_project(session, organization_id=actor.organization_id, project_id=project_id)
    job = await session.scalar(
        select(BackgroundJob)
        .where(
            BackgroundJob.id == job_id,
            BackgroundJob.organization_id == actor.organization_id,
            BackgroundJob.module_name == "anime_studio",
            BackgroundJob.entity_id == project_id,
            BackgroundJob.job_type == "media_generation",
        )
        .with_for_update()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Geracao de midia nao encontrada")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail="A geracao ainda nao foi concluida")
    if (job.result_reference or {}).get("human_review"):
        raise HTTPException(status_code=409, detail="Esta geracao ja foi revisada")
    result = dict(job.result_reference or {})
    output_file_id = result.get("output_asset_file_id")
    if not output_file_id:
        raise HTTPException(status_code=409, detail="A geracao nao produziu um artefato")
    asset_file = await session.scalar(
        select(InstitutionalAssetFile)
        .join(InstitutionalAsset)
        .where(
            InstitutionalAssetFile.id == UUID(str(output_file_id)),
            InstitutionalAsset.organization_id == actor.organization_id,
        )
        .options(selectinload(InstitutionalAssetFile.asset))
    )
    if asset_file is None:
        raise HTTPException(status_code=404, detail="Artefato gerado nao encontrado")
    snapshot = dict(job.input_snapshot or {})
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    if data.decision == "approved":
        asset_file.asset.status = InstitutionalAssetStatus.APPROVED
        asset_file.asset.approved_by_user_id = actor.user_id
        kind = str(snapshot["kind"])
        scene_id = snapshot.get("scene_id")
        if kind in {"image", "animation", "lip_sync"} and scene_id:
            scene = await _get_scene(session, project=project, scene_id=UUID(str(scene_id)))
            scene.visual_asset_file_id = asset_file.id
            scene.revision += 1
        elif kind in {"voice", "music", "sfx"}:
            existing_track = await session.scalar(
                select(AnimeAudioTrack.id).where(
                    AnimeAudioTrack.project_id == project.id,
                    AnimeAudioTrack.asset_file_id == asset_file.id,
                )
            )
            if existing_track is None:
                session.add(
                    AnimeAudioTrack(
                        organization_id=actor.organization_id,
                        project_id=project.id,
                        scene_id=UUID(str(scene_id)) if scene_id else None,
                        track_kind={"voice": "dialogue", "music": "music", "sfx": "sfx"}[kind],
                        label=f"Geracao {kind} {str(job.id)[:8]}",
                        language=project.language,
                        asset_file_id=asset_file.id,
                        transcript=str(snapshot.get("prompt") or "") if kind == "voice" else "",
                        speaker=str(snapshot.get("voice_name") or ""),
                        start_ms=0,
                        duration_ms=int(snapshot.get("duration_ms") or 5000),
                        created_by_user_id=actor.user_id,
                    )
                )
        project.revision += 1
        project.status = "draft"
    else:
        asset_file.asset.status = InstitutionalAssetStatus.REJECTED
    job.result_reference = {
        **result,
        "human_review": {
            "decision": data.decision,
            "notes": data.notes,
            "reviewed_by_user_id": str(actor.user_id),
            "reviewed_at": utcnow().isoformat(),
        },
    }
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action=f"anime.media_generation.{data.decision}",
        entity_type="background_job",
        entity_id=job.id,
        details={"project_id": str(project_id), "notes": data.notes},
    )
    await session.commit()
    return media_generation_read(job)


async def create_audio_track(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeAudioTrackCreate,
) -> AnimeAudioTrack:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    if data.scene_id:
        await _get_scene(session, project=project, scene_id=data.scene_id)
    await _validate_asset_file(
        session,
        organization_id=actor.organization_id,
        asset_file_id=data.asset_file_id,
        expected_prefix="audio/",
    )
    track = AnimeAudioTrack(
        organization_id=actor.organization_id,
        project_id=project.id,
        created_by_user_id=actor.user_id,
        **data.model_dump(),
    )
    project.revision += 1
    project.status = "draft"
    session.add(track)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.audio.created",
        entity_type="anime_audio_track",
        entity_id=track.id,
        details={"project_id": str(project.id), "kind": track.track_kind},
    )
    await session.commit()
    await session.refresh(track)
    return track


async def _get_audio_track(
    session: AsyncSession, *, project: AnimeProject, track_id: UUID
) -> AnimeAudioTrack:
    track = await session.scalar(
        select(AnimeAudioTrack).where(
            AnimeAudioTrack.id == track_id,
            AnimeAudioTrack.project_id == project.id,
            AnimeAudioTrack.organization_id == project.organization_id,
        )
    )
    if track is None:
        raise HTTPException(status_code=404, detail="Faixa de áudio não encontrada")
    return track


async def update_audio_track(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    track_id: UUID,
    data: AnimeAudioTrackUpdate,
) -> AnimeAudioTrack:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    track = await _get_audio_track(session, project=project, track_id=track_id)
    changes = data.model_dump(exclude_unset=True)
    if "scene_id" in changes and changes["scene_id"]:
        await _get_scene(session, project=project, scene_id=changes["scene_id"])
    if "asset_file_id" in changes:
        await _validate_asset_file(
            session,
            organization_id=actor.organization_id,
            asset_file_id=changes["asset_file_id"],
            expected_prefix="audio/",
        )
    for key, value in changes.items():
        setattr(track, key, value)
    if changes:
        project.revision += 1
        project.status = "draft"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.audio.updated",
        entity_type="anime_audio_track",
        entity_id=track.id,
        details={"project_id": str(project.id), "fields": sorted(changes)},
    )
    await session.commit()
    await session.refresh(track)
    return track


async def delete_audio_track(
    session: AsyncSession, *, actor: ActorContext, project_id: UUID, track_id: UUID
) -> None:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    track = await _get_audio_track(session, project=project, track_id=track_id)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.audio.deleted",
        entity_type="anime_audio_track",
        entity_id=track.id,
        details={"project_id": str(project.id)},
    )
    project.revision += 1
    project.status = "draft"
    await session.delete(track)
    await session.commit()


async def create_caption(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeCaptionCreate,
) -> AnimeCaptionCue:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    if data.scene_id:
        await _get_scene(session, project=project, scene_id=data.scene_id)
    await _ensure_caption_window_available(
        session,
        project=project,
        language=data.language,
        start_ms=data.start_ms,
        end_ms=data.end_ms,
    )
    cue = AnimeCaptionCue(
        organization_id=actor.organization_id,
        project_id=project.id,
        created_by_user_id=actor.user_id,
        **data.model_dump(),
    )
    project.revision += 1
    project.status = "draft"
    session.add(cue)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Ordem de legenda já utilizada") from exc
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.caption.created",
        entity_type="anime_caption_cue",
        entity_id=cue.id,
        details={"project_id": str(project.id), "cue_order": cue.cue_order},
    )
    await session.commit()
    await session.refresh(cue)
    return cue


async def _get_caption(
    session: AsyncSession, *, project: AnimeProject, cue_id: UUID
) -> AnimeCaptionCue:
    cue = await session.scalar(
        select(AnimeCaptionCue).where(
            AnimeCaptionCue.id == cue_id,
            AnimeCaptionCue.project_id == project.id,
            AnimeCaptionCue.organization_id == project.organization_id,
        )
    )
    if cue is None:
        raise HTTPException(status_code=404, detail="Legenda não encontrada")
    return cue


async def _ensure_caption_window_available(
    session: AsyncSession,
    *,
    project: AnimeProject,
    language: str,
    start_ms: int,
    end_ms: int,
    exclude_cue_id: UUID | None = None,
) -> None:
    query = select(AnimeCaptionCue.id).where(
        AnimeCaptionCue.project_id == project.id,
        AnimeCaptionCue.organization_id == project.organization_id,
        AnimeCaptionCue.language == language,
        AnimeCaptionCue.start_ms < end_ms,
        AnimeCaptionCue.end_ms > start_ms,
    )
    if exclude_cue_id is not None:
        query = query.where(AnimeCaptionCue.id != exclude_cue_id)
    if await session.scalar(query.limit(1)) is not None:
        raise HTTPException(
            status_code=409,
            detail="Intervalo de legenda sobrepõe outra legenda do mesmo idioma",
        )


async def update_caption(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    cue_id: UUID,
    data: AnimeCaptionUpdate,
) -> AnimeCaptionCue:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    cue = await _get_caption(session, project=project, cue_id=cue_id)
    changes = data.model_dump(exclude_unset=True)
    start_ms = changes.get("start_ms", cue.start_ms)
    end_ms = changes.get("end_ms", cue.end_ms)
    if end_ms <= start_ms:
        raise HTTPException(status_code=422, detail="Fim da legenda deve ser posterior ao início")
    await _ensure_caption_window_available(
        session,
        project=project,
        language=changes.get("language", cue.language),
        start_ms=start_ms,
        end_ms=end_ms,
        exclude_cue_id=cue.id,
    )
    if "scene_id" in changes and changes["scene_id"]:
        await _get_scene(session, project=project, scene_id=changes["scene_id"])
    for key, value in changes.items():
        setattr(cue, key, value)
    if changes:
        project.revision += 1
        project.status = "draft"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.caption.updated",
        entity_type="anime_caption_cue",
        entity_id=cue.id,
        details={"project_id": str(project.id), "fields": sorted(changes)},
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Ordem de legenda já utilizada") from exc
    await session.refresh(cue)
    return cue


async def delete_caption(
    session: AsyncSession, *, actor: ActorContext, project_id: UUID, cue_id: UUID
) -> None:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    cue = await _get_caption(session, project=project, cue_id=cue_id)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.caption.deleted",
        entity_type="anime_caption_cue",
        entity_id=cue.id,
        details={"project_id": str(project.id)},
    )
    project.revision += 1
    project.status = "draft"
    await session.delete(cue)
    await session.commit()


def render_snapshot(project: AnimeProject, data: AnimeRenderCreate) -> dict[str, Any]:
    return {
        "project": {
            "id": str(project.id),
            "revision": project.revision,
            "title": project.title,
            "width": project.width,
            "height": project.height,
            "fps": project.fps,
            "language": project.language,
        },
        "scenes": [
            {
                "id": str(scene.id),
                "position": scene.position,
                "title": scene.title,
                "duration_ms": scene.duration_ms,
                "visual_asset_file_id": (
                    str(scene.visual_asset_file_id) if scene.visual_asset_file_id else None
                ),
                "transition_settings": scene.transition_settings,
            }
            for scene in sorted(project.scenes, key=lambda item: item.position)
        ],
        "audio_tracks": [
            {
                "id": str(track.id),
                "kind": track.track_kind,
                "asset_file_id": str(track.asset_file_id) if track.asset_file_id else None,
                "start_ms": track.start_ms,
                "duration_ms": track.duration_ms,
                "trim_start_ms": track.trim_start_ms,
                "volume": track.volume,
                "fade_in_ms": track.fade_in_ms,
                "fade_out_ms": track.fade_out_ms,
                "is_muted": track.is_muted,
            }
            for track in project.audio_tracks
        ],
        "captions": [
            {
                "id": str(cue.id),
                "language": cue.language,
                "cue_order": cue.cue_order,
                "start_ms": cue.start_ms,
                "end_ms": cue.end_ms,
                "text": cue.text,
                "speaker": cue.speaker,
                "kind": cue.cue_kind,
            }
            for cue in project.captions
        ],
        "settings": data.model_dump(exclude={"idempotency_key"}),
    }


async def request_render(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimeRenderCreate,
) -> AnimeRender:
    require_editor(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    if not project.scenes:
        raise HTTPException(
            status_code=422, detail="Adicione ao menos uma cena antes de renderizar"
        )
    missing_visual = [scene.position for scene in project.scenes if not scene.visual_asset_file_id]
    if missing_visual:
        raise HTTPException(
            status_code=422,
            detail=f"Cenas sem imagem ou vídeo: {', '.join(map(str, missing_visual))}",
        )
    snapshot = render_snapshot(project, data)
    checksum = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    key = data.idempotency_key or f"anime-render:{project.id}:{project.revision}:{checksum[:24]}"
    existing_job = await session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.organization_id == actor.organization_id,
            BackgroundJob.idempotency_key == key,
        )
    )
    if existing_job:
        existing_render = await session.scalar(
            select(AnimeRender).where(
                AnimeRender.organization_id == actor.organization_id,
                AnimeRender.background_job_id == existing_job.id,
            )
        )
        if existing_render:
            return existing_render

    next_revision = (
        int(
            await session.scalar(
                select(func.coalesce(func.max(AnimeRender.revision), 0)).where(
                    AnimeRender.project_id == project.id
                )
            )
            or 0
        )
        + 1
    )
    render = AnimeRender(
        organization_id=actor.organization_id,
        project_id=project.id,
        revision=next_revision,
        status="queued",
        render_settings=snapshot["settings"],
        source_snapshot=snapshot,
        manifest_checksum=checksum,
        requested_by_user_id=actor.user_id,
    )
    session.add(render)
    await session.flush()
    try:
        job, created = await create_job(
            session,
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            job_type="anime_render",
            module_name="anime_studio",
            entity_type="anime_render",
            entity_id=render.id,
            priority=60,
            total_steps=6,
            max_retries=2,
            idempotency_key=key,
            input_snapshot={
                "render_id": str(render.id),
                "project_id": str(project.id),
                "manifest_checksum": checksum,
            },
        )
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not created:
        await session.delete(render)
        existing_render = await session.scalar(
            select(AnimeRender).where(AnimeRender.background_job_id == job.id)
        )
        if existing_render:
            return existing_render
        raise HTTPException(status_code=409, detail="Renderização idempotente inconsistente")
    render.background_job_id = job.id
    project.status = "rendering"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.render.requested",
        entity_type="anime_render",
        entity_id=render.id,
        details={"project_id": str(project.id), "revision": render.revision, "job_id": str(job.id)},
    )
    await session.commit()
    await mark_queued(session, job)
    await session.commit()
    await session.refresh(render)
    return render


async def review_render(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    render_id: UUID,
    data: AnimeRenderReview,
) -> AnimeRender:
    require_reviewer(actor)
    project = await get_project(
        session, organization_id=actor.organization_id, project_id=project_id, for_update=True
    )
    render = await session.scalar(
        select(AnimeRender).where(
            AnimeRender.id == render_id,
            AnimeRender.project_id == project.id,
            AnimeRender.organization_id == actor.organization_id,
        )
    )
    if render is None:
        raise HTTPException(status_code=404, detail="Renderização não encontrada")
    if render.status not in {"in_review", "approved", "rejected"}:
        raise HTTPException(
            status_code=409, detail="A renderização ainda não está pronta para revisão"
        )
    render.review_decision = data.decision
    render.review_notes = data.notes
    render.reviewed_by_user_id = actor.user_id
    render.reviewed_at = utcnow()
    render.status = data.decision
    project.status = "ready" if data.decision == "approved" else "rejected"
    if render.output_asset_id is not None:
        output_asset = await session.scalar(
            select(InstitutionalAsset).where(
                InstitutionalAsset.id == render.output_asset_id,
                InstitutionalAsset.organization_id == actor.organization_id,
            )
        )
        if output_asset is not None:
            output_asset.status = (
                InstitutionalAssetStatus.APPROVED
                if data.decision == "approved"
                else InstitutionalAssetStatus.REJECTED
            )
            output_asset.approved_by_user_id = (
                actor.user_id if data.decision == "approved" else None
            )
            session.add(
                InstitutionalAssetAudit(
                    organization_id=actor.organization_id,
                    asset_id=output_asset.id,
                    actor_user_id=actor.user_id,
                    action=f"anime_render_{data.decision}",
                    details={"anime_render_id": str(render.id), "notes": data.notes},
                )
            )
    if data.decision == "approved":
        project.approved_by_user_id = actor.user_id
        project.production_notes = {
            **project.production_notes,
            "active_render_id": str(render.id),
            "active_render_revision": render.revision,
        }
        project.approved_at = utcnow()
    else:
        project.approved_by_user_id = None
        project.approved_at = None
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action=f"anime.render.{data.decision}",
        entity_type="anime_render",
        entity_id=render.id,
        details={"project_id": str(project.id), "revision": render.revision, "notes": data.notes},
    )
    await session.commit()
    await session.refresh(render)
    return render


async def restore_render_version(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    render_id: UUID,
) -> AnimeProject:
    require_reviewer(actor)
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    render = await session.scalar(
        select(AnimeRender).where(
            AnimeRender.id == render_id,
            AnimeRender.project_id == project.id,
            AnimeRender.organization_id == actor.organization_id,
        )
    )
    if render is None:
        raise HTTPException(status_code=404, detail="Renderização não encontrada")
    if render.status != "approved" or render.output_asset_file_id is None:
        raise HTTPException(
            status_code=409,
            detail="Somente versões aprovadas e concluídas podem ser restauradas",
        )
    project.production_notes = {
        **project.production_notes,
        "active_render_id": str(render.id),
        "active_render_revision": render.revision,
        "restored_at": utcnow().isoformat(),
    }
    project.status = "ready"
    project.revision += 1
    project.approved_by_user_id = actor.user_id
    project.approved_at = utcnow()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.render.version_restored",
        entity_type="anime_render",
        entity_id=render.id,
        details={
            "project_id": str(project.id),
            "render_revision": render.revision,
        },
    )
    await session.commit()
    return await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )


def _publication_from_notes(project: AnimeProject) -> AnimePublicationRead:
    publication = project.production_notes.get("publication")
    if not isinstance(publication, dict):
        raise HTTPException(status_code=404, detail="Produção audiovisual ainda não publicada")
    try:
        return AnimePublicationRead.model_validate(publication)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Manifesto de publicação inválido") from exc


async def publish_project(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
    data: AnimePublicationCreate,
) -> AnimePublicationRead:
    require_reviewer(actor)
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        for_update=True,
    )
    active_render_id = project.production_notes.get("active_render_id")
    try:
        active_render_uuid = UUID(str(active_render_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail="Aprove uma versão antes de publicar") from exc
    render = await session.scalar(
        select(AnimeRender).where(
            AnimeRender.id == active_render_uuid,
            AnimeRender.project_id == project.id,
            AnimeRender.organization_id == actor.organization_id,
        )
    )
    if render is None or render.status != "approved" or render.output_asset_file_id is None:
        raise HTTPException(
            status_code=409,
            detail="Somente a versão ativa, aprovada e concluída pode ser publicada",
        )

    classroom_ids = list(dict.fromkeys(data.classroom_ids))
    classrooms = list(
        (
            await session.scalars(
                select(Classroom).where(
                    Classroom.id.in_(classroom_ids),
                    Classroom.organization_id == actor.organization_id,
                    Classroom.is_active.is_(True),
                )
            )
        ).all()
    )
    if len(classrooms) != len(classroom_ids):
        raise HTTPException(
            status_code=422,
            detail="Selecione somente turmas ativas da organização",
        )

    caption_languages = sorted(
        {cue.language for cue in project.captions}
        if data.include_captions
        else set()
    )
    has_audio_description = data.include_audio_description and any(
        track.track_kind == "audio_description" and not track.is_muted
        for track in project.audio_tracks
    )
    renditions: list[AnimePublicationRendition] = []
    if render.output_asset_id is not None:
        asset_files = list(
            (
                await session.scalars(
                    select(InstitutionalAssetFile)
                    .where(
                        InstitutionalAssetFile.asset_id == render.output_asset_id,
                        InstitutionalAssetFile.mime_type == "video/mp4",
                        InstitutionalAssetFile.view_type.like("anime_render%"),
                    )
                    .order_by(InstitutionalAssetFile.height.desc())
                )
            ).all()
        )
        for asset_file in asset_files:
            is_source = asset_file.id == render.output_asset_file_id
            label = (
                "Original"
                if is_source
                else asset_file.view_type.removeprefix("anime_render_")
            )
            renditions.append(
                AnimePublicationRendition(
                    label=label,
                    asset_file_id=asset_file.id,
                    width=asset_file.width or project.width,
                    height=asset_file.height or project.height,
                    size_bytes=asset_file.size_bytes,
                    media_path=(
                        f"/anime-studio/publications/{project.id}/media"
                        if is_source
                        else (
                            f"/anime-studio/publications/{project.id}/media/{asset_file.id}"
                        )
                    ),
                )
            )
    published_at = utcnow()
    publication = AnimePublicationRead(
        project_id=project.id,
        title=project.title,
        render_id=render.id,
        render_revision=render.revision,
        asset_file_id=render.output_asset_file_id,
        classroom_ids=classroom_ids,
        published_at=published_at,
        published_by_user_id=actor.user_id,
        width=project.width,
        height=project.height,
        format=render.format,
        caption_languages=caption_languages,
        includes_transcript=data.include_transcript and bool(project.captions),
        includes_audio_description=has_audio_description,
        media_path=f"/anime-studio/publications/{project.id}/media",
        renditions=renditions,
    )
    manifest = publication.model_dump(mode="json")
    project.production_notes = {**project.production_notes, "publication": manifest}
    if render.output_asset_id is not None:
        output_asset = await session.scalar(
            select(InstitutionalAsset).where(
                InstitutionalAsset.id == render.output_asset_id,
                InstitutionalAsset.organization_id == actor.organization_id,
            )
        )
        if output_asset is not None:
            output_asset.status = InstitutionalAssetStatus.PUBLISHED
            output_asset.published_at = published_at
            output_asset.metadata_json = {
                **output_asset.metadata_json,
                "anime_publication": manifest,
            }
            session.add(
                InstitutionalAssetAudit(
                    organization_id=actor.organization_id,
                    asset_id=output_asset.id,
                    actor_user_id=actor.user_id,
                    action="anime_render_published",
                    details={
                        "anime_render_id": str(render.id),
                        "classroom_ids": [str(item) for item in classroom_ids],
                    },
                )
            )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="anime_studio",
        action="anime.project.published",
        entity_type="anime_project",
        entity_id=project.id,
        details={
            "render_id": str(render.id),
            "classroom_ids": [str(item) for item in classroom_ids],
        },
    )
    await session.commit()
    return publication


async def get_project_publication(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
) -> AnimePublicationRead:
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )
    publication = _publication_from_notes(project)
    if actor.roles.intersection(EDITOR_ROLES | REVIEWER_ROLES):
        return publication
    enrollment = await session.scalar(
        select(ClassroomEnrollment.id)
        .join(Classroom, Classroom.id == ClassroomEnrollment.classroom_id)
        .where(
            ClassroomEnrollment.user_id == actor.user_id,
            ClassroomEnrollment.classroom_id.in_(publication.classroom_ids),
            ClassroomEnrollment.role.ilike("student"),
            Classroom.organization_id == actor.organization_id,
            Classroom.is_active.is_(True),
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=403, detail="Publicação não autorizada para suas turmas")
    return publication


async def list_project_publications(
    session: AsyncSession,
    *,
    actor: ActorContext,
) -> list[AnimePublicationLibraryItem]:
    projects = list(
        (
            await session.scalars(
                select(AnimeProject)
                .where(AnimeProject.organization_id == actor.organization_id)
                .options(*PROJECT_LOAD_OPTIONS)
                .order_by(AnimeProject.updated_at.desc())
            )
        ).unique().all()
    )
    allowed_classrooms: set[UUID] | None = None
    if not actor.roles.intersection(EDITOR_ROLES | REVIEWER_ROLES):
        allowed_classrooms = set(
            (
                await session.scalars(
                    select(ClassroomEnrollment.classroom_id)
                    .join(Classroom, Classroom.id == ClassroomEnrollment.classroom_id)
                    .where(
                        ClassroomEnrollment.user_id == actor.user_id,
                        ClassroomEnrollment.role.ilike("student"),
                        Classroom.organization_id == actor.organization_id,
                        Classroom.is_active.is_(True),
                    )
                )
            ).all()
        )

    items: list[AnimePublicationLibraryItem] = []
    for project in projects:
        try:
            publication = _publication_from_notes(project)
        except HTTPException:
            continue
        if allowed_classrooms is not None and not allowed_classrooms.intersection(
            publication.classroom_ids
        ):
            continue
        active_render = next(
            (render for render in project.renders if render.id == publication.render_id),
            None,
        )
        if active_render is None or active_render.status != "approved":
            continue
        items.append(
            AnimePublicationLibraryItem(
                publication=publication,
                synopsis=project.synopsis,
                duration_ms=active_render.duration_ms
                or sum(scene.duration_ms for scene in project.scenes),
                caption_count=len(project.captions)
                if publication.caption_languages
                else 0,
            )
        )
    return items


async def get_publication_transcript(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
) -> list[AnimePublicationTranscriptCue]:
    publication = await get_project_publication(
        session,
        actor=actor,
        project_id=project_id,
    )
    if not publication.includes_transcript:
        return []
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )
    return [
        AnimePublicationTranscriptCue(
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            speaker=cue.speaker,
            text=cue.text,
            cue_kind=cue.cue_kind,
        )
        for cue in sorted(project.captions, key=lambda item: (item.start_ms, item.cue_order))
    ]


async def get_publication_caption_cues(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: UUID,
) -> list[AnimePublicationTranscriptCue]:
    publication = await get_project_publication(
        session,
        actor=actor,
        project_id=project_id,
    )
    if not publication.caption_languages:
        return []
    project = await get_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )
    return [
        AnimePublicationTranscriptCue(
            start_ms=cue.start_ms,
            end_ms=cue.end_ms,
            speaker=cue.speaker,
            text=cue.text,
            cue_kind=cue.cue_kind,
        )
        for cue in sorted(project.captions, key=lambda item: (item.start_ms, item.cue_order))
    ]


def transcript_as_webvtt(cues: list[AnimePublicationTranscriptCue]) -> str:
    def timestamp(milliseconds: int) -> str:
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, millis = divmod(remainder, 1_000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    lines = ["WEBVTT", ""]
    for index, cue in enumerate(cues, start=1):
        text = f"{cue.speaker}: {cue.text}" if cue.speaker else cue.text
        lines.extend(
            [
                str(index),
                f"{timestamp(cue.start_ms)} --> {timestamp(cue.end_ms)}",
                text,
                "",
            ]
        )
    return "\n".join(lines)
