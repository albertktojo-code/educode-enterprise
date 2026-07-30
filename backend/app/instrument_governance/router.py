from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment_hub import models as hub_models

from . import audit, models, repositories
from .compat import ActorContext, get_project_session, resolve_actor_context
from .enums import ImportStatus, InterpretationStatus, LicenseStatus, NormStatus, ProtocolStatus
from .policies import (
    LearnerProfile,
    choose_norm_group,
    lookup_norm_entry,
    roman_gonzalez_structural_template,
    safe_descriptive_interpretation,
    validate_import_manifest,
    validate_license_for_use,
)
from .schemas import (
    ImportBatchCreate,
    ImportBatchRead,
    InterpretationCreate,
    InterpretationDecision,
    InterpretationRead,
    LicenseCreate,
    LicenseDecision,
    LicenseRead,
    MappingCreate,
    MappingRead,
    NormGroupCreate,
    NormGroupRead,
    ProtocolCreate,
    ProtocolRead,
    ScoreSimulationRequest,
    ScoreSimulationResult,
)

router = APIRouter(prefix="/instrument-governance", tags=["instrument-governance"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ADMIN_ROLES = {"ADMIN", "SUPER_ADMIN", "PLATFORM_ADMIN", "ORG_ADMIN"}
STAFF_ROLES = ADMIN_ROLES | {"TEACHER", "PROFESSOR", "COORDINATOR", "ASSESSMENT_MANAGER"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    if not actor.roles.intersection(allowed):
        raise HTTPException(status_code=403, detail={"code": "INSTRUMENT_GOVERNANCE_ACCESS_DENIED"})


async def ensure_instrument(session: AsyncSession, actor: ActorContext, instrument_id: uuid.UUID) -> hub_models.ExternalInstrument:
    entity = await repositories.get_for_organization(
        session, hub_models.ExternalInstrument, actor.organization_id, instrument_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "EXTERNAL_INSTRUMENT_NOT_FOUND"})
    return entity


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "15.3", "module": "instrument-governance"}


@router.get("/templates/roman-gonzalez")
async def roman_gonzalez_template(actor: ActorDep) -> dict:
    require_role(actor, STAFF_ROLES)
    return roman_gonzalez_structural_template()


@router.post("/licenses", response_model=LicenseRead, status_code=201)
async def create_license(payload: LicenseCreate, session: SessionDep, actor: ActorDep) -> models.InstrumentLicense:
    require_role(actor, ADMIN_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    latest = await session.scalar(
        select(func.max(models.InstrumentLicense.version)).where(
            models.InstrumentLicense.organization_id == actor.organization_id,
            models.InstrumentLicense.instrument_id == payload.instrument_id,
        )
    )
    entity = models.InstrumentLicense(
        organization_id=actor.organization_id,
        version=int(latest or 0) + 1,
        status=LicenseStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    audit.record("instrument.license_created", license_id=str(entity.id))
    return entity


@router.get("/licenses", response_model=list[LicenseRead])
async def list_licenses(
    session: SessionDep,
    actor: ActorDep,
    instrument_id: uuid.UUID | None = None,
    status: LicenseStatus | None = None,
) -> list[models.InstrumentLicense]:
    require_role(actor, STAFF_ROLES)
    query = select(models.InstrumentLicense).where(models.InstrumentLicense.organization_id == actor.organization_id)
    if instrument_id:
        query = query.where(models.InstrumentLicense.instrument_id == instrument_id)
    if status:
        query = query.where(models.InstrumentLicense.status == status.value)
    result = await session.execute(query.order_by(models.InstrumentLicense.created_at.desc()))
    return list(result.scalars().all())


@router.post("/licenses/{license_id}/decision", response_model=LicenseRead)
async def decide_license(
    license_id: uuid.UUID,
    payload: LicenseDecision,
    session: SessionDep,
    actor: ActorDep,
) -> models.InstrumentLicense:
    require_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(session, models.InstrumentLicense, actor.organization_id, license_id)
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "INSTRUMENT_LICENSE_NOT_FOUND"})
    entity.status = LicenseStatus.ACTIVE.value if payload.approve else LicenseStatus.REVOKED.value
    entity.approved_by_user_id = actor.user_id
    entity.approved_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    audit.record("instrument.license_decided", license_id=str(entity.id), approved=payload.approve)
    return entity


@router.post("/protocols", response_model=ProtocolRead, status_code=201)
async def create_protocol(payload: ProtocolCreate, session: SessionDep, actor: ActorDep) -> models.AdministrationProtocol:
    require_role(actor, STAFF_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    entity = models.AdministrationProtocol(
        organization_id=actor.organization_id,
        status=ProtocolStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    audit.record("instrument.protocol_created", protocol_id=str(entity.id))
    return entity


@router.post("/protocols/{protocol_id}/publish", response_model=ProtocolRead)
async def publish_protocol(protocol_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> models.AdministrationProtocol:
    require_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(
        session, models.AdministrationProtocol, actor.organization_id, protocol_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "INSTRUMENT_PROTOCOL_NOT_FOUND"})
    entity.status = ProtocolStatus.PUBLISHED.value
    entity.published_by_user_id = actor.user_id
    entity.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/norm-groups", response_model=NormGroupRead, status_code=201)
async def create_norm_group(payload: NormGroupCreate, session: SessionDep, actor: ActorDep) -> models.NormGroup:
    require_role(actor, ADMIN_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    data = payload.model_dump(exclude={"entries"})
    entity = models.NormGroup(
        organization_id=actor.organization_id,
        status=NormStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
        **data,
    )
    await repositories.add_and_refresh(session, entity)
    for entry in payload.entries:
        session.add(
            models.NormTableEntry(
                organization_id=actor.organization_id,
                norm_group_id=entity.id,
                **entry.model_dump(),
            )
        )
    await session.commit()
    await session.refresh(entity)
    audit.record("instrument.norm_group_created", norm_group_id=str(entity.id))
    return entity


@router.post("/norm-groups/{norm_group_id}/publish", response_model=NormGroupRead)
async def publish_norm_group(norm_group_id: uuid.UUID, session: SessionDep, actor: ActorDep) -> models.NormGroup:
    require_role(actor, ADMIN_ROLES)
    entity = await repositories.get_for_organization(session, models.NormGroup, actor.organization_id, norm_group_id)
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "NORM_GROUP_NOT_FOUND"})
    license_result = await session.execute(
        select(models.InstrumentLicense).where(
            models.InstrumentLicense.organization_id == actor.organization_id,
            models.InstrumentLicense.instrument_id == entity.instrument_id,
            models.InstrumentLicense.status == LicenseStatus.ACTIVE.value,
        ).order_by(models.InstrumentLicense.version.desc())
    )
    license_entity = license_result.scalars().first()
    if not license_entity:
        raise HTTPException(status_code=409, detail={"code": "ACTIVE_LICENSE_REQUIRED"})
    valid, reason = validate_license_for_use(
        status=license_entity.status,
        valid_from=license_entity.valid_from,
        valid_until=license_entity.valid_until,
        rights_scope=license_entity.rights_scope,
        requested_action="SCORE",
    )
    if not valid:
        raise HTTPException(status_code=409, detail={"code": reason})
    entity.status = NormStatus.PUBLISHED.value
    entity.published_by_user_id = actor.user_id
    entity.published_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/mappings", response_model=MappingRead, status_code=201)
async def create_mapping(payload: MappingCreate, session: SessionDep, actor: ActorDep) -> models.DimensionFrameworkMapping:
    require_role(actor, STAFF_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    dimension = await repositories.get_for_organization(
        session, hub_models.InstrumentDimension, actor.organization_id, payload.dimension_id
    )
    if not dimension or dimension.instrument_id != payload.instrument_id:
        raise HTTPException(status_code=404, detail={"code": "INSTRUMENT_DIMENSION_NOT_FOUND"})
    entity = models.DimensionFrameworkMapping(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(mode="json"),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/imports", response_model=ImportBatchRead, status_code=201)
async def create_import(payload: ImportBatchCreate, session: SessionDep, actor: ActorDep) -> models.InstrumentImportBatch:
    require_role(actor, ADMIN_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    license_entity = None
    if payload.declared_license_id:
        license_entity = await repositories.get_for_organization(
            session, models.InstrumentLicense, actor.organization_id, payload.declared_license_id
        )
    has_active_license = False
    if license_entity and license_entity.instrument_id == payload.instrument_id:
        has_active_license, _ = validate_license_for_use(
            status=license_entity.status,
            valid_from=license_entity.valid_from,
            valid_until=license_entity.valid_until,
            rights_scope=license_entity.rights_scope,
            requested_action="IMPORT",
        )
    manifest = payload.manifest.model_dump()
    errors = validate_import_manifest(manifest, has_active_license=has_active_license)
    entity = models.InstrumentImportBatch(
        organization_id=actor.organization_id,
        instrument_id=payload.instrument_id,
        filename=payload.filename,
        file_format=payload.file_format,
        checksum_sha256=payload.checksum_sha256.lower(),
        declared_license_id=payload.declared_license_id,
        contains_protected_items=payload.manifest.contains_protected_items,
        manifest=manifest,
        validation_errors=errors,
        status=ImportStatus.REJECTED.value if errors else ImportStatus.VALID.value,
        created_by_user_id=actor.user_id,
        validated_by_user_id=actor.user_id,
        validated_at=datetime.now(UTC),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    audit.record("instrument.import_validated", import_id=str(entity.id), errors=len(errors))
    return entity


@router.post("/score-simulations", response_model=ScoreSimulationResult)
async def simulate_score(payload: ScoreSimulationRequest, session: SessionDep, actor: ActorDep) -> ScoreSimulationResult:
    require_role(actor, STAFF_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    groups_result = await session.execute(
        select(models.NormGroup).where(
            models.NormGroup.organization_id == actor.organization_id,
            models.NormGroup.instrument_id == payload.instrument_id,
            models.NormGroup.status == NormStatus.PUBLISHED.value,
        )
    )
    groups = list(groups_result.scalars().all())
    group_payloads = [
        {
            "id": item.id,
            "status": item.status,
            "locale": item.locale,
            "age_min": item.age_min,
            "age_max": item.age_max,
            "school_year_min": item.school_year_min,
            "school_year_max": item.school_year_max,
            "population_filters": item.population_filters,
            "sample_size": item.sample_size,
        }
        for item in groups
    ]
    selected = choose_norm_group(
        group_payloads,
        LearnerProfile(
            locale=payload.profile.locale,
            age=payload.profile.age,
            school_year=payload.profile.school_year,
            attributes=payload.profile.attributes,
        ),
    )
    warnings: list[str] = []
    dimensions = []
    if not selected:
        warnings.append("Nenhum grupo normativo compativel foi localizado.")
        for code, raw in payload.raw_scores.items():
            dimensions.append(
                {
                    "dimension_code": code,
                    "raw_score": raw,
                    "standardized_score": None,
                    "percentile": None,
                    "classification": "SEM_NORMA_COMPATIVEL",
                    "interpretation": safe_descriptive_interpretation(
                        dimension_code=code,
                        classification="SEM_NORMA_COMPATIVEL",
                        percentile=None,
                        source="none",
                    ),
                }
            )
        return ScoreSimulationResult(norm_group_id=None, dimensions=dimensions, warnings=warnings)
    entries_result = await session.execute(
        select(models.NormTableEntry).where(
            models.NormTableEntry.organization_id == actor.organization_id,
            models.NormTableEntry.norm_group_id == selected["id"],
        )
    )
    entries = [
        {
            "dimension_code": item.dimension_code,
            "raw_min": item.raw_min,
            "raw_max": item.raw_max,
            "standardized_score": item.standardized_score,
            "percentile": item.percentile,
            "classification": item.classification,
            "interpretation": item.interpretation,
        }
        for item in entries_result.scalars().all()
    ]
    for code, raw in payload.raw_scores.items():
        entry = lookup_norm_entry(entries, dimension_code=code, raw_score=raw)
        if entry is None:
            warnings.append(f"Faixa normativa ausente para {code}: {raw}.")
            classification = "FORA_DA_TABELA"
            standardized = percentile = None
            interpretation = safe_descriptive_interpretation(
                dimension_code=code, classification=classification, percentile=None, source="norm_table"
            )
        else:
            classification = str(entry["classification"])
            standardized = entry.get("standardized_score")
            percentile = entry.get("percentile")
            interpretation = {
                **safe_descriptive_interpretation(
                    dimension_code=code,
                    classification=classification,
                    percentile=percentile,
                    source="norm_table",
                ),
                "authorized_note": entry.get("interpretation") or {},
            }
        dimensions.append(
            {
                "dimension_code": code,
                "raw_score": raw,
                "standardized_score": standardized,
                "percentile": percentile,
                "classification": classification,
                "interpretation": interpretation,
            }
        )
    return ScoreSimulationResult(norm_group_id=selected["id"], dimensions=dimensions, warnings=warnings)


@router.post("/interpretations", response_model=InterpretationRead, status_code=201)
async def create_interpretation(
    payload: InterpretationCreate, session: SessionDep, actor: ActorDep
) -> models.InstrumentResultInterpretation:
    require_role(actor, STAFF_ROLES)
    await ensure_instrument(session, actor, payload.instrument_id)
    attempt = await repositories.get_for_organization(
        session, hub_models.AssessmentAttempt, actor.organization_id, payload.attempt_id
    )
    if not attempt or attempt.external_instrument_id != payload.instrument_id:
        raise HTTPException(status_code=404, detail={"code": "INSTRUMENT_ATTEMPT_NOT_FOUND"})
    entity = models.InstrumentResultInterpretation(
        organization_id=actor.organization_id,
        status=InterpretationStatus.REQUIRES_REVIEW.value,
        requires_human_review=True,
        calculated_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    await repositories.add_and_refresh(session, entity)
    await session.commit()
    return entity


@router.post("/interpretations/{interpretation_id}/decision", response_model=InterpretationRead)
async def decide_interpretation(
    interpretation_id: uuid.UUID,
    payload: InterpretationDecision,
    session: SessionDep,
    actor: ActorDep,
) -> models.InstrumentResultInterpretation:
    require_role(actor, STAFF_ROLES)
    entity = await repositories.get_for_organization(
        session, models.InstrumentResultInterpretation, actor.organization_id, interpretation_id
    )
    if not entity:
        raise HTTPException(status_code=404, detail={"code": "INSTRUMENT_INTERPRETATION_NOT_FOUND"})
    entity.status = (
        InterpretationStatus.VALIDATED.value if payload.approved else InterpretationStatus.INVALIDATED.value
    )
    entity.requires_human_review = False
    entity.validated_by_user_id = actor.user_id
    entity.validated_at = datetime.now(UTC)
    entity.descriptive_interpretation = {
        **entity.descriptive_interpretation,
        "review_justification": payload.justification,
    }
    await session.commit()
    await session.refresh(entity)
    return entity


@router.get("/dashboard")
async def dashboard(session: SessionDep, actor: ActorDep) -> dict[str, int]:
    require_role(actor, STAFF_ROLES)
    counters = {}
    for key, model in (
        ("licenses", models.InstrumentLicense),
        ("protocols", models.AdministrationProtocol),
        ("norm_groups", models.NormGroup),
        ("imports", models.InstrumentImportBatch),
        ("interpretations", models.InstrumentResultInterpretation),
    ):
        counters[key] = int(
            await session.scalar(
                select(func.count(model.id)).where(model.organization_id == actor.organization_id)
            )
            or 0
        )
    return counters
