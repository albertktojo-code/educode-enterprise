from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.platform import (
    BackupRun,
    DataRetentionPolicy,
    DeploymentRelease,
    FeatureFlag,
    SecurityEvent,
    ServiceHealthSnapshot,
    SystemAuditEvent,
    SystemIncident,
    RestoreTest,
)
from app.schemas.platform import (
    AuditEventRead,
    BackupCreate,
    BackupRead,
    DeploymentCreate,
    DeploymentRead,
    DiagnosticsRead,
    FeatureFlagRead,
    FeatureFlagWrite,
    IncidentCreate,
    IncidentRead,
    IncidentUpdate,
    IntegrityFinding,
    IntegrityReport,
    PlatformVersionRead,
    PreflightRead,
    RestoreTestRead,
    RetentionPolicyRead,
    RetentionPolicyWrite,
    SecurityEventRead,
)
from app.services.operations import create_job, mark_queued
from app.services.platform import (
    append_audit_event,
    configuration_warnings,
    current_migration,
    database_status,
    integrity_report,
    redis_status,
    storage_status,
    utcnow,
    verify_audit_chain,
    worker_status,
)

router = APIRouter(prefix="/platform", tags=["platform-hardening"])
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)
ALL_ROLES = (*ADMIN_ROLES, OrganizationRole.TEACHER, OrganizationRole.MEMBER)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def request_meta(request: Request) -> tuple[str, str]:
    return getattr(request.state, "request_id", request.headers.get("x-request-id", "")), request.client.host if request.client else ""


def require_platform_operator(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Esta operação é exclusiva do operador da plataforma",
        )


@router.get("/version", response_model=PlatformVersionRead)
async def platform_version(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    _: Membership = Depends(require_roles(*ALL_ROLES)),
) -> PlatformVersionRead:
    return PlatformVersionRead(
        application=settings.project_name,
        version=settings.app_version,
        build_identifier=settings.build_identifier,
        commit_sha=settings.commit_sha,
        environment=settings.environment,
        migration_revision=await current_migration(session),
        maintenance_mode=settings.maintenance_mode,
    )


@router.get("/diagnostics", response_model=DiagnosticsRead)
async def diagnostics(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    _: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> DiagnosticsRead:
    db_status, db_latency, db_details = await database_status(session)
    redis_state, redis_latency, redis_details = await redis_status(settings)
    workers = await worker_status(session)
    storage = storage_status(settings)
    dependencies = [
        {"name": "postgresql", "status": db_status, "latency_ms": db_latency, "details": db_details},
        {"name": "redis", "status": redis_state, "latency_ms": redis_latency, "details": redis_details},
    ]
    session.add_all([
        ServiceHealthSnapshot(organization_id=org_id(_), service_name="postgresql", status=db_status, latency_ms=db_latency, details=db_details),
        ServiceHealthSnapshot(organization_id=org_id(_), service_name="redis", status=redis_state, latency_ms=redis_latency, details=redis_details),
    ])
    await session.commit()
    storage_ok = all(bool(item.get("writable")) for item in storage.values())
    if not storage_ok:
        dependencies.append({"name": "storage", "status": "degraded", "latency_ms": 0, "details": storage})
    overall = "healthy"
    if any(item["status"] == "unavailable" for item in dependencies):
        overall = "unavailable"
    elif any(item["status"] == "degraded" for item in dependencies) or workers["active"] == 0:
        overall = "degraded"
    warnings = configuration_warnings(settings)
    if workers["active"] == 0:
        warnings.append("Nenhum worker ativo foi detectado.")
    return DiagnosticsRead(
        overall_status=overall,
        version=PlatformVersionRead(
            application=settings.project_name,
            version=settings.app_version,
            build_identifier=settings.build_identifier,
            commit_sha=settings.commit_sha,
            environment=settings.environment,
            migration_revision=await current_migration(session),
            maintenance_mode=settings.maintenance_mode,
        ),
        dependencies=dependencies,
        storage=storage,
        workers=workers,
        warnings=warnings,
    )


@router.get("/preflight", response_model=PreflightRead)
async def preflight(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    _: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> PreflightRead:
    db_state, db_latency, db_details = await database_status(session)
    redis_state, redis_latency, redis_details = await redis_status(settings)
    storage = storage_status(settings)
    checks = [
        {"name": "postgresql", "status": db_state, "latency_ms": db_latency, "details": db_details},
        {"name": "redis", "status": redis_state, "latency_ms": redis_latency, "details": redis_details},
        {
            "name": "storage",
            "status": "healthy" if all(x.get("writable") for x in storage.values()) else "unavailable",
            "latency_ms": 0,
            "details": storage,
        },
    ]
    warnings = configuration_warnings(settings)
    return PreflightRead(ready=all(item["status"] == "healthy" for item in checks) and not warnings, checks=checks, warnings=warnings)


@router.get("/deployments", response_model=list[DeploymentRead])
async def list_deployments(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[DeploymentRelease]:
    return list((await session.scalars(select(DeploymentRelease).where(DeploymentRelease.organization_id == org_id(membership)).order_by(DeploymentRelease.deployed_at.desc()).limit(100))).all())


@router.post("/deployments", response_model=DeploymentRead)
async def create_deployment(
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
        release_notes=data.release_notes,
        deployed_by_user_id=user.id,
    )
    session.add(release)
    await session.flush()
    req_id, ip = request_meta(request)
    await append_audit_event(session, organization_id=org_id(membership), user_id=user.id, module_name="platform", action="deployment.registered", entity_type="deployment_release", entity_id=release.id, request_id=req_id, ip_address=ip, details={"version": release.version, "build": release.build_identifier})
    await session.commit()
    await session.refresh(release)
    return release


@router.get("/backups", response_model=list[BackupRead])
async def list_backups(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> list[BackupRun]:
    require_platform_operator(user)
    return list(
        (
            await session.scalars(
                select(BackupRun)
                .where(BackupRun.organization_id == org_id(membership))
                .order_by(BackupRun.created_at.desc())
                .limit(100)
            )
        ).all()
    )


@router.post("/backups", response_model=BackupRead)
async def create_backup(
    data: BackupCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> BackupRun:
    require_platform_operator(user)
    backup = BackupRun(
        organization_id=org_id(membership),
        requested_by_user_id=user.id,
        backup_type=data.backup_type,
        expires_at=utcnow() + timedelta(days=data.retention_days),
    )
    session.add(backup)
    await session.flush()
    job, _ = await create_job(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        job_type="platform_backup",
        module_name="platform",
        entity_type="backup_run",
        entity_id=backup.id,
        input_snapshot={"backup_run_id": str(backup.id)},
        total_steps=4,
        max_retries=1,
    )
    req_id, ip = request_meta(request)
    await append_audit_event(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        module_name="platform",
        action="backup.requested",
        entity_type="backup_run",
        entity_id=backup.id,
        request_id=req_id,
        ip_address=ip,
        details={"backup_type": data.backup_type, "job_id": str(job.id)},
    )
    await session.commit()
    await mark_queued(session, job)
    await session.commit()
    await session.refresh(backup)
    return backup


@router.post("/backups/{backup_id}/verify", response_model=RestoreTestRead)
async def verify_backup(
    backup_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> RestoreTest:
    require_platform_operator(user)
    backup = await session.get(BackupRun, backup_id)
    if backup is None or backup.organization_id != org_id(membership):
        raise HTTPException(status_code=404, detail="Backup não encontrado")
    if backup.status != "completed" or not backup.storage_path:
        raise HTTPException(status_code=422, detail="O backup ainda não está pronto para restauração")
    test = RestoreTest(
        organization_id=org_id(membership),
        backup_run_id=backup.id,
        requested_by_user_id=user.id,
        status="pending",
    )
    session.add(test)
    await session.flush()
    job, _ = await create_job(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        job_type="platform_restore_test",
        module_name="platform",
        entity_type="restore_test",
        entity_id=test.id,
        input_snapshot={"backup_run_id": str(backup.id), "restore_test_id": str(test.id)},
        total_steps=5,
        max_retries=0,
    )
    req_id, ip = request_meta(request)
    await append_audit_event(
        session,
        organization_id=org_id(membership),
        user_id=user.id,
        module_name="platform",
        action="backup.restore_test_requested",
        entity_type="restore_test",
        entity_id=test.id,
        request_id=req_id,
        ip_address=ip,
        details={"backup_id": str(backup.id), "job_id": str(job.id)},
    )
    await session.commit()
    await mark_queued(session, job)
    await session.commit()
    await session.refresh(test)
    return test


@router.get("/incidents", response_model=list[IncidentRead])
async def list_incidents(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[SystemIncident]:
    statement = select(SystemIncident).where(SystemIncident.organization_id == org_id(membership)).order_by(SystemIncident.started_at.desc())
    if status:
        statement = statement.where(SystemIncident.status == status)
    return list((await session.scalars(statement.limit(200))).all())


@router.post("/incidents", response_model=IncidentRead)
async def create_incident(
    data: IncidentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> SystemIncident:
    incident = SystemIncident(organization_id=org_id(membership), title=data.title, severity=data.severity, affected_service=data.affected_service, impact=data.impact, opened_by_user_id=user.id)
    session.add(incident)
    await session.flush()
    req_id, ip = request_meta(request)
    await append_audit_event(session, organization_id=org_id(membership), user_id=user.id, module_name="platform", action="incident.created", entity_type="system_incident", entity_id=incident.id, request_id=req_id, ip_address=ip, details={"severity": incident.severity, "service": incident.affected_service})
    await session.commit()
    await session.refresh(incident)
    return incident


@router.patch("/incidents/{incident_id}", response_model=IncidentRead)
async def update_incident(
    incident_id: UUID,
    data: IncidentUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> SystemIncident:
    incident = await session.get(SystemIncident, incident_id)
    if incident is None or incident.organization_id != org_id(membership):
        raise HTTPException(status_code=404, detail="Incidente não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(incident, field, value)
    if incident.status in {"resolved", "closed"} and incident.resolved_at is None:
        incident.resolved_at = utcnow()
        incident.resolved_by_user_id = user.id
    req_id, ip = request_meta(request)
    await append_audit_event(session, organization_id=org_id(membership), user_id=user.id, module_name="platform", action="incident.updated", entity_type="system_incident", entity_id=incident.id, request_id=req_id, ip_address=ip, details=data.model_dump(exclude_unset=True))
    await session.commit()
    await session.refresh(incident)
    return incident


@router.get("/retention-policies", response_model=list[RetentionPolicyRead])
async def retention_policies(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[DataRetentionPolicy]:
    return list((await session.scalars(select(DataRetentionPolicy).where(DataRetentionPolicy.organization_id == org_id(membership)).order_by(DataRetentionPolicy.data_type))).all())


@router.put("/retention-policies/{data_type}", response_model=RetentionPolicyRead)
async def upsert_retention_policy(
    data_type: str,
    data: RetentionPolicyWrite,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> DataRetentionPolicy:
    if data_type != data.data_type:
        raise HTTPException(status_code=422, detail="O tipo da URL deve coincidir com o corpo")
    policy = await session.scalar(select(DataRetentionPolicy).where(DataRetentionPolicy.organization_id == org_id(membership), DataRetentionPolicy.data_type == data_type))
    if policy is None:
        policy = DataRetentionPolicy(organization_id=org_id(membership), data_type=data_type, created_by_user_id=user.id, updated_by_user_id=user.id)
        session.add(policy)
    for field, value in data.model_dump().items():
        setattr(policy, field, value)
    policy.updated_by_user_id = user.id
    await session.flush()
    req_id, ip = request_meta(request)
    await append_audit_event(session, organization_id=org_id(membership), user_id=user.id, module_name="privacy", action="retention_policy.updated", entity_type="data_retention_policy", entity_id=policy.id, request_id=req_id, ip_address=ip, details=data.model_dump())
    await session.commit()
    await session.refresh(policy)
    return policy


@router.get("/feature-flags", response_model=list[FeatureFlagRead])
async def feature_flags(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[FeatureFlag]:
    return list((await session.scalars(select(FeatureFlag).where((FeatureFlag.organization_id == org_id(membership)) | (FeatureFlag.organization_id.is_(None))).order_by(FeatureFlag.flag_key))).all())


@router.put("/feature-flags/{flag_key}", response_model=FeatureFlagRead)
async def upsert_feature_flag(
    flag_key: str,
    data: FeatureFlagWrite,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> FeatureFlag:
    if flag_key != data.flag_key:
        raise HTTPException(status_code=422, detail="A chave da URL deve coincidir com o corpo")
    flag = await session.scalar(select(FeatureFlag).where(FeatureFlag.organization_id == org_id(membership), FeatureFlag.flag_key == flag_key, FeatureFlag.scope_type == data.scope_type, FeatureFlag.scope_id == data.scope_id))
    if flag is None:
        flag = FeatureFlag(organization_id=org_id(membership), flag_key=flag_key, updated_by_user_id=user.id)
        session.add(flag)
    for field, value in data.model_dump().items():
        setattr(flag, field, value)
    flag.updated_by_user_id = user.id
    await session.flush()
    req_id, ip = request_meta(request)
    await append_audit_event(session, organization_id=org_id(membership), user_id=user.id, module_name="platform", action="feature_flag.updated", entity_type="feature_flag", entity_id=flag.id, request_id=req_id, ip_address=ip, details={"flag_key": flag_key, "enabled": flag.is_enabled, "scope": flag.scope_type})
    await session.commit()
    await session.refresh(flag)
    return flag


@router.get("/audit-events", response_model=list[AuditEventRead])
async def audit_events(
    module_name: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[SystemAuditEvent]:
    statement = select(SystemAuditEvent).where(SystemAuditEvent.organization_id == org_id(membership)).order_by(SystemAuditEvent.created_at.desc()).limit(limit)
    if module_name:
        statement = statement.where(SystemAuditEvent.module_name == module_name)
    if action:
        statement = statement.where(SystemAuditEvent.action == action)
    return list((await session.scalars(statement)).all())


@router.get("/audit-events/verify")
async def verify_audit_events(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> dict:
    return await verify_audit_chain(session, org_id(membership))


@router.get("/security-events", response_model=list[SecurityEventRead])
async def security_events(
    severity: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> list[SecurityEvent]:
    visibility = SecurityEvent.organization_id == org_id(membership)
    if user.is_superuser:
        visibility = visibility | SecurityEvent.organization_id.is_(None)
    statement = (
        select(SecurityEvent)
        .where(visibility)
        .order_by(SecurityEvent.created_at.desc())
        .limit(500)
    )
    if severity:
        statement = statement.where(SecurityEvent.severity == severity)
    return list((await session.scalars(statement)).all())


@router.get("/integrity", response_model=IntegrityReport)
async def platform_integrity(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> IntegrityReport:
    rows = await integrity_report(session, org_id(membership))
    findings = [IntegrityFinding(**row) for row in rows]
    status = "healthy"
    if any(item.severity == "critical" and item.count for item in findings):
        status = "critical"
    elif any(item.severity == "warning" and item.count for item in findings):
        status = "warnings"
    return IntegrityReport(status=status, checked_at=utcnow(), findings=findings)
