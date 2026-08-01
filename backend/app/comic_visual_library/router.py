from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import (
    IDENTITY_FIELDS,
    SCENARIO_FIELDS,
    build_batch_plan,
    calculate_batch_progress,
    compare_snapshots,
    stable_fingerprint,
)
from app.services.comic_runtime import cancel_domain_job, enqueue_domain_job, runtime_job_for_domain, synchronize_simple_domain_job
from app.services.consolidated_audit import append_domain_audit

from .repositories import list_characters as repository_list_characters
from .repositories import list_scenarios as repository_list_scenarios
from .schemas import (
    CharacterCreate,
    CharacterRead,
    CharacterVariantCreate,
    CharacterVersionCreate,
    ConsistencyResolution,
    ConsistencyRunRequest,
    ContinuityRecordCreate,
    GenerationBatchCreate,
    LibraryCreate,
    LibraryRead,
    ScenarioCreate,
    ScenarioRead,
)

router = APIRouter(prefix="/comic-visual-library", tags=["comic-visual-library"])
SessionDep = Annotated[Any, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]
ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
EDITOR_ROLES = ADMIN_ROLES | {"TEACHER", "COORDINATOR", "PEDAGOGICAL_COORDINATOR"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    roles = {str(item).upper() for item in actor.roles}
    if not roles.intersection(allowed):
        raise HTTPException(403, "Permissao insuficiente para gerenciar a biblioteca visual.")


async def get_library(session: Any, organization_id: uuid.UUID, library_id: uuid.UUID) -> models.ComicVisualLibrary:
    item = await session.scalar(
        select(models.ComicVisualLibrary).where(
            models.ComicVisualLibrary.organization_id == organization_id,
            models.ComicVisualLibrary.id == library_id,
        )
    )
    if not item:
        raise HTTPException(404, "Biblioteca visual nao encontrada.")
    return item


async def get_character(session: Any, organization_id: uuid.UUID, character_id: uuid.UUID) -> models.ComicCharacter:
    item = await session.scalar(
        select(models.ComicCharacter).where(
            models.ComicCharacter.organization_id == organization_id,
            models.ComicCharacter.id == character_id,
        )
    )
    if not item:
        raise HTTPException(404, "Personagem nao encontrado.")
    return item


async def get_scenario(session: Any, organization_id: uuid.UUID, scenario_id: uuid.UUID) -> models.ComicScenario:
    item = await session.scalar(
        select(models.ComicScenario).where(
            models.ComicScenario.organization_id == organization_id,
            models.ComicScenario.id == scenario_id,
        )
    )
    if not item:
        raise HTTPException(404, "Cenario nao encontrado.")
    return item


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "16.3", "module": "comic-visual-library"}


@router.post("/libraries", response_model=LibraryRead, status_code=status.HTTP_201_CREATED)
async def create_library(payload: LibraryCreate, session: SessionDep, actor: ActorDep) -> LibraryRead:
    require_role(actor, EDITOR_ROLES)
    existing = await session.scalar(
        select(models.ComicVisualLibrary).where(
            models.ComicVisualLibrary.organization_id == actor.organization_id,
            models.ComicVisualLibrary.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(409, "Ja existe uma biblioteca com este codigo.")
    item = models.ComicVisualLibrary(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/libraries", response_model=list[LibraryRead])
async def list_libraries(session: SessionDep, actor: ActorDep) -> list[LibraryRead]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(
        select(models.ComicVisualLibrary)
        .where(models.ComicVisualLibrary.organization_id == actor.organization_id)
        .order_by(models.ComicVisualLibrary.name)
    )
    return list(result.scalars().all())


@router.post("/characters", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(payload: CharacterCreate, session: SessionDep, actor: ActorDep) -> CharacterRead:
    require_role(actor, EDITOR_ROLES)
    await get_library(session, actor.organization_id, payload.library_id)
    identity_fingerprint = stable_fingerprint(payload.identity_profile)
    item = models.ComicCharacter(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        identity_fingerprint=identity_fingerprint,
        **payload.model_dump(),
    )
    session.add(item)
    await session.flush()
    version = models.ComicCharacterVersion(
        organization_id=actor.organization_id,
        character_id=item.id,
        version_number=1,
        snapshot=payload.model_dump(mode="json"),
        change_summary="Versao inicial",
        identity_fingerprint=identity_fingerprint,
        created_by_user_id=actor.user_id,
    )
    session.add(version)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/characters", response_model=list[CharacterRead])
async def list_characters(session: SessionDep, actor: ActorDep, library_id: uuid.UUID | None = None) -> list[CharacterRead]:
    require_role(actor, EDITOR_ROLES)
    return await repository_list_characters(session, actor.organization_id, library_id)


@router.get("/characters/{character_id}", response_model=CharacterRead)
async def character_detail(character_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> CharacterRead:
    require_role(actor, EDITOR_ROLES)
    return await get_character(session, actor.organization_id, character_id)


@router.post("/characters/{character_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_character_version(
    character_id: uuid.UUID,
    payload: CharacterVersionCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    character = await get_character(session, actor.organization_id, character_id)
    next_version = character.current_version + 1
    fingerprint = stable_fingerprint(payload.snapshot.get("identity_profile", payload.snapshot))
    item = models.ComicCharacterVersion(
        organization_id=actor.organization_id,
        character_id=character_id,
        version_number=next_version,
        snapshot=payload.snapshot,
        change_summary=payload.change_summary,
        identity_fingerprint=fingerprint,
        created_by_user_id=actor.user_id,
    )
    character.current_version = next_version
    character.identity_fingerprint = fingerprint
    session.add(item)
    await session.commit()
    return {"id": str(item.id), "version_number": next_version, "identity_fingerprint": fingerprint}


@router.post("/characters/{character_id}/variants", status_code=status.HTTP_201_CREATED)
async def create_character_variant(
    character_id: uuid.UUID,
    payload: CharacterVariantCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    await get_character(session, actor.organization_id, character_id)
    item = models.ComicCharacterVariant(
        organization_id=actor.organization_id,
        character_id=character_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "character_id": str(character_id), "name": item.name, "status": item.status}


@router.post("/characters/{character_id}/publish")
async def publish_character(character_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> dict[str, str]:
    require_role(actor, ADMIN_ROLES)
    character = await get_character(session, actor.organization_id, character_id)
    library = await get_library(session, actor.organization_id, character.library_id)
    character.status = "IN_REVIEW" if library.scope == "INSTITUTIONAL" else "PUBLISHED"
    await session.commit()
    return {"status": character.status}


@router.post("/scenarios", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
async def create_scenario(payload: ScenarioCreate, session: SessionDep, actor: ActorDep) -> ScenarioRead:
    require_role(actor, EDITOR_ROLES)
    await get_library(session, actor.organization_id, payload.library_id)
    fingerprint = stable_fingerprint(payload.location_profile)
    item = models.ComicScenario(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        identity_fingerprint=fingerprint,
        **payload.model_dump(),
    )
    session.add(item)
    await session.flush()
    session.add(models.ComicScenarioVersion(
        organization_id=actor.organization_id,
        scenario_id=item.id,
        version_number=1,
        snapshot=payload.model_dump(mode="json"),
        change_summary="Versao inicial",
        identity_fingerprint=fingerprint,
        created_by_user_id=actor.user_id,
    ))
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/scenarios", response_model=list[ScenarioRead])
async def list_scenarios(session: SessionDep, actor: ActorDep, library_id: uuid.UUID | None = None) -> list[ScenarioRead]:
    require_role(actor, EDITOR_ROLES)
    return await repository_list_scenarios(session, actor.organization_id, library_id)


@router.post("/scenarios/{scenario_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_scenario_version(
    scenario_id: uuid.UUID,
    payload: CharacterVersionCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    scenario = await get_scenario(session, actor.organization_id, scenario_id)
    next_version = scenario.current_version + 1
    fingerprint = stable_fingerprint(payload.snapshot.get("location_profile", payload.snapshot))
    item = models.ComicScenarioVersion(
        organization_id=actor.organization_id,
        scenario_id=scenario_id,
        version_number=next_version,
        snapshot=payload.snapshot,
        change_summary=payload.change_summary,
        identity_fingerprint=fingerprint,
        created_by_user_id=actor.user_id,
    )
    scenario.current_version = next_version
    scenario.identity_fingerprint = fingerprint
    session.add(item)
    await session.commit()
    return {"id": str(item.id), "version_number": next_version, "identity_fingerprint": fingerprint}


@router.post("/continuity", status_code=status.HTTP_201_CREATED)
async def create_continuity_record(
    payload: ContinuityRecordCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    existing = await session.scalar(
        select(models.ComicContinuityRecord).where(
            models.ComicContinuityRecord.organization_id == actor.organization_id,
            models.ComicContinuityRecord.comic_project_id == payload.comic_project_id,
            models.ComicContinuityRecord.page_id == payload.page_id,
            models.ComicContinuityRecord.panel_id == payload.panel_id,
        )
    )
    if existing:
        for key, value in payload.model_dump().items():
            setattr(existing, key, value)
        item = existing
    else:
        item = models.ComicContinuityRecord(
            organization_id=actor.organization_id,
            created_by_user_id=actor.user_id,
            **payload.model_dump(),
        )
        session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "sequence_number": item.sequence_number, "updated": existing is not None}


@router.get("/projects/{project_id}/continuity")
async def list_continuity(project_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(
        select(models.ComicContinuityRecord)
        .where(
            models.ComicContinuityRecord.organization_id == actor.organization_id,
            models.ComicContinuityRecord.comic_project_id == project_id,
        )
        .order_by(models.ComicContinuityRecord.sequence_number)
    )
    return [
        {
            "id": str(item.id),
            "page_id": str(item.page_id),
            "panel_id": str(item.panel_id),
            "sequence_number": item.sequence_number,
            "location": item.location,
            "time_of_day": item.time_of_day,
            "character_states": item.character_states,
        }
        for item in result.scalars().all()
    ]


@router.post("/consistency/run", status_code=status.HTTP_201_CREATED)
async def run_consistency_check(
    payload: ConsistencyRunRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    fields = tuple(payload.fields) if payload.fields else (IDENTITY_FIELDS if payload.entity_type.upper() == "CHARACTER" else SCENARIO_FIELDS)
    findings = compare_snapshots(payload.expected_snapshot, payload.observed_snapshot, fields=fields)
    ids: list[str] = []
    for finding in findings:
        item = models.ComicConsistencyCheck(
            organization_id=actor.organization_id,
            comic_project_id=payload.comic_project_id,
            page_id=payload.page_id,
            panel_id=payload.panel_id,
            entity_type=payload.entity_type.upper(),
            entity_id=payload.entity_id,
            check_code=finding["code"],
            severity=finding["severity"],
            message=f"Divergencia de consistencia no campo {finding['field']}.",
            expected_snapshot={finding["field"]: finding["expected"]},
            observed_snapshot={finding["field"]: finding["observed"]},
        )
        session.add(item)
        await session.flush()
        ids.append(str(item.id))
    await session.commit()
    return {"consistent": not findings, "findings": findings, "finding_ids": ids}


@router.get("/projects/{project_id}/consistency")
async def list_consistency(project_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(
        select(models.ComicConsistencyCheck)
        .where(
            models.ComicConsistencyCheck.organization_id == actor.organization_id,
            models.ComicConsistencyCheck.comic_project_id == project_id,
        )
        .order_by(models.ComicConsistencyCheck.created_at.desc())
    )
    return [
        {
            "id": str(item.id),
            "check_code": item.check_code,
            "severity": item.severity,
            "status": item.status,
            "message": item.message,
            "page_id": str(item.page_id) if item.page_id else None,
            "panel_id": str(item.panel_id) if item.panel_id else None,
        }
        for item in result.scalars().all()
    ]


@router.post("/consistency/{check_id}/resolve")
async def resolve_consistency(
    check_id: uuid.UUID,
    payload: ConsistencyResolution,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, str]:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.ComicConsistencyCheck).where(
            models.ComicConsistencyCheck.organization_id == actor.organization_id,
            models.ComicConsistencyCheck.id == check_id,
        )
    )
    if not item:
        raise HTTPException(404, "Verificacao de consistencia nao encontrada.")
    item.status = payload.status
    item.resolution = {**payload.resolution, "note": payload.note}
    item.resolved_by_user_id = actor.user_id
    item.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"status": item.status}


@router.post("/generation-batches", status_code=status.HTTP_201_CREATED)
async def create_generation_batch(
    payload: GenerationBatchCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    plan = build_batch_plan([item.model_dump(mode="json") for item in payload.items], payload.default_locks)
    batch = models.ComicGenerationBatch(
        organization_id=actor.organization_id,
        comic_project_id=payload.comic_project_id,
        name=payload.name,
        selection_mode=payload.selection_mode.upper(),
        total_items=len(plan),
        lock_policy=payload.default_locks,
        generation_settings=payload.generation_settings,
        requested_by_user_id=actor.user_id,
    )
    session.add(batch)
    await session.flush()
    for item in plan:
        session.add(models.ComicGenerationBatchItem(
            organization_id=actor.organization_id,
            batch_id=batch.id,
            page_id=item["page_id"],
            panel_id=item["panel_id"],
            sequence_number=item["sequence_number"],
            status=item["status"],
            character_locks=item["character_locks"],
            scenario_locks=item["scenario_locks"],
            prompt_snapshot=item["prompt_snapshot"],
        ))
    await session.commit()
    return {"id": str(batch.id), "status": batch.status, "total_items": batch.total_items, "plan": plan}


@router.get("/generation-batches/{batch_id}")
async def generation_batch_detail(batch_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    batch = await session.scalar(
        select(models.ComicGenerationBatch).where(
            models.ComicGenerationBatch.organization_id == actor.organization_id,
            models.ComicGenerationBatch.id == batch_id,
        )
    )
    if not batch:
        raise HTTPException(404, "Lote de geracao nao encontrado.")
    result = await session.execute(
        select(models.ComicGenerationBatchItem)
        .where(
            models.ComicGenerationBatchItem.organization_id == actor.organization_id,
            models.ComicGenerationBatchItem.batch_id == batch_id,
        )
        .order_by(models.ComicGenerationBatchItem.sequence_number)
    )
    items = list(result.scalars().all())
    runtime = await runtime_job_for_domain(
        session,
        organization_id=actor.organization_id,
        module_name="comic_visual_library",
        entity_type="comic_generation_batch",
        entity_id=batch.id,
    )
    if runtime:
        synchronize_simple_domain_job(batch, runtime)
        completed_count = int((runtime.progress_percent / 100) * len(items))
        for index, item in enumerate(items):
            if runtime.status == "completed" or index < completed_count:
                item.status = "COMPLETED"
                item.finished_at = item.finished_at or datetime.now(UTC)
            elif index == completed_count and runtime.status in {"processing", "waiting_provider", "validating"}:
                item.status = "RUNNING"
                item.started_at = item.started_at or datetime.now(UTC)
            elif runtime.status == "failed" and index == min(completed_count, max(len(items) - 1, 0)):
                item.status = "FAILED"
                item.error_message = runtime.error_message or "Falha no processamento."
            elif runtime.status == "cancelled":
                item.status = "CANCELLED"
        await session.commit()
    metrics = calculate_batch_progress([item.status for item in items])
    return {
        "id": str(batch.id),
        "name": batch.name,
        "status": metrics["status"],
        "progress_percent": metrics["progress_percent"],
        "items": [
            {
                "id": str(item.id),
                "panel_id": str(item.panel_id),
                "status": item.status,
                "retry_count": item.retry_count,
            }
            for item in items
        ],
    }


@router.post("/generation-batches/{batch_id}/start")
async def start_generation_batch(batch_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> dict[str, str]:
    require_role(actor, EDITOR_ROLES)
    batch = await session.scalar(select(models.ComicGenerationBatch).where(
        models.ComicGenerationBatch.organization_id == actor.organization_id,
        models.ComicGenerationBatch.id == batch_id,
    ))
    if not batch:
        raise HTTPException(404, "Lote de geracao nao encontrado.")
    if batch.status in {"COMPLETED", "CANCELLED"}:
        raise HTTPException(409, "Lote finalizado nao pode ser iniciado.")
    try:
        runtime = await enqueue_domain_job(
            session,
            actor=actor,
            module_name="comic_visual_library",
            entity_type="comic_generation_batch",
            entity_id=batch.id,
            job_type="media_generation",
            total_steps=max(batch.total_items, 1),
            input_snapshot={
                "domain_batch_id": str(batch.id),
                "comic_project_id": str(batch.comic_project_id),
                "settings": batch.generation_settings,
                "steps": [f"Gerando quadro {index}" for index in range(1, max(batch.total_items, 1) + 1)],
            },
            priority=70,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    batch.generation_settings = {**batch.generation_settings, "_runtime_job_id": str(runtime.id)}
    batch.status = "RUNNING" if runtime.status == "processing" else "QUEUED"
    batch.started_at = batch.started_at or datetime.now(UTC)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_visual_library",
        action="comic.batch.queued",
        entity_type="comic_generation_batch",
        entity_id=batch.id,
        details={"runtime_job_id": str(runtime.id)},
    )
    await session.commit()
    return {"status": batch.status, "runtime_job_id": str(runtime.id)}


@router.post("/generation-batches/{batch_id}/pause")
async def pause_generation_batch(batch_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> dict[str, str]:
    require_role(actor, EDITOR_ROLES)
    batch = await session.scalar(select(models.ComicGenerationBatch).where(
        models.ComicGenerationBatch.organization_id == actor.organization_id,
        models.ComicGenerationBatch.id == batch_id,
    ))
    if not batch:
        raise HTTPException(404, "Lote de geracao nao encontrado.")
    batch.status = "PAUSED"
    await session.commit()
    return {"status": batch.status}


@router.post("/generation-batches/{batch_id}/cancel")
async def cancel_generation_batch(batch_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> dict[str, str]:
    require_role(actor, EDITOR_ROLES)
    batch = await session.scalar(select(models.ComicGenerationBatch).where(
        models.ComicGenerationBatch.organization_id == actor.organization_id,
        models.ComicGenerationBatch.id == batch_id,
    ))
    if not batch:
        raise HTTPException(404, "Lote de geracao nao encontrado.")
    batch.status = "CANCELLED"
    batch.finished_at = datetime.now(UTC)
    runtime = await cancel_domain_job(
        session,
        organization_id=actor.organization_id,
        module_name="comic_visual_library",
        entity_type="comic_generation_batch",
        entity_id=batch.id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_visual_library",
        action="comic.batch.cancelled",
        entity_type="comic_generation_batch",
        entity_id=batch.id,
        details={"runtime_job_id": str(runtime.id) if runtime else None},
    )
    await session.commit()
    return {"status": batch.status}
