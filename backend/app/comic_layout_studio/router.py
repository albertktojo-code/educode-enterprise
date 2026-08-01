from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import (
    ALLOWED_BLEND_MODES,
    evaluate_preflight,
    export_progress,
    next_z_index,
    normalize_z_order,
    page_geometry,
    snap_transform,
    validate_transform,
)
from app.services.comic_runtime import cancel_domain_job, enqueue_domain_job, runtime_job_for_domain, synchronize_simple_domain_job
from app.services.consolidated_audit import append_domain_audit

from .repositories import document_guides, document_layers
from .schemas import (
    CanvasDocumentCreate,
    CanvasDocumentRead,
    ExportJobCreate,
    ExportJobRead,
    ExportPresetCreate,
    ExportPresetRead,
    GroupCreate,
    GuideCreate,
    GuideRead,
    LayerCreate,
    LayerRead,
    LayerUpdate,
    OperationCreate,
    PreflightRequest,
    ReorderLayersRequest,
)

router = APIRouter(prefix="/comic-layout-studio", tags=["comic-layout-studio"])
SessionDep = Annotated[Any, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]
ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
EDITOR_ROLES = ADMIN_ROLES | {"TEACHER", "COORDINATOR", "PEDAGOGICAL_COORDINATOR"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    roles = {str(item).upper() for item in actor.roles}
    if not roles.intersection(allowed):
        raise HTTPException(403, "Permissao insuficiente para diagramar HQs.")


async def get_document_or_404(
    session: Any, organization_id: uuid.UUID, document_id: uuid.UUID
) -> models.HQCanvasDocument:
    document = await session.scalar(
        select(models.HQCanvasDocument).where(
            models.HQCanvasDocument.organization_id == organization_id,
            models.HQCanvasDocument.id == document_id,
        )
    )
    if not document:
        raise HTTPException(404, "Documento de diagramacao nao encontrado.")
    return document


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "16.2", "module": "comic-layout-studio"}


@router.post(
    "/documents", response_model=CanvasDocumentRead, status_code=status.HTTP_201_CREATED
)
async def create_document(
    payload: CanvasDocumentCreate, session: SessionDep, actor: ActorDep
) -> CanvasDocumentRead:
    require_role(actor, EDITOR_ROLES)
    existing = await session.scalar(
        select(models.HQCanvasDocument).where(
            models.HQCanvasDocument.organization_id == actor.organization_id,
            models.HQCanvasDocument.page_id == payload.page_id,
        )
    )
    if existing:
        raise HTTPException(409, "Esta pagina ja possui um documento de layout livre.")
    item = models.HQCanvasDocument(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/projects/{project_id}/documents", response_model=list[CanvasDocumentRead])
async def list_documents(
    project_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> list[CanvasDocumentRead]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(
        select(models.HQCanvasDocument)
        .where(
            models.HQCanvasDocument.organization_id == actor.organization_id,
            models.HQCanvasDocument.comic_project_id == project_id,
        )
        .order_by(models.HQCanvasDocument.created_at)
    )
    return list(result.scalars().all())


@router.get("/documents/{document_id}", response_model=CanvasDocumentRead)
async def get_document(
    document_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> CanvasDocumentRead:
    require_role(actor, EDITOR_ROLES)
    return await get_document_or_404(session, actor.organization_id, document_id)


@router.get("/documents/{document_id}/geometry")
async def get_geometry(
    document_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    document = await get_document_or_404(session, actor.organization_id, document_id)
    return page_geometry(
        width_mm=document.page_width,
        height_mm=document.page_height,
        bleed_mm=document.bleed_mm,
        safe_margin_mm=document.safe_margin_mm,
    )


@router.post(
    "/documents/{document_id}/layers",
    response_model=LayerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_layer(
    document_id: uuid.UUID, payload: LayerCreate, session: SessionDep, actor: ActorDep
) -> LayerRead:
    require_role(actor, EDITOR_ROLES)
    document = await get_document_or_404(session, actor.organization_id, document_id)
    if payload.blend_mode.upper() not in ALLOWED_BLEND_MODES:
        raise HTTPException(422, "Modo de mesclagem nao suportado.")
    transform = payload.transform.model_dump()
    errors = validate_transform(transform)
    if errors:
        raise HTTPException(422, {"code": "INVALID_TRANSFORM", "errors": errors})
    transform = snap_transform(
        transform, grid_size=document.grid_size, enabled=document.snap_enabled
    )
    z_values = list(
        (
            await session.execute(
                select(models.HQCanvasLayer.z_index).where(
                    models.HQCanvasLayer.organization_id == actor.organization_id,
                    models.HQCanvasLayer.document_id == document_id,
                )
            )
        ).scalars()
    )
    item = models.HQCanvasLayer(
        organization_id=actor.organization_id,
        document_id=document_id,
        source_panel_id=payload.source_panel_id,
        layer_type=payload.layer_type,
        name=payload.name,
        z_index=next_z_index(z_values),
        x=transform["x"],
        y=transform["y"],
        width=transform["width"],
        height=transform["height"],
        rotation_deg=transform.get("rotation_deg", 0),
        opacity=transform.get("opacity", 1),
        blend_mode=payload.blend_mode.upper(),
        shape=payload.shape,
        visible=payload.visible,
        locked=payload.locked,
        clip_path=payload.clip_path,
        transform_origin=payload.transform_origin,
        style=payload.style,
        content=payload.content,
        asset_reference=payload.asset_reference,
        accessibility_metadata=payload.accessibility_metadata,
    )
    session.add(item)
    document.revision_number += 1
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/documents/{document_id}/layers", response_model=list[LayerRead])
async def list_layers(
    document_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> list[LayerRead]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    return await document_layers(session, actor.organization_id, document_id)


@router.patch("/layers/{layer_id}", response_model=LayerRead)
async def update_layer(
    layer_id: uuid.UUID, payload: LayerUpdate, session: SessionDep, actor: ActorDep
) -> LayerRead:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.HQCanvasLayer).where(
            models.HQCanvasLayer.organization_id == actor.organization_id,
            models.HQCanvasLayer.id == layer_id,
        )
    )
    if not item:
        raise HTTPException(404, "Camada nao encontrada.")
    if item.locked and payload.locked is not False:
        raise HTTPException(409, "Camada bloqueada. Desbloqueie antes de editar.")
    data = payload.model_dump(exclude_unset=True)
    transform = data.pop("transform", None)
    if transform:
        document = await get_document_or_404(
            session, actor.organization_id, item.document_id
        )
        transformed = snap_transform(
            transform, grid_size=document.grid_size, enabled=document.snap_enabled
        )
        errors = validate_transform(transformed)
        if errors:
            raise HTTPException(422, {"code": "INVALID_TRANSFORM", "errors": errors})
        for key in ("x", "y", "width", "height", "rotation_deg", "opacity"):
            if key in transformed:
                setattr(item, key, transformed[key])
    if "blend_mode" in data and data["blend_mode"]:
        mode = str(data["blend_mode"]).upper()
        if mode not in ALLOWED_BLEND_MODES:
            raise HTTPException(422, "Modo de mesclagem nao suportado.")
        data["blend_mode"] = mode
    for key, value in data.items():
        setattr(item, key, value)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/layers/{layer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layer(
    layer_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> None:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.HQCanvasLayer).where(
            models.HQCanvasLayer.organization_id == actor.organization_id,
            models.HQCanvasLayer.id == layer_id,
        )
    )
    if not item:
        raise HTTPException(404, "Camada nao encontrada.")
    if item.locked:
        raise HTTPException(409, "Camada bloqueada nao pode ser excluida.")
    await session.delete(item)
    await session.commit()


@router.post("/documents/{document_id}/layers/reorder")
async def reorder_layers(
    document_id: uuid.UUID,
    payload: ReorderLayersRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    mapping = normalize_z_order([str(item) for item in payload.layer_ids])
    result = await session.execute(
        select(models.HQCanvasLayer).where(
            models.HQCanvasLayer.organization_id == actor.organization_id,
            models.HQCanvasLayer.document_id == document_id,
        )
    )
    layers = list(result.scalars().all())
    if {str(item.id) for item in layers} != set(mapping):
        raise HTTPException(422, "A lista deve conter todas as camadas do documento.")
    for item in layers:
        item.z_index = mapping[str(item.id)]
    await session.commit()
    return {"reordered": True, "z_order": mapping}


@router.post(
    "/documents/{document_id}/guides",
    response_model=GuideRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_guide(
    document_id: uuid.UUID, payload: GuideCreate, session: SessionDep, actor: ActorDep
) -> GuideRead:
    require_role(actor, EDITOR_ROLES)
    document = await get_document_or_404(session, actor.organization_id, document_id)
    maximum = document.page_width if payload.orientation.upper() == "VERTICAL" else document.page_height
    if payload.position < -document.bleed_mm or payload.position > maximum + document.bleed_mm:
        raise HTTPException(422, "Guia fora da area da pagina e sangria.")
    item = models.HQCanvasGuide(
        organization_id=actor.organization_id,
        document_id=document_id,
        orientation=payload.orientation.upper(),
        position=payload.position,
        guide_type=payload.guide_type.upper(),
        visible=payload.visible,
        locked=payload.locked,
        label=payload.label,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/documents/{document_id}/guides", response_model=list[GuideRead])
async def list_guides(
    document_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> list[GuideRead]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    return await document_guides(session, actor.organization_id, document_id)


@router.delete("/guides/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guide(
    guide_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> None:
    require_role(actor, EDITOR_ROLES)
    guide = await session.scalar(
        select(models.HQCanvasGuide).where(
            models.HQCanvasGuide.organization_id == actor.organization_id,
            models.HQCanvasGuide.id == guide_id,
        )
    )
    if not guide:
        raise HTTPException(404, "Guia nao encontrada.")
    if guide.locked:
        raise HTTPException(409, "Guia bloqueada nao pode ser excluida.")
    await session.delete(guide)
    await session.commit()


@router.post("/documents/{document_id}/groups", status_code=status.HTTP_201_CREATED)
async def create_group(
    document_id: uuid.UUID, payload: GroupCreate, session: SessionDep, actor: ActorDep
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    layer_ids = [str(item) for item in payload.layer_ids]
    layers = list(
        (
            await session.execute(
                select(models.HQCanvasLayer).where(
                    models.HQCanvasLayer.organization_id == actor.organization_id,
                    models.HQCanvasLayer.document_id == document_id,
                    models.HQCanvasLayer.id.in_(payload.layer_ids),
                )
            )
        ).scalars().all()
    )
    if len(layers) != len(layer_ids):
        raise HTTPException(422, "Uma ou mais camadas nao pertencem ao documento.")
    group = models.HQCanvasGroup(
        organization_id=actor.organization_id,
        document_id=document_id,
        name=payload.name,
        layer_ids=layer_ids,
        visible=payload.visible,
        locked=payload.locked,
        transform={},
    )
    session.add(group)
    await session.flush()
    for layer in layers:
        layer.group_id = group.id
    await session.commit()
    await session.refresh(group)
    return {"id": group.id, "name": group.name, "layer_ids": group.layer_ids}


@router.post("/documents/{document_id}/operations", status_code=status.HTTP_201_CREATED)
async def record_operation(
    document_id: uuid.UUID,
    payload: OperationCreate,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    item = models.HQCanvasOperation(
        organization_id=actor.organization_id,
        document_id=document_id,
        actor_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": item.id, "sequence": item.sequence, "applied": item.applied}


@router.post("/documents/{document_id}/undo")
async def undo_operation(
    document_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    operation = await session.scalar(
        select(models.HQCanvasOperation)
        .where(
            models.HQCanvasOperation.organization_id == actor.organization_id,
            models.HQCanvasOperation.document_id == document_id,
            models.HQCanvasOperation.applied.is_(True),
        )
        .order_by(models.HQCanvasOperation.sequence.desc())
        .limit(1)
    )
    if not operation:
        raise HTTPException(409, "Nao ha operacao para desfazer.")
    operation.applied = False
    await session.commit()
    return {
        "undone": True,
        "sequence": operation.sequence,
        "reverse_payload": operation.reverse_payload,
    }


@router.post("/documents/{document_id}/redo")
async def redo_operation(
    document_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    await get_document_or_404(session, actor.organization_id, document_id)
    operation = await session.scalar(
        select(models.HQCanvasOperation)
        .where(
            models.HQCanvasOperation.organization_id == actor.organization_id,
            models.HQCanvasOperation.document_id == document_id,
            models.HQCanvasOperation.applied.is_(False),
        )
        .order_by(models.HQCanvasOperation.sequence.asc())
        .limit(1)
    )
    if not operation:
        raise HTTPException(409, "Nao ha operacao para refazer.")
    operation.applied = True
    await session.commit()
    return {
        "redone": True,
        "sequence": operation.sequence,
        "forward_payload": operation.forward_payload,
    }


@router.post("/export-presets", response_model=ExportPresetRead, status_code=status.HTTP_201_CREATED)
async def create_export_preset(
    payload: ExportPresetCreate, session: SessionDep, actor: ActorDep
) -> ExportPresetRead:
    require_role(actor, ADMIN_ROLES)
    item = models.HQExportPreset(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        status="DRAFT",
        is_system=False,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/export-presets", response_model=list[ExportPresetRead])
async def list_export_presets(session: SessionDep, actor: ActorDep) -> list[ExportPresetRead]:
    require_role(actor, EDITOR_ROLES)
    result = await session.execute(
        select(models.HQExportPreset)
        .where(
            (models.HQExportPreset.organization_id == actor.organization_id)
            | (models.HQExportPreset.is_system.is_(True))
        )
        .order_by(models.HQExportPreset.output_format, models.HQExportPreset.name)
    )
    return list(result.scalars().all())


@router.post("/documents/{document_id}/preflight")
async def run_preflight(
    document_id: uuid.UUID,
    payload: PreflightRequest,
    session: SessionDep,
    actor: ActorDep,
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    document = await get_document_or_404(session, actor.organization_id, document_id)
    layers = await document_layers(session, actor.organization_id, document_id)
    findings = evaluate_preflight(
        {
            "page_width": document.page_width,
            "page_height": document.page_height,
            "bleed_mm": document.bleed_mm,
            "safe_margin_mm": document.safe_margin_mm,
            "dpi": document.dpi,
        },
        [
            {
                "id": str(item.id),
                "layer_type": item.layer_type,
                "z_index": item.z_index,
                "x": item.x,
                "y": item.y,
                "width": item.width,
                "height": item.height,
                "rotation_deg": item.rotation_deg,
                "opacity": item.opacity,
                "visible": item.visible,
                "style": item.style,
                "content": item.content,
                "accessibility_metadata": item.accessibility_metadata,
            }
            for item in layers
        ],
        output_format=payload.output_format,
        minimum_dpi=payload.minimum_dpi,
    )
    if payload.persist_findings:
        await session.execute(
            delete(models.HQPreflightFinding).where(
                models.HQPreflightFinding.organization_id == actor.organization_id,
                models.HQPreflightFinding.document_id == document_id,
                models.HQPreflightFinding.export_job_id.is_(None),
            )
        )
        for finding in findings:
            resource_id = finding.get("resource_id")
            session.add(
                models.HQPreflightFinding(
                    organization_id=actor.organization_id,
                    document_id=document_id,
                    severity=finding.get("severity", "INFO"),
                    code=finding.get("code", "UNKNOWN"),
                    message=finding.get("message", ""),
                    resource_type=finding.get("resource_type", "DOCUMENT"),
                    resource_id=uuid.UUID(resource_id) if resource_id else None,
                    details=finding.get("details", {}),
                )
            )
        await session.commit()
    summary = {
        "errors": sum(1 for item in findings if item.get("severity") == "ERROR"),
        "warnings": sum(1 for item in findings if item.get("severity") == "WARNING"),
        "info": sum(1 for item in findings if item.get("severity") == "INFO"),
    }
    return {"valid": summary["errors"] == 0, "summary": summary, "findings": findings}


@router.post(
    "/documents/{document_id}/export-jobs",
    response_model=ExportJobRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_export_job(
    document_id: uuid.UUID,
    payload: ExportJobCreate,
    session: SessionDep,
    actor: ActorDep,
) -> ExportJobRead:
    require_role(actor, EDITOR_ROLES)
    document = await get_document_or_404(session, actor.organization_id, document_id)
    warnings: list[dict[str, Any]] = []
    if payload.run_preflight:
        layers = await document_layers(session, actor.organization_id, document_id)
        findings = evaluate_preflight(
            {
                "page_width": document.page_width,
                "page_height": document.page_height,
                "bleed_mm": document.bleed_mm,
                "safe_margin_mm": document.safe_margin_mm,
                "dpi": document.dpi,
            },
            [
                {
                    "id": str(item.id),
                    "layer_type": item.layer_type,
                    "z_index": item.z_index,
                    "x": item.x,
                    "y": item.y,
                    "width": item.width,
                    "height": item.height,
                    "rotation_deg": item.rotation_deg,
                    "opacity": item.opacity,
                    "visible": item.visible,
                    "style": item.style,
                    "content": item.content,
                    "accessibility_metadata": item.accessibility_metadata,
                }
                for item in layers
            ],
            output_format=payload.output_format,
        )
        errors = [item for item in findings if item.get("severity") == "ERROR"]
        warnings = [item for item in findings if item.get("severity") != "ERROR"]
        if errors:
            raise HTTPException(
                422,
                {
                    "code": "PREFLIGHT_FAILED",
                    "errors": errors,
                    "warnings": warnings,
                },
            )
        if warnings and not payload.allow_warnings:
            raise HTTPException(409, {"code": "PREFLIGHT_WARNINGS", "warnings": warnings})
    item = models.HQExportJob(
        organization_id=actor.organization_id,
        document_id=document_id,
        preset_id=payload.preset_id,
        requested_by_user_id=actor.user_id,
        status="QUEUED",
        progress_percent=export_progress("QUEUED"),
        configuration={
            "output_format": payload.output_format,
            "run_preflight": payload.run_preflight,
            **payload.configuration,
        },
        warnings=warnings,
        started_at=datetime.now(UTC),
    )
    session.add(item)
    await session.flush()
    try:
        runtime = await enqueue_domain_job(
            session,
            actor=actor,
            module_name="comic_layout_studio",
            entity_type="hq_export_job",
            entity_id=item.id,
            job_type="file_export",
            total_steps=4,
            input_snapshot={
                "domain_job_id": str(item.id),
                "document_id": str(document_id),
                "configuration": item.configuration,
                "steps": [
                    "Validando pre-flight",
                    "Renderizando paginas",
                    "Empacotando arquivo",
                    "Registrando artefato",
                ],
            },
            priority=60,
        )
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(422, str(exc)) from exc
    item.configuration = {**item.configuration, "_runtime_job_id": str(runtime.id)}
    document.status = "EXPORTING"
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_layout_studio",
        action="comic.export.queued",
        entity_type="hq_export_job",
        entity_id=item.id,
        details={"runtime_job_id": str(runtime.id), "document_id": str(document_id)},
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/export-jobs/{job_id}", response_model=ExportJobRead)
async def get_export_job(
    job_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> ExportJobRead:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.HQExportJob).where(
            models.HQExportJob.organization_id == actor.organization_id,
            models.HQExportJob.id == job_id,
        )
    )
    if not item:
        raise HTTPException(404, "Exportacao nao encontrada.")
    runtime = await runtime_job_for_domain(
        session,
        organization_id=actor.organization_id,
        module_name="comic_layout_studio",
        entity_type="hq_export_job",
        entity_id=item.id,
    )
    if runtime:
        synchronize_simple_domain_job(item, runtime)
        if runtime.status == "completed":
            item.output_reference = item.output_reference or f"job://{runtime.id}"
    else:
        item.progress_percent = export_progress(item.status)
    await session.commit()
    return item


@router.post("/export-jobs/{job_id}/cancel")
async def cancel_export_job(
    job_id: uuid.UUID, session: SessionDep, actor: ActorDep
) -> dict[str, Any]:
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.HQExportJob).where(
            models.HQExportJob.organization_id == actor.organization_id,
            models.HQExportJob.id == job_id,
        )
    )
    if not item:
        raise HTTPException(404, "Exportacao nao encontrada.")
    if item.status in {"COMPLETED", "COMPLETED_WITH_WARNINGS", "FAILED", "CANCELLED"}:
        raise HTTPException(409, "A exportacao ja foi finalizada.")
    item.status = "CANCELLED"
    item.progress_percent = 100
    item.finished_at = datetime.now(UTC)
    runtime = await cancel_domain_job(
        session,
        organization_id=actor.organization_id,
        module_name="comic_layout_studio",
        entity_type="hq_export_job",
        entity_id=item.id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_layout_studio",
        action="comic.export.cancelled",
        entity_type="hq_export_job",
        entity_id=item.id,
        details={"runtime_job_id": str(runtime.id) if runtime else None},
    )
    await session.commit()
    return {"cancelled": True, "job_id": job_id}
