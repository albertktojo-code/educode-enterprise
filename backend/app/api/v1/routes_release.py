from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.operations import BackgroundJob, WorkerHeartbeat
from app.models.platform import BackupRun, DeploymentRelease
from app.models.release import (
    DeploymentApproval,
    DeploymentStep,
    MaintenanceWindow,
    RecoveryObjective,
    ReleaseArtifact,
    ReleaseValidationRun,
    RestoreEntityJob,
    SecretRotationRecord,
    WorkerDrainEvent,
)
from app.schemas.platform import DeploymentCreate, DeploymentRead
from app.schemas.release import (
    DeploymentApprovalRead,
    DeploymentApprovalWrite,
    DeploymentStepRead,
    DeploymentStepUpdate,
    MaintenanceStatusUpdate,
    MaintenanceWindowRead,
    MaintenanceWindowWrite,
    MigrationValidationWrite,
    RecoveryObjectiveRead,
    RecoveryObjectiveWrite,
    ReleaseArtifactRead,
    ReleaseArtifactWrite,
    ReleaseReadiness,
    ReleaseValidationRead,
    RestoreEntityRead,
    RestoreEntityWrite,
    SecretInventoryItem,
    SecretRotationRead,
    SecretRotationWrite,
    WorkerDrainRead,
    WorkerDrainWrite,
)
from app.services.platform import append_audit_event, current_migration
from app.services.operations import get_redis
from redis.exceptions import RedisError
from app.services.release import (
    configuration_release_warnings,
    ensure_release_steps,
    release_readiness,
    scan_migration_sql,
    selective_restore_plan,
    sha256_text,
    utcnow,
    validate_revision_id,
)

router = APIRouter(prefix="/release-management", tags=["release-recovery"])
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def require_platform_operator(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Operação exclusiva do operador global")


def request_meta(request: Request) -> tuple[str, str]:
    request_id = getattr(request.state, "request_id", request.headers.get("x-request-id", ""))
    ip = request.client.host if request.client else ""
    return request_id, ip


async def publish_maintenance_mode(mode: str | None, settings: Settings) -> None:
    redis = get_redis()
    try:
        key = f"{settings.job_queue_prefix}:maintenance:mode"
        if mode is None or mode == "available":
            await redis.delete(key)
        else:
            await redis.set(key, mode)
    except RedisError:
        pass
    finally:
        await redis.aclose()


async def get_release(session: AsyncSession, release_id: UUID, organization_id: UUID) -> DeploymentRelease:
    release = await session.get(DeploymentRelease, release_id)
    if release is None or release.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Release não encontrada")
    return release


@router.get("/releases", response_model=list[DeploymentRead])
async def list_releases(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[DeploymentRelease]:
    return list((await session.scalars(select(DeploymentRelease).where(DeploymentRelease.organization_id == org_id(membership)).order_by(DeploymentRelease.created_at.desc()).limit(100))).all())


@router.post("/releases", response_model=DeploymentRead)
async def create_release(
    data: DeploymentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DeploymentRelease:
    release = DeploymentRelease(
        organization_id=org_id(membership),
        version=data.version,
        build_identifier=data.build_identifier,
        commit_sha=data.commit_sha,
        environment=settings.environment,
        migration_revision=await current_migration(session),
        status="planned",
        release_notes=data.release_notes,
        deployed_by_user_id=user.id,
    )
    session.add(release)
    await session.flush()
    await ensure_release_steps(session, release)
    for stage in ("technical", "security", "business", "production"):
        session.add(DeploymentApproval(organization_id=release.organization_id, release_id=release.id, approval_stage=stage, requested_by_user_id=user.id, status="pending"))
    request_id, ip = request_meta(request)
    await append_audit_event(session, organization_id=release.organization_id, user_id=user.id, module_name="release", action="release.created", entity_type="deployment_release", entity_id=release.id, request_id=request_id, ip_address=ip, details={"version": release.version, "environment": release.environment})
    await session.commit()
    await session.refresh(release)
    return release


@router.get("/releases/{release_id}/readiness", response_model=ReleaseReadiness)
async def get_readiness(
    release_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> ReleaseReadiness:
    release = await get_release(session, release_id, org_id(membership))
    return ReleaseReadiness(**(await release_readiness(session, release)))


@router.get("/releases/{release_id}/steps", response_model=list[DeploymentStepRead])
async def list_steps(release_id: UUID, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    release = await get_release(session, release_id, org_id(membership))
    return await ensure_release_steps(session, release)


@router.patch("/releases/{release_id}/steps/{step_id}", response_model=DeploymentStepRead)
async def update_step(release_id: UUID, step_id: UUID, data: DeploymentStepUpdate, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    await get_release(session, release_id, org_id(membership))
    step = await session.get(DeploymentStep, step_id)
    if step is None or step.release_id != release_id:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    step.status = data.status
    step.details = data.details
    if data.status == "running":
        step.started_at = utcnow()
    if data.status in {"completed", "failed", "skipped"}:
        step.completed_at = utcnow()
    await session.commit(); await session.refresh(step)
    return step


@router.post("/releases/{release_id}/artifacts", response_model=ReleaseArtifactRead)
async def create_artifact(release_id: UUID, data: ReleaseArtifactWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    release = await get_release(session, release_id, org_id(membership))
    artifact = ReleaseArtifact(organization_id=release.organization_id, release_id=release.id, **data.model_dump())
    session.add(artifact); await session.commit(); await session.refresh(artifact)
    return artifact


@router.get("/releases/{release_id}/artifacts", response_model=list[ReleaseArtifactRead])
async def list_artifacts(release_id: UUID, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    release = await get_release(session, release_id, org_id(membership))
    return list((await session.scalars(select(ReleaseArtifact).where(ReleaseArtifact.release_id == release.id).order_by(ReleaseArtifact.created_at))).all())


@router.post("/releases/{release_id}/validate-migration", response_model=ReleaseValidationRead)
async def validate_migration(release_id: UUID, data: MigrationValidationWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    release = await get_release(session, release_id, org_id(membership))
    revision_problems = validate_revision_id(data.revision)
    scan = scan_migration_sql(data.sql)
    blockers = [{"code": "revision", "message": item} for item in revision_problems]
    blockers.extend({"code": item, "message": f"Operação destrutiva detectada: {item}"} for item in scan["destructive_operations"])
    run = ReleaseValidationRun(organization_id=release.organization_id, release_id=release.id, validation_type="migration", status="failed" if blockers else "passed", checks={"revision": data.revision, **scan}, blockers=blockers, warnings=[], summary={"safe": not blockers}, started_at=utcnow(), completed_at=utcnow())
    session.add(run); await session.commit(); await session.refresh(run)
    return run


@router.post("/releases/{release_id}/approvals", response_model=DeploymentApprovalRead)
async def decide_approval(release_id: UUID, data: DeploymentApprovalWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)):
    release = await get_release(session, release_id, org_id(membership))
    approval = await session.scalar(select(DeploymentApproval).where(DeploymentApproval.release_id == release.id, DeploymentApproval.approval_stage == data.approval_stage))
    if approval is None:
        approval = DeploymentApproval(organization_id=release.organization_id, release_id=release.id, approval_stage=data.approval_stage, requested_by_user_id=user.id)
        session.add(approval)
    approval.status = data.decision
    approval.decided_by_user_id = user.id
    approval.decision_notes = data.notes
    approval.decided_at = utcnow()
    await session.commit(); await session.refresh(approval)
    return approval


@router.get("/recovery-objectives", response_model=list[RecoveryObjectiveRead])
async def list_recovery_objectives(session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    return list((await session.scalars(select(RecoveryObjective).where(RecoveryObjective.organization_id == org_id(membership)).order_by(RecoveryObjective.environment, RecoveryObjective.service_name))).all())


@router.put("/recovery-objectives", response_model=RecoveryObjectiveRead)
async def upsert_recovery_objective(data: RecoveryObjectiveWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)):
    item = await session.scalar(select(RecoveryObjective).where(RecoveryObjective.organization_id == org_id(membership), RecoveryObjective.environment == data.environment, RecoveryObjective.service_name == data.service_name))
    if item is None:
        item = RecoveryObjective(organization_id=org_id(membership), updated_by_user_id=user.id, **data.model_dump())
        session.add(item)
    else:
        for key, value in data.model_dump().items(): setattr(item, key, value)
        item.updated_by_user_id = user.id
    await session.commit(); await session.refresh(item)
    return item


@router.post("/selective-restores/preview", response_model=RestoreEntityRead)
async def preview_selective_restore(data: RestoreEntityWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)):
    backup = await session.get(BackupRun, data.backup_run_id)
    if backup is None or backup.organization_id != org_id(membership) or backup.status != "completed":
        raise HTTPException(status_code=422, detail="Backup concluído não encontrado")
    plan = selective_restore_plan(data.entity_type, str(data.entity_id) if data.entity_id else None, data.restore_mode)
    item = RestoreEntityJob(organization_id=org_id(membership), backup_run_id=backup.id, requested_by_user_id=user.id, entity_type=data.entity_type, entity_id=data.entity_id, restore_mode=data.restore_mode, status="preview_ready", dependency_plan=plan, impact_preview={"will_overwrite": data.restore_mode == "replace", "requires_manual_confirmation": True})
    session.add(item); await session.commit(); await session.refresh(item)
    return item


@router.get("/maintenance", response_model=list[MaintenanceWindowRead])
async def list_maintenance(session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))):
    return list((await session.scalars(select(MaintenanceWindow).where((MaintenanceWindow.organization_id == org_id(membership)) | (MaintenanceWindow.organization_id.is_(None))).order_by(MaintenanceWindow.starts_at.desc()).limit(100))).all())


@router.post("/maintenance", response_model=MaintenanceWindowRead)
async def create_maintenance(data: MaintenanceWindowWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user), settings: Settings = Depends(get_settings)):
    item = MaintenanceWindow(organization_id=org_id(membership), created_by_user_id=user.id, **data.model_dump())
    if item.starts_at <= utcnow() < item.ends_at:
        item.status = "active"
        item.activated_at = utcnow()
        await publish_maintenance_mode(item.mode, settings)
    session.add(item); await session.commit(); await session.refresh(item)
    return item


@router.patch("/maintenance/{window_id}", response_model=MaintenanceWindowRead)
async def update_maintenance(window_id: UUID, data: MaintenanceStatusUpdate, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), settings: Settings = Depends(get_settings)):
    item = await session.get(MaintenanceWindow, window_id)
    if item is None or item.organization_id not in {None, org_id(membership)}:
        raise HTTPException(status_code=404, detail="Janela não encontrada")
    item.status = data.status
    if data.status == "active":
        item.activated_at = utcnow()
        await publish_maintenance_mode(item.mode, settings)
    if data.status in {"completed", "cancelled"}:
        item.completed_at = utcnow()
        await publish_maintenance_mode("available", settings)
    await session.commit(); await session.refresh(item)
    return item


@router.post("/workers/drain", response_model=WorkerDrainRead)
async def drain_workers(data: WorkerDrainWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)):
    require_platform_operator(user)
    conditions = [BackgroundJob.status.in_(["processing", "waiting_provider", "validating"])]
    if data.queue_name != "all": conditions.append(BackgroundJob.queue_name == data.queue_name)
    active = int(await session.scalar(select(func.count(BackgroundJob.id)).where(*conditions)) or 0)
    event = WorkerDrainEvent(organization_id=org_id(membership), release_id=data.release_id, queue_name=data.queue_name, requested_by_user_id=user.id, action=data.action, status="completed", active_jobs_at_request=active, timeout_seconds=data.timeout_seconds, details={"instruction": "workers finish current job and stop consuming" if data.action == "drain" else "workers may consume jobs", "active_jobs": active}, completed_at=utcnow())
    session.add(event)
    heartbeats = list((await session.scalars(select(WorkerHeartbeat))).all())
    for heartbeat in heartbeats:
        if data.queue_name == "all" or heartbeat.queue_name == data.queue_name:
            heartbeat.status = "draining" if data.action == "drain" else "idle"
    await session.commit(); await session.refresh(event)
    return event


@router.get("/secrets", response_model=list[SecretInventoryItem])
async def secret_inventory(settings: Settings = Depends(get_settings), _: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)):
    require_platform_operator(user)
    keys = ["JWT_SECRET_KEY", "POSTGRES_PASSWORD", "EDUCODE_AI_API_KEY", "GRAFANA_ADMIN_PASSWORD", "OBSERVABILITY_METRICS_TOKEN"]
    output = []
    for key in keys:
        value = os.getenv(key, "")
        output.append(SecretInventoryItem(secret_key=key, configured=bool(value), provider_type=settings.secret_provider, fingerprint=hashlib.sha256(value.encode()).hexdigest()[:12] if value else "", required_in_production=key in {"JWT_SECRET_KEY", "POSTGRES_PASSWORD"}))
    return output


@router.post("/secrets/rotations", response_model=SecretRotationRead)
async def register_secret_rotation(data: SecretRotationWrite, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)):
    require_platform_operator(user)
    current = os.getenv(data.secret_key, "")
    record = SecretRotationRecord(organization_id=org_id(membership), environment=data.environment, secret_key=data.secret_key, provider_type=data.provider_type, status="recorded", rotated_by_user_id=user.id, reason=data.reason, fingerprint_before=sha256_text(current)[:16] if current else "", fingerprint_after="external-change-required", next_rotation_at=data.next_rotation_at, rotated_at=utcnow())
    session.add(record); await session.commit(); await session.refresh(record)
    return record


@router.get("/preflight", response_model=dict)
async def advanced_preflight(settings: Settings = Depends(get_settings), session: AsyncSession = Depends(get_db_session), _: Membership = Depends(require_roles(*ADMIN_ROLES))):
    warnings = configuration_release_warnings(settings)
    current = await current_migration(session)
    revision_problems = validate_revision_id(current)
    return {"ready": not warnings and not revision_problems, "environment": settings.environment, "strategy": settings.deployment_strategy, "migration_revision": current, "warnings": warnings, "blockers": revision_problems, "backup_required": settings.require_release_backup, "approval_required": settings.require_release_approval}
