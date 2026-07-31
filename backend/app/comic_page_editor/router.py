from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import (
    COVER_COMPOSITIONS,
    aspect_ratio_for_panel,
    calculate_progress,
    continuity_issues,
    reorder_page_numbers,
    select_playful_message,
    PRESERVATION_LABELS,
    stable_hash,
    validate_accessibility_payload,
    validate_grid_definition,
)
from app.services.comic_runtime import cancel_domain_job, enqueue_domain_job, runtime_job_for_domain, synchronize_simple_domain_job
from app.services.consolidated_audit import append_domain_audit

from .cover_services import (
    apply_cover_result,
    cover_payload,
    create_back_cover,
    ensure_cover,
    request_cover_variations,
    special_page,
    upsert_cover,
)
from .activity_delivery import (
    create_delivery,
    monitoring_summary,
    publish_delivery,
)
from .activity_feedback import (
    approve_profile,
    feedback_for_result,
    score_objective,
    upsert_profile,
)
from .activities import (
    ACTIVITY_TYPES,
    approve_activity,
    build_word_search,
    create_activity,
    next_special_page_number,
    validate_crossword,
)
from .editorial import (
    BUBBLE_TYPES,
    arrange_bubbles,
    bubble_conflicts,
    dialogue_suggestions,
    list_comments,
    panel_layers,
    resolve_comment,
    update_layer,
)
from .learning_analytics import (
    generate_snapshot,
    latest_snapshot,
)
from .productivity import (
    analyze_project,
    compare_snapshot_payloads,
    reorder_page_panels,
    reorder_story_pages,
)
from .student_experience import (
    combined_progress,
    experience_manifest,
    save_experience_state,
)
from .story_services import (
    apply_ai_result,
    apply_layout,
    distribute_story,
    request_ai_story,
    story_plan_for_project,
    upsert_story_plan,
)

from .schemas import (
    AutosaveRequest,
    AdvancedPageReorderRequest,
    ActivityCorrectionSimulation,
    ActivityFeedbackProfileRead,
    ActivityFeedbackProfileUpsert,
    CrosswordValidateRequest,
    HQActivityCreate,
    HQDeliveryCreate,
    HQLearningAnalyticsGenerate,
    HQStudentExperienceStateUpdate,
    HQActivityStatusUpdate,
    WordSearchBuildRequest,
    BubbleArrangeRequest,
    DialogueSuggestionRequest,
    EditorialCommentCreate,
    EditorialCommentStatusUpdate,
    TextLayerEditorialUpdate,
    CustomLayoutFromPageRequest,
    PanelReadingOrderRequest,
    ProductivityAnalysisRequest,
    SnapshotCompareRequest,
    GenerationJobCreate,
    GenerationJobRead,
    LayoutTemplateCreate,
    LayoutTemplateRead,
    PageCreate,
    PageRead,
    PanelRead,
    PanelUpdate,
    ReorderPagesRequest,
    SnapshotCreate,
    TextLayerCreate,
    ApplyAIStoryResultRequest,
    PageLayoutApplyRequest,
    StoryDistributeRequest,
    StoryGenerateRequest,
    StoryPlanRead,
    StoryPlanUpsert,
    ContinuityMetadataUpdate,
    CoverApplyResultRequest,
    CoverGenerateRequest,
    CoverPageUpsert,
    PagePreservationUpdate,
    SnapshotRestoreRequest,
    SpecialPageCreate,
)

router = APIRouter(prefix="/comic-page-editor", tags=["comic-page-editor"])
SessionDep = Annotated[Any, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]
ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
EDITOR_ROLES = ADMIN_ROLES | {"TEACHER", "COORDINATOR", "PEDAGOGICAL_COORDINATOR"}
STUDENT_ROLES = {"STUDENT", "LEARNER", "MEMBER", "ALUNO"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    roles = {str(item).upper() for item in actor.roles}
    if not roles.intersection(allowed):
        raise HTTPException(403, "Permissao insuficiente para editar HQs.")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "16.11.6", "module": "comic-page-editor"}


@router.post("/layouts/validate")
async def validate_layout(payload: LayoutTemplateCreate, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    errors = validate_grid_definition(payload.grid_definition.model_dump())
    return {"valid": not errors, "errors": errors, "panel_count": len(payload.grid_definition.panels)}


@router.post("/layouts", response_model=LayoutTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_layout(payload: LayoutTemplateCreate, session: SessionDep, actor: ActorDep) -> LayoutTemplateRead:
    require_role(actor, EDITOR_ROLES)
    grid = payload.grid_definition.model_dump()
    errors = validate_grid_definition(grid)
    if errors:
        raise HTTPException(422, {"code": "INVALID_GRID", "errors": errors})
    item = models.HQLayoutTemplate(
        organization_id=actor.organization_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        version=payload.version,
        panel_count=len(payload.grid_definition.panels),
        orientation=payload.orientation,
        category=payload.category,
        status="DRAFT",
        is_system=False,
        is_favorite=payload.is_favorite,
        grid_definition=grid,
        preview_metadata={"checksum": stable_hash(grid)},
        created_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/layouts", response_model=list[LayoutTemplateRead])
async def list_layouts(session: SessionDep, actor: ActorDep) -> list[LayoutTemplateRead]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(
        select(models.HQLayoutTemplate).where(
            (models.HQLayoutTemplate.organization_id == actor.organization_id)
            | (models.HQLayoutTemplate.is_system.is_(True))
        ).order_by(models.HQLayoutTemplate.panel_count, models.HQLayoutTemplate.name)
    )
    return list(result.scalars().all())


@router.post("/projects/{project_id}/pages", response_model=PageRead, status_code=status.HTTP_201_CREATED)
async def create_page(project_id: uuid.UUID, payload: PageCreate, session: SessionDep, actor: ActorDep) -> PageRead:
    require_role(actor, EDITOR_ROLES)
    grid = payload.grid_definition.model_dump()
    errors = validate_grid_definition(grid)
    if errors:
        raise HTTPException(422, {"code": "INVALID_GRID", "errors": errors})
    page = models.HQEditorPage(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        layout_template_id=payload.layout_template_id,
        page_number=payload.page_number,
        page_type="STORY",
        title=payload.title,
        page_width=payload.page_width,
        page_height=payload.page_height,
        accessibility_settings=payload.accessibility_settings,
        created_by_user_id=actor.user_id,
    )
    session.add(page)
    await session.flush()
    for order, rect in enumerate(payload.grid_definition.panels, start=1):
        session.add(models.HQEditorPanel(
            organization_id=actor.organization_id, page_id=page.id, panel_order=order,
            shape=rect.shape, x=rect.x, y=rect.y, width=rect.width, height=rect.height,
            aspect_ratio=aspect_ratio_for_panel(rect.width, rect.height),
        ))
    await session.commit()
    await session.refresh(page)
    return page


@router.get("/projects/{project_id}/pages", response_model=list[PageRead])
async def list_pages(project_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> list[PageRead]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(select(models.HQEditorPage).where(
        models.HQEditorPage.organization_id == actor.organization_id,
        models.HQEditorPage.comic_project_id == project_id,
    ).order_by(models.HQEditorPage.page_number))
    return list(result.scalars().all())


@router.get("/pages/{page_id}/panels", response_model=list[PanelRead])
async def list_panels(page_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> list[PanelRead]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(select(models.HQEditorPanel).where(
        models.HQEditorPanel.organization_id == actor.organization_id,
        models.HQEditorPanel.page_id == page_id,
    ).order_by(models.HQEditorPanel.panel_order))
    return list(result.scalars().all())


@router.patch("/panels/{panel_id}", response_model=PanelRead)
async def update_panel(panel_id: uuid.UUID, payload: PanelUpdate, session: SessionDep, actor: ActorDep) -> PanelRead:
    require_role(actor, EDITOR_ROLES)
    panel = await session.scalar(select(models.HQEditorPanel).where(
        models.HQEditorPanel.organization_id == actor.organization_id,
        models.HQEditorPanel.id == panel_id,
    ))
    if not panel:
        raise HTTPException(404, "Quadro nao encontrado.")
    data = payload.model_dump(exclude_unset=True)
    rect = data.pop("rect", None)
    if rect:
        for key in ("x", "y", "width", "height", "shape"):
            setattr(panel, key, rect[key])
        panel.aspect_ratio = aspect_ratio_for_panel(rect["width"], rect["height"])
    for key, value in data.items():
        setattr(panel, key, value)
    await session.commit()
    await session.refresh(panel)
    return panel


@router.post("/panels/{panel_id}/text-layers", status_code=status.HTTP_201_CREATED)
async def create_text_layer(panel_id: uuid.UUID, payload: TextLayerCreate, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    panel = await session.scalar(select(models.HQEditorPanel).where(
        models.HQEditorPanel.organization_id == actor.organization_id,
        models.HQEditorPanel.id == panel_id,
    ))
    if not panel:
        raise HTTPException(404, "Quadro nao encontrado.")
    item = models.HQPanelTextLayer(organization_id=actor.organization_id, panel_id=panel_id, **payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": item.id, "panel_id": panel_id, "layer_type": item.layer_type, "content": item.content}


@router.post("/projects/{project_id}/pages/reorder")
async def reorder_pages(project_id: uuid.UUID, payload: ReorderPagesRequest, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    mapping = reorder_page_numbers([str(item) for item in payload.page_ids])
    result = await session.execute(select(models.HQEditorPage).where(
        models.HQEditorPage.organization_id == actor.organization_id,
        models.HQEditorPage.comic_project_id == project_id,
        models.HQEditorPage.page_type == "STORY",
        models.HQEditorPage.id.in_(payload.page_ids),
    ))
    pages = list(result.scalars().all())
    if len(pages) != len(payload.page_ids):
        raise HTTPException(404, "Uma ou mais paginas nao foram encontradas.")
    for page in pages:
        page.page_number = mapping[str(page.id)]
    await session.commit()
    return {"project_id": project_id, "page_order": mapping}


@router.post("/projects/{project_id}/autosave")
async def autosave(project_id: uuid.UUID, payload: AutosaveRequest, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    expected = stable_hash(payload.payload)
    if expected != payload.checksum:
        raise HTTPException(409, {"code": "AUTOSAVE_CHECKSUM_MISMATCH", "expected": expected})
    item = await session.scalar(select(models.HQEditorAutosave).where(
        models.HQEditorAutosave.organization_id == actor.organization_id,
        models.HQEditorAutosave.comic_project_id == project_id,
        models.HQEditorAutosave.client_id == payload.client_id,
    ))
    if item and payload.sequence <= item.sequence:
        raise HTTPException(409, {"code": "AUTOSAVE_OUTDATED_SEQUENCE", "current": item.sequence})
    if not item:
        item = models.HQEditorAutosave(organization_id=actor.organization_id, comic_project_id=project_id, client_id=payload.client_id, sequence=payload.sequence, payload=payload.payload, checksum=payload.checksum, last_saved_by_user_id=actor.user_id)
        session.add(item)
    else:
        item.sequence = payload.sequence
        item.payload = payload.payload
        item.checksum = payload.checksum
        item.last_saved_by_user_id = actor.user_id
    await session.commit()
    return {"saved": True, "sequence": payload.sequence, "checksum": payload.checksum}


@router.post("/projects/{project_id}/snapshots", status_code=status.HTTP_201_CREATED)
async def create_snapshot(project_id: uuid.UUID, payload: SnapshotCreate, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    checksum = stable_hash(payload.data_snapshot)
    item = models.HQEditorSnapshot(organization_id=actor.organization_id, comic_project_id=project_id, snapshot_type=payload.snapshot_type, label=payload.label, revision_number=payload.revision_number, data_snapshot=payload.data_snapshot, checksum=checksum, created_by_user_id=actor.user_id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": item.id, "checksum": checksum, "revision_number": item.revision_number}


@router.post("/projects/{project_id}/generation-jobs", response_model=GenerationJobRead, status_code=status.HTTP_201_CREATED)
async def create_generation_job(project_id: uuid.UUID, payload: GenerationJobCreate, session: SessionDep, actor: ActorDep) -> GenerationJobRead:
    require_role(actor, EDITOR_ROLES)
    page_query = select(models.HQEditorPage).where(
        models.HQEditorPage.organization_id == actor.organization_id,
        models.HQEditorPage.comic_project_id == project_id,
    )
    if payload.selected_page_ids:
        page_query = page_query.where(models.HQEditorPage.id.in_(payload.selected_page_ids))
    pages = list((await session.execute(page_query)).scalars().all())
    panel_count = 0
    if pages:
        panel_count = len(list((await session.execute(select(models.HQEditorPanel).where(models.HQEditorPanel.page_id.in_([p.id for p in pages])))).scalars().all()))
    job = models.HQGenerationJob(organization_id=actor.organization_id, comic_project_id=project_id, requested_by_user_id=actor.user_id, status="PLANNING", progress_percent=0, current_step_code="PEDAGOGICAL_PLAN", total_pages=len(pages), total_panels=panel_count, continue_in_background=payload.continue_in_background, configuration=payload.model_dump(mode="json"), started_at=datetime.now(UTC))
    session.add(job)
    await session.flush()
    step_titles = [
        ("PEDAGOGICAL_PLAN", "Organizando os objetivos pedagogicos"),
        ("BNCC_VALIDATION", "Validando habilidades BNCC"),
        ("STORY_STRUCTURE", "Estruturando a narrativa"),
        ("PAGE_LAYOUT", "Distribuindo cenas nas paginas"),
        ("VISUAL_PROMPTS", "Preparando prompts visuais"),
        ("IMAGE_GENERATION", "Gerando imagens dos quadros"),
        ("TEXT_ASSEMBLY", "Inserindo falas e narracoes"),
        ("ACCESSIBILITY", "Verificando acessibilidade"),
        ("FINAL_PREVIEW", "Montando a previa da HQ"),
    ]
    for order, (code, title) in enumerate(step_titles, start=1):
        session.add(models.HQGenerationStep(organization_id=actor.organization_id, generation_job_id=job.id, step_order=order, step_code=code, title=title, playful_message=select_playful_message(str(job.id), order), status="PENDING", progress_weight=3 if code == "IMAGE_GENERATION" else 1))
    try:
        runtime = await enqueue_domain_job(
            session,
            actor=actor,
            module_name="comic_page_editor",
            entity_type="hq_generation_job",
            entity_id=job.id,
            job_type="media_generation",
            total_steps=len(step_titles),
            input_snapshot={
                "domain_job_id": str(job.id),
                "comic_project_id": str(project_id),
                "configuration": payload.model_dump(mode="json"),
                "steps": [title for _, title in step_titles],
            },
            priority=70,
        )
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(422, str(exc)) from exc
    job.result_summary = {"runtime_job_id": str(runtime.id)}
    job.status = "QUEUED" if runtime.status in {"pending", "queued"} else "RUNNING"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.generation.queued",
        entity_type="hq_generation_job",
        entity_id=job.id,
        details={"runtime_job_id": str(runtime.id), "project_id": str(project_id)},
    )
    await session.commit()
    await session.refresh(job)
    return job


@router.get("/generation-jobs/{job_id}", response_model=GenerationJobRead)
async def get_generation_job(job_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> GenerationJobRead:
    require_role(actor, EDITOR_ROLES)
    job = await session.scalar(select(models.HQGenerationJob).where(models.HQGenerationJob.organization_id == actor.organization_id, models.HQGenerationJob.id == job_id))
    if not job:
        raise HTTPException(404, "Geracao nao encontrada.")
    steps = list((await session.execute(select(models.HQGenerationStep).where(models.HQGenerationStep.generation_job_id == job_id).order_by(models.HQGenerationStep.step_order))).scalars().all())
    runtime = await runtime_job_for_domain(
        session,
        organization_id=actor.organization_id,
        module_name="comic_page_editor",
        entity_type="hq_generation_job",
        entity_id=job.id,
    )
    if runtime:
        synchronize_simple_domain_job(job, runtime)
        completed_count = int((runtime.progress_percent / 100) * len(steps))
        for index, step in enumerate(steps):
            if runtime.status == "failed" and index == min(completed_count, max(len(steps) - 1, 0)):
                step.status = "FAILED"
                step.error_message = runtime.error_message or "Falha no processamento."
            elif index < completed_count or runtime.status == "completed":
                step.status = "COMPLETED"
                step.finished_at = step.finished_at or datetime.now(UTC)
            elif index == completed_count and runtime.status in {"processing", "waiting_provider", "validating"}:
                step.status = "RUNNING"
                step.started_at = step.started_at or datetime.now(UTC)
                job.current_step_code = step.step_code
            elif runtime.status == "cancelled":
                step.status = "CANCELLED"
            else:
                step.status = "PENDING"
    else:
        job.progress_percent = calculate_progress([{"status": step.status, "progress_weight": step.progress_weight} for step in steps])
    await session.commit()
    return job


@router.post("/generation-jobs/{job_id}/cancel")
async def cancel_generation(job_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    job = await session.scalar(select(models.HQGenerationJob).where(models.HQGenerationJob.organization_id == actor.organization_id, models.HQGenerationJob.id == job_id))
    if not job:
        raise HTTPException(404, "Geracao nao encontrada.")
    if job.status in {"COMPLETED", "COMPLETED_WITH_ISSUES", "FAILED", "CANCELLED"}:
        raise HTTPException(409, "A geracao ja foi finalizada.")
    job.cancel_requested = True
    job.status = "CANCELLED"
    job.finished_at = datetime.now(UTC)
    runtime = await cancel_domain_job(
        session,
        organization_id=actor.organization_id,
        module_name="comic_page_editor",
        entity_type="hq_generation_job",
        entity_id=job.id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.generation.cancelled",
        entity_type="hq_generation_job",
        entity_id=job.id,
        details={"runtime_job_id": str(runtime.id) if runtime else None},
    )
    await session.commit()
    return {"cancelled": True, "job_id": job_id}


@router.post("/accessibility/validate")
async def validate_accessibility(payload: dict[str, Any], actor: ActorDep) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    warnings = validate_accessibility_payload(payload)
    return {"valid": not warnings, "warnings": warnings}


def story_plan_payload(item: models.HQStoryPlan) -> dict[str, Any]:
    return {
        "exists": True,
        "id": str(item.id),
        "comic_project_id": str(item.comic_project_id),
        "source_mode": item.source_mode,
        "total_pages": item.total_pages,
        "narrative_pacing": item.narrative_pacing,
        "distribution_mode": item.distribution_mode,
        "short_summary": item.short_summary,
        "full_script": item.full_script,
        "page_plan": item.page_plan,
        "continuity_constraints": item.continuity_constraints,
        "generation_instructions": item.generation_instructions,
        "generation_status": item.generation_status,
        "ai_generation_request_id": (
            str(item.ai_generation_request_id)
            if item.ai_generation_request_id
            else None
        ),
        "content_hash": item.content_hash,
        "revision_number": item.revision_number,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/preservation-options")
async def preservation_options(
    actor: ActorDep,
) -> list[dict[str, str]]:
    require_role(actor, EDITOR_ROLES)
    return [
        {"key": key, "label": label}
        for key, label in PRESERVATION_LABELS.items()
    ]


@router.get("/projects/{project_id}/story-plan")
async def get_story_plan(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await story_plan_for_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )
    if item is None:
        page_count = len(
            list(
                (
                    await session.execute(
                        select(models.HQEditorPage.id).where(
                            models.HQEditorPage.organization_id
                            == actor.organization_id,
                            models.HQEditorPage.comic_project_id
                            == project_id,
                        )
                    )
                ).scalars().all()
            )
        )
        return {
            "exists": False,
            "comic_project_id": str(project_id),
            "source_mode": "MANUAL",
            "total_pages": max(1, page_count),
            "narrative_pacing": "BALANCED",
            "distribution_mode": "AUTOMATIC",
            "short_summary": "",
            "full_script": "",
            "page_plan": [],
            "continuity_constraints": {},
            "generation_instructions": {},
            "generation_status": "DRAFT",
            "ai_generation_request_id": None,
            "revision_number": 0,
        }
    return story_plan_payload(item)


@router.put("/projects/{project_id}/story-plan")
async def save_story_plan(
    project_id: uuid.UUID,
    payload: StoryPlanUpsert,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await upsert_story_plan(
        session,
        actor=actor,
        project_id=project_id,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.story_plan.saved",
        entity_type="hq_story_plan",
        entity_id=item.id,
        details={
            "project_id": str(project_id),
            "source_mode": item.source_mode,
            "total_pages": item.total_pages,
            "narrative_pacing": item.narrative_pacing,
            "distribution_mode": item.distribution_mode,
            "revision_number": item.revision_number,
        },
    )
    await session.commit()
    await session.refresh(item)
    return story_plan_payload(item)


@router.post("/projects/{project_id}/story-plan/generate")
async def generate_story_plan(
    project_id: uuid.UUID,
    payload: StoryGenerateRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item, request = await request_ai_story(
        session,
        actor=actor,
        project_id=project_id,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.story_plan.ai_queued",
        entity_type="hq_story_plan",
        entity_id=item.id,
        details={
            "project_id": str(project_id),
            "ai_request_id": str(request.id),
            "total_pages": item.total_pages,
            "page_capacities": [
                page.get("panel_count")
                for page in item.page_plan
            ],
        },
    )
    await session.commit()
    return {
        "story_plan": story_plan_payload(item),
        "ai_request_id": str(request.id),
        "ai_status": request.status,
        "message": (
            "A IA recebeu o número total de páginas e a capacidade real "
            "dos grids. Um rascunho estrutural já foi preparado para revisão."
        ),
    }


@router.post("/projects/{project_id}/story-plan/distribute")
async def distribute_story_plan(
    project_id: uuid.UUID,
    payload: StoryDistributeRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await story_plan_for_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        lock=True,
    )
    if item is None:
        raise HTTPException(
            409,
            "Salve o roteiro ou gere um rascunho com IA antes de distribuir.",
        )
    plan = await distribute_story(
        session,
        actor=actor,
        story_plan=item,
        ensure_total_pages=payload.ensure_total_pages,
        preserve_existing_summaries=(
            payload.preserve_existing_summaries
        ),
        apply_layout_recommendations=(
            payload.apply_layout_recommendations
        ),
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.story_plan.distributed",
        entity_type="hq_story_plan",
        entity_id=item.id,
        details={
            "project_id": str(project_id),
            "pages": len(plan),
            "panels": sum(
                len(page.get("panels", [])) for page in plan
            ),
            "apply_layout_recommendations": (
                payload.apply_layout_recommendations
            ),
        },
    )
    await session.commit()
    return {
        "story_plan": story_plan_payload(item),
        "pages": len(plan),
        "panels": sum(len(page["panels"]) for page in plan),
    }


@router.post("/projects/{project_id}/story-plan/apply-ai-result")
async def apply_story_ai_result(
    project_id: uuid.UUID,
    payload: ApplyAIStoryResultRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await story_plan_for_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        lock=True,
    )
    if item is None:
        raise HTTPException(404, "Planejamento narrativo não encontrado.")
    item = await apply_ai_result(
        session,
        actor=actor,
        story_plan=item,
        result_id=payload.result_id,
        distribute_after_apply=payload.distribute_after_apply,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.story_plan.ai_result_applied",
        entity_type="hq_story_plan",
        entity_id=item.id,
        details={
            "result_id": str(payload.result_id),
            "distribute_after_apply": payload.distribute_after_apply,
        },
    )
    await session.commit()
    return story_plan_payload(item)


@router.post("/pages/{page_id}/layout", response_model=list[PanelRead])
async def apply_page_layout(
    page_id: uuid.UUID,
    payload: PageLayoutApplyRequest,
    session: SessionDep,
    actor: ActorDep,
) -> list[PanelRead]:
    require_role(actor, EDITOR_ROLES)
    page = await session.scalar(
        select(models.HQEditorPage)
        .where(
            models.HQEditorPage.organization_id == actor.organization_id,
            models.HQEditorPage.id == page_id,
        )
        .with_for_update()
    )
    if page is None:
        raise HTTPException(404, "Página não encontrada.")
    layout = await session.scalar(
        select(models.HQLayoutTemplate).where(
            models.HQLayoutTemplate.id == payload.layout_template_id,
            (
                (
                    models.HQLayoutTemplate.organization_id
                    == actor.organization_id
                )
                | (models.HQLayoutTemplate.is_system.is_(True))
            ),
            models.HQLayoutTemplate.status != "ARCHIVED",
        )
    )
    if layout is None:
        raise HTTPException(404, "Grid não encontrado.")
    panels = await apply_layout(
        session,
        actor=actor,
        page=page,
        layout=layout,
        preserve_content=payload.preserve_content,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.page.layout_applied",
        entity_type="hq_editor_page",
        entity_id=page.id,
        details={
            "layout_template_id": str(layout.id),
            "layout_code": layout.code,
            "panel_count": len(panels),
            "preserve_content": payload.preserve_content,
        },
    )
    await session.commit()
    return panels


@router.get("/cover-compositions")
async def cover_compositions(
    actor: ActorDep,
) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    return [
        {"code": code, **settings}
        for code, settings in COVER_COMPOSITIONS.items()
    ]


@router.get("/projects/{project_id}/cover")
async def get_cover_page(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    page = await ensure_cover(
        session,
        actor=actor,
        project_id=project_id,
    )
    await session.commit()
    return cover_payload(page)


@router.put("/projects/{project_id}/cover")
async def save_cover_page(
    project_id: uuid.UUID,
    payload: CoverPageUpsert,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    page = await upsert_cover(
        session,
        actor=actor,
        project_id=project_id,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.cover.saved",
        entity_type="hq_editor_page",
        entity_id=page.id,
        details={
            "project_id": str(project_id),
            "composition_code": payload.composition_code,
            "revision_number": page.revision_number,
        },
    )
    await session.commit()
    await session.refresh(page)
    return cover_payload(page)


@router.post("/projects/{project_id}/cover/generate")
async def generate_cover_variations(
    project_id: uuid.UUID,
    payload: CoverGenerateRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    cover = await ensure_cover(
        session,
        actor=actor,
        project_id=project_id,
    )
    story = await story_plan_for_project(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )
    request = await request_cover_variations(
        session,
        actor=actor,
        project_id=project_id,
        cover=cover,
        story_plan=story,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.cover.ai_queued",
        entity_type="hq_editor_page",
        entity_id=cover.id,
        details={
            "request_id": str(request.id),
            "variation_count": payload.variation_count,
            "forbid_text_in_image": True,
        },
    )
    await session.commit()
    return {
        "cover": cover_payload(cover),
        "ai_request_id": str(request.id),
        "status": request.status,
        "message": (
            "A IA gerará variações sem texto incorporado. "
            "O professor deverá comparar e confirmar antes de aplicar."
        ),
    }


@router.post("/projects/{project_id}/cover/apply-result")
async def apply_cover_variation(
    project_id: uuid.UUID,
    payload: CoverApplyResultRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    cover = await ensure_cover(
        session,
        actor=actor,
        project_id=project_id,
    )
    result = await apply_cover_result(
        session,
        actor=actor,
        project_id=project_id,
        cover=cover,
        result_id=payload.result_id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.cover.variation_applied",
        entity_type="hq_editor_page",
        entity_id=cover.id,
        details={
            "result_id": str(result.id),
            "comparison_required": True,
        },
    )
    await session.commit()
    return cover_payload(cover)


@router.post("/projects/{project_id}/special-pages")
async def create_special_page(
    project_id: uuid.UUID,
    payload: SpecialPageCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    if payload.page_type == "COVER":
        page = await ensure_cover(
            session,
            actor=actor,
            project_id=project_id,
        )
    elif payload.page_type == "BACK_COVER":
        page = await create_back_cover(
            session,
            actor=actor,
            project_id=project_id,
            title=payload.title,
        )
    else:
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
            page_type=payload.page_type,
            title=payload.title,
            status="DRAFT",
            page_width=1200,
            page_height=1600,
            background_settings={},
            accessibility_settings={},
            content_layers=[],
            preservation_settings={},
            continuity_metadata={},
            cover_generation={},
            revision_number=1,
            created_by_user_id=actor.user_id,
        )
        session.add(page)
        await session.flush()
    await session.commit()
    return page


@router.put("/pages/{page_id}/continuity")
async def update_page_continuity(
    page_id: uuid.UUID,
    payload: ContinuityMetadataUpdate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    page = await session.scalar(
        select(models.HQEditorPage)
        .where(
            models.HQEditorPage.organization_id
            == actor.organization_id,
            models.HQEditorPage.id == page_id,
        )
        .with_for_update()
    )
    if page is None:
        raise HTTPException(404, "Página não encontrada.")
    page.continuity_metadata = payload.model_dump()
    page.revision_number += 1
    await session.commit()
    return {
        "page_id": str(page.id),
        "continuity_metadata": page.continuity_metadata,
    }


@router.put("/pages/{page_id}/preservation")
async def update_page_preservation(
    page_id: uuid.UUID,
    payload: PagePreservationUpdate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    page = await session.scalar(
        select(models.HQEditorPage)
        .where(
            models.HQEditorPage.organization_id
            == actor.organization_id,
            models.HQEditorPage.id == page_id,
        )
        .with_for_update()
    )
    if page is None:
        raise HTTPException(404, "Página não encontrada.")
    if payload.scope == "PANEL":
        if payload.panel_id is None:
            raise HTTPException(
                422,
                "Informe o quadro para preservação local.",
            )
        panel = await session.scalar(
            select(models.HQEditorPanel).where(
                models.HQEditorPanel.organization_id
                == actor.organization_id,
                models.HQEditorPanel.page_id == page.id,
                models.HQEditorPanel.id == payload.panel_id,
            )
        )
        if panel is None:
            raise HTTPException(404, "Quadro não encontrado.")
        panel.locked_elements = payload.elements
    elif payload.scope == "PAGE":
        page.preservation_settings = {
            "scope": "PAGE",
            "elements": payload.elements,
        }
    else:
        story = await story_plan_for_project(
            session,
            organization_id=actor.organization_id,
            project_id=page.comic_project_id,
            lock=True,
        )
        if story is None:
            raise HTTPException(
                409,
                "Salve o planejamento narrativo antes da preservação global.",
            )
        story.continuity_constraints = {
            **story.continuity_constraints,
            "preservation_scope": "PROJECT",
            "preserved_elements": payload.elements,
        }
        page.preservation_settings = {
            "scope": "PROJECT",
            "elements": payload.elements,
        }
    await session.commit()
    return {
        "scope": payload.scope,
        "elements": payload.elements,
        "page_id": str(page.id),
    }


@router.get("/projects/{project_id}/continuity-map")
async def get_continuity_map(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    pages = list(
        (
            await session.scalars(
                select(models.HQEditorPage)
                .where(
                    models.HQEditorPage.organization_id
                    == actor.organization_id,
                    models.HQEditorPage.comic_project_id == project_id,
                    models.HQEditorPage.page_type.in_(
                        ["COVER", "STORY"]
                    ),
                )
                .order_by(models.HQEditorPage.page_number)
            )
        ).all()
    )
    rows = [
        {
            "page_id": str(page.id),
            "page_number": page.page_number,
            "page_type": page.page_type,
            **(page.continuity_metadata or {}),
        }
        for page in pages
    ]
    return {
        "project_id": str(project_id),
        "pages": rows,
        "issues": continuity_issues(rows),
    }


@router.get("/projects/{project_id}/autosave/latest")
async def get_latest_autosave(
    project_id: uuid.UUID,
    client_id: str,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.HQEditorAutosave)
        .where(
            models.HQEditorAutosave.organization_id
            == actor.organization_id,
            models.HQEditorAutosave.comic_project_id == project_id,
            models.HQEditorAutosave.client_id == client_id,
        )
        .order_by(models.HQEditorAutosave.updated_at.desc())
        .limit(1)
    )
    if item is None:
        return {"exists": False}
    return {
        "exists": True,
        "id": str(item.id),
        "sequence": item.sequence,
        "payload": item.payload,
        "checksum": item.checksum,
        "updated_at": item.updated_at,
    }


@router.get("/projects/{project_id}/snapshots")
async def list_project_snapshots(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    rows = list(
        (
            await session.scalars(
                select(models.HQEditorSnapshot)
                .where(
                    models.HQEditorSnapshot.organization_id
                    == actor.organization_id,
                    models.HQEditorSnapshot.comic_project_id
                    == project_id,
                )
                .order_by(
                    models.HQEditorSnapshot.created_at.desc()
                )
                .limit(100)
            )
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "snapshot_type": item.snapshot_type,
            "label": item.label,
            "revision_number": item.revision_number,
            "checksum": item.checksum,
            "created_at": item.created_at,
        }
        for item in rows
    ]


@router.post("/projects/{project_id}/snapshots/restore")
async def restore_snapshot_payload(
    project_id: uuid.UUID,
    payload: SnapshotRestoreRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.HQEditorSnapshot).where(
            models.HQEditorSnapshot.organization_id
            == actor.organization_id,
            models.HQEditorSnapshot.comic_project_id == project_id,
            models.HQEditorSnapshot.id == payload.snapshot_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Snapshot não encontrado.")
    return {
        "snapshot_id": str(item.id),
        "revision_number": item.revision_number,
        "checksum": item.checksum,
        "payload": item.data_snapshot,
        "requires_confirmation": True,
    }


@router.get("/projects/{project_id}/cover/results/{result_id}")
async def preview_cover_variation(
    project_id: uuid.UUID,
    result_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    from app.models.ai_runtime import (
        AIGenerationRequest,
        AIGenerationResult,
    )

    result = await session.scalar(
        select(AIGenerationResult).where(
            AIGenerationResult.organization_id
            == actor.organization_id,
            AIGenerationResult.id == result_id,
        )
    )
    if result is None:
        raise HTTPException(404, "Variação não encontrada.")
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
    asset_reference = (
        result.storage_reference
        or result.structured_content.get("asset_reference")
        or result.structured_content.get("url")
    )
    if not asset_reference:
        raise HTTPException(
            409,
            "A variação ainda não possui imagem disponível.",
        )
    return {
        "result_id": str(result.id),
        "asset_reference": asset_reference,
        "review_status": result.review_status,
        "applied_to_module": result.applied_to_module,
        "requires_confirmation": True,
    }


@router.post("/projects/{project_id}/productivity/analyze")
async def analyze_editor_productivity(
    project_id: uuid.UUID,
    payload: ProductivityAnalysisRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    result = await analyze_project(
        session,
        actor=actor,
        project_id=project_id,
        expected_story_pages=payload.expected_story_pages,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.productivity.analyzed",
        entity_type="comic_project",
        entity_id=project_id,
        details={
            "publication_status": result["publication_status"],
            "rhythm_warning_count": result["rhythm"]["warning_count"],
            "blocked_panels": result["readability"]["blocked"],
        },
    )
    await session.commit()
    return result


@router.post("/projects/{project_id}/pages/reorder-advanced")
async def advanced_reorder_pages(
    project_id: uuid.UUID,
    payload: AdvancedPageReorderRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    pages = await reorder_story_pages(
        session,
        actor=actor,
        project_id=project_id,
        ordered_story_page_ids=payload.ordered_story_page_ids,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.story_pages.reordered",
        entity_type="comic_project",
        entity_id=project_id,
        details={
            "ordered_story_page_ids": [
                str(item) for item in payload.ordered_story_page_ids
            ],
            "recalculate_narrative": payload.recalculate_narrative,
        },
    )
    await session.commit()
    return {
        "project_id": str(project_id),
        "story_page_order": [
            {
                "page_id": str(page.id),
                "page_number": page.page_number,
            }
            for page in pages
            if page.page_type == "STORY"
        ],
        "recalculate_narrative": payload.recalculate_narrative,
    }


@router.post("/pages/{page_id}/panels/reorder", response_model=list[PanelRead])
async def reorder_panels_reading_order(
    page_id: uuid.UUID,
    payload: PanelReadingOrderRequest,
    session: SessionDep,
    actor: ActorDep,
) -> list[PanelRead]:
    require_role(actor, EDITOR_ROLES)
    panels = await reorder_page_panels(
        session,
        actor=actor,
        page_id=page_id,
        ordered_panel_ids=payload.ordered_panel_ids,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.panels.reordered",
        entity_type="hq_editor_page",
        entity_id=page_id,
        details={
            "ordered_panel_ids": [
                str(item) for item in payload.ordered_panel_ids
            ],
        },
    )
    await session.commit()
    return panels


@router.post("/projects/{project_id}/snapshots/compare")
async def compare_editor_snapshots(
    project_id: uuid.UUID,
    payload: SnapshotCompareRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    snapshots = list(
        (
            await session.scalars(
                select(models.HQEditorSnapshot).where(
                    models.HQEditorSnapshot.organization_id
                    == actor.organization_id,
                    models.HQEditorSnapshot.comic_project_id
                    == project_id,
                    models.HQEditorSnapshot.id.in_(
                        [
                            payload.left_snapshot_id,
                            payload.right_snapshot_id,
                        ]
                    ),
                )
            )
        ).all()
    )
    by_id = {item.id: item for item in snapshots}
    if (
        payload.left_snapshot_id not in by_id
        or payload.right_snapshot_id not in by_id
    ):
        raise HTTPException(404, "Um dos snapshots não foi encontrado.")
    left = by_id[payload.left_snapshot_id]
    right = by_id[payload.right_snapshot_id]
    return {
        "left": {
            "id": str(left.id),
            "label": left.label,
            "created_at": left.created_at,
        },
        "right": {
            "id": str(right.id),
            "label": right.label,
            "created_at": right.created_at,
        },
        "comparison": compare_snapshot_payloads(
            left.snapshot_data,
            right.snapshot_data,
        ),
    }


@router.post("/pages/{page_id}/save-as-layout", response_model=LayoutTemplateRead)
async def save_page_as_custom_layout(
    page_id: uuid.UUID,
    payload: CustomLayoutFromPageRequest,
    session: SessionDep,
    actor: ActorDep,
) -> LayoutTemplateRead:
    require_role(actor, EDITOR_ROLES)
    page = await session.scalar(
        select(models.HQEditorPage).where(
            models.HQEditorPage.organization_id == actor.organization_id,
            models.HQEditorPage.id == page_id,
            models.HQEditorPage.page_type == "STORY",
        )
    )
    if page is None:
        raise HTTPException(404, "Página narrativa não encontrada.")
    panels = list(
        (
            await session.scalars(
                select(models.HQEditorPanel)
                .where(
                    models.HQEditorPanel.organization_id
                    == actor.organization_id,
                    models.HQEditorPanel.page_id == page_id,
                )
                .order_by(models.HQEditorPanel.panel_order)
            )
        ).all()
    )
    grid = {
        "gutter": 0.02,
        "page_margin": 0.02,
        "panels": [
            {
                "x": panel.x,
                "y": panel.y,
                "width": panel.width,
                "height": panel.height,
                "shape": panel.shape,
            }
            for panel in panels
        ],
    }
    existing = await session.scalar(
        select(models.HQLayoutTemplate).where(
            models.HQLayoutTemplate.organization_id
            == actor.organization_id,
            models.HQLayoutTemplate.code == payload.code,
            models.HQLayoutTemplate.status != "ARCHIVED",
        )
    )
    if existing is not None:
        raise HTTPException(409, "Já existe um layout ativo com esse código.")
    layout = models.HQLayoutTemplate(
        organization_id=actor.organization_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        version="1.0.0",
        panel_count=len(panels),
        orientation="PORTRAIT",
        category=payload.category,
        status="PUBLISHED",
        is_system=False,
        is_favorite=True,
        grid_definition=grid,
        preview_metadata={
            "source_page_id": str(page_id),
            "created_from_editor": True,
        },
        created_by_user_id=actor.user_id,
    )
    session.add(layout)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.layout.saved_from_page",
        entity_type="hq_layout_template",
        entity_id=layout.id,
        details={
            "page_id": str(page_id),
            "code": payload.code,
            "panel_count": len(panels),
        },
    )
    await session.commit()
    await session.refresh(layout)
    return layout


@router.get("/bubble-types")
async def bubble_types(actor: ActorDep) -> list[dict[str, str]]:
    require_role(actor, EDITOR_ROLES)
    return [
        {"code": code, "label": label}
        for code, label in BUBBLE_TYPES.items()
    ]


@router.patch("/text-layers/{layer_id}")
async def edit_text_layer(
    layer_id: uuid.UUID,
    payload: TextLayerEditorialUpdate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await update_layer(
        session,
        actor=actor,
        layer_id=layer_id,
        data=payload.model_dump(exclude_unset=True),
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.text_layer.updated",
        entity_type="hq_panel_text_layer",
        entity_id=layer_id,
        details={
            "layer_type": item.layer_type,
            "review_status": item.review_status,
            "reading_order": item.reading_order,
        },
    )
    await session.commit()
    return {
        "id": str(item.id),
        "panel_id": str(item.panel_id),
        "layer_type": item.layer_type,
        "speaker_name": item.speaker_name,
        "content": item.content,
        "x": item.x,
        "y": item.y,
        "width": item.width,
        "height": item.height,
        "style": item.style,
        "reading_order": item.reading_order,
        "bubble_metadata": item.bubble_metadata,
        "accessibility_metadata": item.accessibility_metadata,
        "review_status": item.review_status,
        "linked_character_id": (
            str(item.linked_character_id)
            if item.linked_character_id
            else None
        ),
    }


@router.get("/panels/{panel_id}/text-layers")
async def list_panel_text_layers(
    panel_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    items = await panel_layers(
        session,
        organization_id=actor.organization_id,
        panel_id=panel_id,
    )
    return [
        {
            "id": str(item.id),
            "panel_id": str(item.panel_id),
            "layer_type": item.layer_type,
            "speaker_name": item.speaker_name,
            "content": item.content,
            "x": item.x,
            "y": item.y,
            "width": item.width,
            "height": item.height,
            "style": item.style,
            "reading_order": item.reading_order,
            "bubble_metadata": item.bubble_metadata,
            "accessibility_metadata": item.accessibility_metadata,
            "review_status": item.review_status,
            "linked_character_id": (
                str(item.linked_character_id)
                if item.linked_character_id
                else None
            ),
        }
        for item in items
    ]


@router.post("/panels/{panel_id}/bubbles/analyze")
async def analyze_panel_bubbles(
    panel_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    items = await panel_layers(
        session,
        organization_id=actor.organization_id,
        panel_id=panel_id,
    )
    layers = [
        {
            "id": str(item.id),
            "content": item.content,
            "x": item.x,
            "y": item.y,
            "width": item.width,
            "height": item.height,
            "reading_order": item.reading_order,
        }
        for item in items
    ]
    conflicts = bubble_conflicts(layers=layers)
    return {
        "panel_id": str(panel_id),
        "status": (
            "CRITICAL"
            if any(item["severity"] == "CRITICAL" for item in conflicts)
            else "WARNING"
            if conflicts
            else "READY"
        ),
        "conflicts": conflicts,
    }


@router.post("/panels/{panel_id}/bubbles/arrange")
async def auto_arrange_panel_bubbles(
    panel_id: uuid.UUID,
    payload: BubbleArrangeRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    items = await panel_layers(
        session,
        organization_id=actor.organization_id,
        panel_id=panel_id,
    )
    selected = [
        item for item in items if item.id in set(payload.layer_ids)
    ]
    if len(selected) != len(payload.layer_ids):
        raise HTTPException(404, "Um ou mais balões não foram encontrados.")
    arranged = arrange_bubbles(
        [
            {
                "id": str(item.id),
                "content": item.content,
                "x": item.x,
                "y": item.y,
                "width": item.width,
                "height": item.height,
                "reading_order": item.reading_order,
                "bubble_metadata": item.bubble_metadata,
            }
            for item in selected
        ]
    )
    by_id = {str(item.id): item for item in selected}
    for data in arranged:
        item = by_id[data["id"]]
        item.x = data["x"]
        item.y = data["y"]
        item.width = data["width"]
        item.height = data["height"]
        item.reading_order = data["reading_order"]
        item.bubble_metadata = data["bubble_metadata"]
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.bubbles.auto_arranged",
        entity_type="hq_editor_panel",
        entity_id=panel_id,
        details={"layer_count": len(arranged)},
    )
    await session.commit()
    return {"panel_id": str(panel_id), "layers": arranged}


@router.post("/dialogue/suggestions")
async def suggest_dialogue_edits(
    payload: DialogueSuggestionRequest,
    actor: ActorDep,
) -> list[dict[str, str]]:
    require_role(actor, EDITOR_ROLES)
    return dialogue_suggestions(
        content=payload.content,
        school_year=payload.school_year,
        tone=payload.tone,
    )


@router.get("/projects/{project_id}/editorial-comments")
async def project_editorial_comments(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    items = await list_comments(
        session,
        actor=actor,
        project_id=project_id,
    )
    return [
        {
            "id": str(item.id),
            "project_id": str(item.comic_project_id),
            "target_type": item.target_type,
            "target_id": str(item.target_id),
            "content": item.content,
            "status": item.status,
            "priority": item.priority,
            "created_by_user_id": str(item.created_by_user_id),
            "resolved_by_user_id": (
                str(item.resolved_by_user_id)
                if item.resolved_by_user_id
                else None
            ),
            "resolved_at": item.resolved_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        for item in items
    ]


@router.post("/projects/{project_id}/editorial-comments")
async def create_editorial_comment(
    project_id: uuid.UUID,
    payload: EditorialCommentCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = models.HQEditorialComment(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        content=payload.content,
        status="OPEN",
        priority=payload.priority,
        created_by_user_id=actor.user_id,
    )
    session.add(item)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.editorial_comment.created",
        entity_type=payload.target_type.lower(),
        entity_id=payload.target_id,
        details={
            "project_id": str(project_id),
            "priority": payload.priority,
        },
    )
    await session.commit()
    await session.refresh(item)
    return {
        "id": str(item.id),
        "status": item.status,
        "priority": item.priority,
    }


@router.patch("/editorial-comments/{comment_id}/status")
async def update_editorial_comment_status(
    comment_id: uuid.UUID,
    payload: EditorialCommentStatusUpdate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await resolve_comment(
        session,
        actor=actor,
        comment_id=comment_id,
        status=payload.status,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.editorial_comment.status_changed",
        entity_type="hq_editorial_comment",
        entity_id=comment_id,
        details={"status": payload.status},
    )
    await session.commit()
    return {
        "id": str(item.id),
        "status": item.status,
        "resolved_at": item.resolved_at,
    }


@router.get("/activity-types")
async def activity_types(actor: ActorDep) -> list[dict[str, str]]:
    require_role(actor, EDITOR_ROLES)
    return [
        {"code": code, "label": label}
        for code, label in ACTIVITY_TYPES.items()
    ]


@router.post("/activities/word-search/build")
async def build_activity_word_search(
    payload: WordSearchBuildRequest,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    try:
        return build_word_search(payload.words, payload.size)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post("/activities/crossword/validate")
async def validate_activity_crossword(
    payload: CrosswordValidateRequest,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    return validate_crossword(payload.entries)


@router.post("/projects/{project_id}/activities")
async def create_hq_activity(
    project_id: uuid.UUID,
    payload: HQActivityCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    binding, page = await create_activity(
        session,
        actor=actor,
        project_id=project_id,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.activity.created",
        entity_type="hq_activity_binding",
        entity_id=binding.id,
        details={
            "activity_type": binding.activity_type,
            "activity_page_id": str(page.id),
            "question_version_id": str(binding.question_version_id),
            "teacher_review_required": True,
        },
    )
    await session.commit()
    return {
        "id": str(binding.id),
        "activity_page_id": str(page.id),
        "question_id": str(binding.question_id),
        "question_version_id": str(binding.question_version_id),
        "activity_type": binding.activity_type,
        "title": binding.title,
        "status": binding.status,
    }


@router.get("/projects/{project_id}/activities")
async def list_hq_activities(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> list[dict[str, Any]]:
    require_role(actor, EDITOR_ROLES)
    items = list(
        (
            await session.scalars(
                select(models.HQActivityBinding)
                .where(
                    models.HQActivityBinding.organization_id
                    == actor.organization_id,
                    models.HQActivityBinding.comic_project_id
                    == project_id,
                )
                .order_by(models.HQActivityBinding.display_order)
            )
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "activity_page_id": str(item.activity_page_id),
            "source_page_id": (
                str(item.source_page_id) if item.source_page_id else None
            ),
            "source_panel_id": (
                str(item.source_panel_id) if item.source_panel_id else None
            ),
            "question_id": (
                str(item.question_id) if item.question_id else None
            ),
            "question_version_id": (
                str(item.question_version_id)
                if item.question_version_id
                else None
            ),
            "publication_id": (
                str(item.publication_id) if item.publication_id else None
            ),
            "activity_type": item.activity_type,
            "title": item.title,
            "instructions": item.instructions,
            "activity_payload": item.activity_payload,
            "answer_key": item.answer_key,
            "pedagogical_links": item.pedagogical_links,
            "accessibility": item.accessibility,
            "difficulty": item.difficulty,
            "status": item.status,
            "display_order": item.display_order,
            "max_score": item.max_score,
            "teacher_review_required": item.teacher_review_required,
        }
        for item in items
    ]


@router.post("/activities/{activity_id}/approve")
async def approve_hq_activity(
    activity_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await approve_activity(
        session,
        actor=actor,
        activity_id=activity_id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.activity.approved",
        entity_type="hq_activity_binding",
        entity_id=item.id,
        details={
            "question_version_id": str(item.question_version_id),
            "status": item.status,
        },
    )
    await session.commit()
    return {
        "id": str(item.id),
        "status": item.status,
        "reviewed_at": item.reviewed_at,
    }


@router.post("/projects/{project_id}/activities/answer-key-page")
async def ensure_answer_key_page(
    project_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    existing = await session.scalar(
        select(models.HQEditorPage).where(
            models.HQEditorPage.organization_id == actor.organization_id,
            models.HQEditorPage.comic_project_id == project_id,
            models.HQEditorPage.page_type == "ANSWER_KEY",
        )
    )
    if existing is None:
        number = await next_special_page_number(
            session,
            organization_id=actor.organization_id,
            project_id=project_id,
        )
        existing = models.HQEditorPage(
            organization_id=actor.organization_id,
            comic_project_id=project_id,
            page_number=number,
            page_type="ANSWER_KEY",
            title="Gabarito",
            status="DRAFT",
            page_width=1200,
            page_height=1600,
            background_settings={"answer_key": True},
            accessibility_settings={"teacher_only": True},
            content_layers=[],
            preservation_settings={},
            continuity_metadata={},
            cover_generation={},
            revision_number=1,
            created_by_user_id=actor.user_id,
        )
        session.add(existing)
        await session.flush()
    await session.commit()
    return {"page_id": str(existing.id), "page_type": "ANSWER_KEY"}


@router.put("/activities/{activity_id}/feedback-profile")
async def upsert_activity_feedback_profile(
    activity_id: uuid.UUID,
    payload: ActivityFeedbackProfileUpsert,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    profile = await upsert_profile(
        session,
        actor=actor,
        activity_id=activity_id,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.activity_feedback_profile.saved",
        entity_type="hq_activity_feedback_profile",
        entity_id=profile.id,
        details={
            "activity_id": str(activity_id),
            "correction_mode": profile.correction_mode,
            "rubric_version_id": (
                str(profile.rubric_version_id)
                if profile.rubric_version_id
                else None
            ),
        },
    )
    await session.commit()
    return {
        "id": str(profile.id),
        "activity_binding_id": str(profile.activity_binding_id),
        "rubric_id": str(profile.rubric_id) if profile.rubric_id else None,
        "rubric_version_id": (
            str(profile.rubric_version_id)
            if profile.rubric_version_id
            else None
        ),
        "correction_mode": profile.correction_mode,
        "feedback_templates": profile.feedback_templates,
        "graduated_hints": profile.graduated_hints,
        "common_errors": profile.common_errors,
        "review_rules": profile.review_rules,
        "appeal_enabled": profile.appeal_enabled,
        "status": profile.status,
    }


@router.get("/activities/{activity_id}/feedback-profile")
async def get_activity_feedback_profile(
    activity_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any] | None:
    require_role(actor, EDITOR_ROLES)
    profile = await session.scalar(
        select(models.HQActivityFeedbackProfile).where(
            models.HQActivityFeedbackProfile.organization_id
            == actor.organization_id,
            models.HQActivityFeedbackProfile.activity_binding_id
            == activity_id,
        )
    )
    if profile is None:
        return None
    return {
        "id": str(profile.id),
        "activity_binding_id": str(profile.activity_binding_id),
        "rubric_id": str(profile.rubric_id) if profile.rubric_id else None,
        "rubric_version_id": (
            str(profile.rubric_version_id)
            if profile.rubric_version_id
            else None
        ),
        "correction_mode": profile.correction_mode,
        "feedback_templates": profile.feedback_templates,
        "graduated_hints": profile.graduated_hints,
        "common_errors": profile.common_errors,
        "review_rules": profile.review_rules,
        "appeal_enabled": profile.appeal_enabled,
        "status": profile.status,
    }


@router.post("/activities/{activity_id}/feedback-profile/approve")
async def approve_activity_feedback_profile(
    activity_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    profile = await session.scalar(
        select(models.HQActivityFeedbackProfile).where(
            models.HQActivityFeedbackProfile.organization_id
            == actor.organization_id,
            models.HQActivityFeedbackProfile.activity_binding_id
            == activity_id,
        )
    )
    if profile is None:
        raise HTTPException(404, "Perfil de correção não encontrado.")
    profile = await approve_profile(
        session,
        actor=actor,
        profile_id=profile.id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.activity_feedback_profile.approved",
        entity_type="hq_activity_feedback_profile",
        entity_id=profile.id,
        details={"activity_id": str(activity_id)},
    )
    await session.commit()
    return {
        "id": str(profile.id),
        "status": profile.status,
        "reviewed_at": profile.reviewed_at,
    }


@router.post("/activities/{activity_id}/correction/simulate")
async def simulate_activity_correction(
    activity_id: uuid.UUID,
    payload: ActivityCorrectionSimulation,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    activity = await session.scalar(
        select(models.HQActivityBinding).where(
            models.HQActivityBinding.organization_id
            == actor.organization_id,
            models.HQActivityBinding.id == activity_id,
        )
    )
    if activity is None:
        raise HTTPException(404, "Atividade não encontrada.")
    profile = await session.scalar(
        select(models.HQActivityFeedbackProfile).where(
            models.HQActivityFeedbackProfile.organization_id
            == actor.organization_id,
            models.HQActivityFeedbackProfile.activity_binding_id
            == activity_id,
        )
    )
    result = score_objective(
        activity.activity_type,
        activity.answer_key,
        payload.response,
        activity.max_score,
        profile.correction_mode if profile else None,
    )
    feedback = feedback_for_result(
        result=result,
        templates=profile.feedback_templates if profile else {},
        hints=profile.graduated_hints if profile else [],
        source_reference=activity.pedagogical_links,
    )
    return {
        "activity_id": str(activity_id),
        "result": result,
        "feedback": feedback,
        "correction_mode": (
            profile.correction_mode
            if profile
            else (
                "AUTOMATIC"
                if activity.activity_type in {
                    "MULTIPLE_CHOICE",
                    "TRUE_FALSE",
                    "MATCHING",
                    "ORDERING",
                    "FILL_BLANKS",
                    "CROSSWORD",
                    "WORD_SEARCH",
                }
                else "HUMAN"
            )
        ),
    }

@router.post("/projects/{project_id}/activity-deliveries")
async def create_hq_activity_delivery(project_id:uuid.UUID,payload:HQDeliveryCreate,session:SessionDep,actor:ActorDep)->dict[str,Any]:
    require_role(actor,EDITOR_ROLES)
    link,publication=await create_delivery(session,actor=actor,project_id=project_id,data=payload)
    await append_domain_audit(session,actor=actor,module_name="comic_page_editor",action="comic.activity_delivery.created",entity_type="hq_activity_delivery_link",entity_id=link.id,details={"publication_id":str(publication.id),"targets":len(payload.targets)})
    await session.commit()
    return {"id":str(link.id),"publication_id":str(publication.id),"status":link.status}

@router.post("/activity-deliveries/{delivery_id}/publish")
async def publish_hq_activity_delivery(delivery_id:uuid.UUID,session:SessionDep,actor:ActorDep)->dict[str,Any]:
    require_role(actor,EDITOR_ROLES)
    link,publication=await publish_delivery(session,actor=actor,link_id=delivery_id)
    await append_domain_audit(session,actor=actor,module_name="comic_page_editor",action="comic.activity_delivery.published",entity_type="hq_activity_delivery_link",entity_id=link.id,details={"publication_id":str(publication.id)})
    await session.commit()
    return {"id":str(link.id),"publication_id":str(publication.id),"status":link.status,"published_at":link.published_at}

@router.get("/activity-deliveries/{delivery_id}/monitoring")
async def monitor_hq_activity_delivery(
    delivery_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    classroom_id: uuid.UUID | None = Query(default=None),
    student_id: uuid.UUID | None = Query(default=None),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        pattern="^(NOT_STARTED|STARTED|READING|ANSWERING|PAUSED|COMPLETED)$",
    ),
    idle_threshold_seconds: int | None = Query(
        default=None,
        ge=30,
        le=3600,
    ),
) -> dict[str, Any]:
    require_role(actor,EDITOR_ROLES)
    return await monitoring_summary(
        session,
        actor=actor,
        link_id=delivery_id,
        classroom_id=classroom_id,
        student_id=student_id,
        status_filter=status_filter,
        idle_threshold_seconds=idle_threshold_seconds,
    )


@router.get("/student-experience/publications/{publication_id}")
async def get_student_hq_experience(
    publication_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, STUDENT_ROLES)
    result = await experience_manifest(
        session,
        actor=actor,
        publication_id=publication_id,
    )
    return result


@router.put("/student-experience/publications/{publication_id}/state")
async def update_student_hq_experience(
    publication_id: uuid.UUID,
    payload: HQStudentExperienceStateUpdate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, STUDENT_ROLES)
    state, delivery = await save_experience_state(
        session,
        actor=actor,
        publication_id=publication_id,
        data=payload,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_page_editor",
        action="comic.student_experience.progress_saved",
        entity_type="hq_student_experience_state",
        entity_id=state.id,
        details={
            "publication_id": str(publication_id),
            "stage": state.current_stage,
            "reading_progress": state.reading_progress,
            "activity_progress": state.activity_progress,
            "answered_count": state.answered_count,
        },
    )
    await session.commit()
    return {
        "id": str(state.id),
        "current_stage": state.current_stage,
        "reading_progress": state.reading_progress,
        "activity_progress": state.activity_progress,
        "answered_count": state.answered_count,
        "combined_progress": combined_progress(
            reading_progress=state.reading_progress,
            activity_progress=state.activity_progress,
            reader_required=delivery.reader_required,
        ),
        "last_sequence": state.last_sequence,
        "completed_at": state.completed_at,
    }

@router.post("/activity-deliveries/{delivery_id}/analytics/generate")
async def generate_hq_learning_analytics(delivery_id:uuid.UUID,payload:HQLearningAnalyticsGenerate,session:SessionDep,actor:ActorDep)->dict[str,Any]:
    require_role(actor,EDITOR_ROLES)
    delivery=await session.scalar(select(models.HQActivityDeliveryLink).where(
        models.HQActivityDeliveryLink.organization_id==actor.organization_id,
        models.HQActivityDeliveryLink.id==delivery_id))
    if delivery is None:
        raise HTTPException(404,"Aplicação não encontrada.")
    snapshot=await generate_snapshot(session,actor=actor,publication_id=delivery.publication_id,
        scope_type=payload.scope_type,scope_id=payload.scope_id,period_start=payload.period_start,period_end=payload.period_end)
    await append_domain_audit(session,actor=actor,module_name="comic_page_editor",
        action="comic.learning_analytics.generated",entity_type="hq_learning_analytics_snapshot",
        entity_id=snapshot.id,details={"publication_id":str(delivery.publication_id),"scope_type":payload.scope_type})
    await session.commit()
    return {"id":str(snapshot.id),"publication_id":str(snapshot.publication_id),"metrics":snapshot.metrics,
        "skill_metrics":snapshot.skill_metrics,"page_metrics":snapshot.page_metrics,
        "activity_metrics":snapshot.activity_metrics,"correlations":snapshot.correlations,"alerts":snapshot.alerts,
        "generated_at":snapshot.generated_at}

@router.get("/activity-deliveries/{delivery_id}/analytics/latest")
async def get_latest_hq_learning_analytics(
    delivery_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    scope_type: str = "PUBLICATION",
    scope_id: uuid.UUID | None = None,
) -> dict[str, Any] | None:
    require_role(actor,EDITOR_ROLES)
    delivery=await session.scalar(select(models.HQActivityDeliveryLink).where(
        models.HQActivityDeliveryLink.organization_id==actor.organization_id,
        models.HQActivityDeliveryLink.id==delivery_id))
    if delivery is None:
        raise HTTPException(404,"Aplicação não encontrada.")
    normalized_scope = scope_type.upper()
    if normalized_scope not in {"PUBLICATION", "CLASS", "STUDENT", "ACTIVITY"}:
        raise HTTPException(status_code=422, detail="invalid analytics scope")
    if normalized_scope != "PUBLICATION" and scope_id is None:
        raise HTTPException(
            status_code=422,
            detail="scope_id is required outside PUBLICATION scope",
        )
    if normalized_scope == "PUBLICATION" and scope_id is not None:
        raise HTTPException(
            status_code=422,
            detail="scope_id must be omitted for PUBLICATION scope",
        )
    snapshot = await latest_snapshot(
        session,
        actor=actor,
        publication_id=delivery.publication_id,
        scope_type=normalized_scope,
        scope_id=scope_id,
    )
    if snapshot is None:
        return None
    return {"id":str(snapshot.id),"publication_id":str(snapshot.publication_id),"metrics":snapshot.metrics,
        "skill_metrics":snapshot.skill_metrics,"page_metrics":snapshot.page_metrics,
        "activity_metrics":snapshot.activity_metrics,"correlations":snapshot.correlations,"alerts":snapshot.alerts,
        "generated_at":snapshot.generated_at}
