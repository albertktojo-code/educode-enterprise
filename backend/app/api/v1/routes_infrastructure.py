from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.infrastructure import (
    AutoscalingPolicy,
    ClusterHealthSnapshot,
    DisasterRecoveryPlan,
    DisasterRecoveryRun,
    FailoverEvent,
    GitOpsApplication,
    InfrastructureCluster,
    ObjectStorageTarget,
    StorageReplicationLink,
)
from app.schemas.infrastructure import (
    AutoscalingPolicyRead,
    AutoscalingPolicyWrite,
    CapacityRecommendation,
    ClusterHealthRead,
    ClusterHealthWrite,
    ClusterRead,
    ClusterWrite,
    DRPlanRead,
    DRPlanWrite,
    DRReadiness,
    DRRunCreate,
    DRRunRead,
    FailoverEventCreate,
    FailoverEventDecision,
    FailoverEventRead,
    GitOpsApplicationRead,
    GitOpsApplicationWrite,
    InfrastructureOverview,
    ReplicationLinkRead,
    ReplicationLinkWrite,
    StorageTargetRead,
    StorageTargetWrite,
    StorageTestRead,
)
from app.services.infrastructure import (
    calculate_capacity_recommendation,
    dr_readiness,
    render_argocd_application,
    render_hpa_values,
)
from app.services.object_storage import LocalObjectStorage, S3CompatibleObjectStorage

router = APIRouter(prefix="/infrastructure", tags=["infrastructure-continuity"])
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def require_global_operator(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Operação exclusiva do operador global da plataforma")


async def scoped(session: AsyncSession, model, entity_id: UUID, organization_id: UUID):
    item = await session.scalar(select(model).where(model.id == entity_id, model.organization_id == organization_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return item


@router.get("/overview", response_model=InfrastructureOverview)
async def overview(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    settings: Settings = Depends(get_settings),
) -> InfrastructureOverview:
    oid = org_id(membership)
    async def count(model, *conditions) -> int:
        return int(await session.scalar(select(func.count(model.id)).where(model.organization_id == oid, *conditions)) or 0)
    return InfrastructureOverview(
        clusters=await count(InfrastructureCluster),
        healthy_clusters=await count(InfrastructureCluster, InfrastructureCluster.status == "healthy"),
        storage_targets=await count(ObjectStorageTarget),
        healthy_storage_targets=await count(ObjectStorageTarget, ObjectStorageTarget.status == "healthy"),
        replication_links=await count(StorageReplicationLink),
        dr_plans=await count(DisasterRecoveryPlan),
        gitops_applications=await count(GitOpsApplication),
        autoscaling_policies=await count(AutoscalingPolicy),
        kubernetes_enabled=settings.kubernetes_enabled,
        gitops_enabled=settings.gitops_enabled,
        object_storage_provider=settings.object_storage_provider,
    )


@router.get("/clusters", response_model=list[ClusterRead])
async def list_clusters(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[InfrastructureCluster]:
    return list((await session.scalars(select(InfrastructureCluster).where(InfrastructureCluster.organization_id == org_id(membership)).order_by(InfrastructureCluster.environment, InfrastructureCluster.name))).all())


@router.post("/clusters", response_model=ClusterRead)
async def create_cluster(
    data: ClusterWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> InfrastructureCluster:
    cluster = InfrastructureCluster(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        status="unknown",
        **data.model_dump(),
    )
    if data.is_primary:
        await session.execute(
            InfrastructureCluster.__table__.update()
            .where(InfrastructureCluster.organization_id == org_id(membership), InfrastructureCluster.environment == data.environment)
            .values(is_primary=False)
        )
    session.add(cluster)
    await session.commit()
    await session.refresh(cluster)
    return cluster


@router.post("/clusters/{cluster_id}/health", response_model=ClusterHealthRead)
async def record_cluster_health(
    cluster_id: UUID,
    data: ClusterHealthWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> ClusterHealthSnapshot:
    cluster = await scoped(session, InfrastructureCluster, cluster_id, org_id(membership))
    snapshot = ClusterHealthSnapshot(
        organization_id=org_id(membership),
        cluster_id=cluster.id,
        **data.model_dump(),
    )
    cluster.status = data.status
    cluster.last_seen_at = datetime.now(UTC)
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


@router.get("/storage-targets", response_model=list[StorageTargetRead])
async def list_storage_targets(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[ObjectStorageTarget]:
    return list((await session.scalars(select(ObjectStorageTarget).where(ObjectStorageTarget.organization_id == org_id(membership)).order_by(ObjectStorageTarget.name))).all())


@router.post("/storage-targets", response_model=StorageTargetRead)
async def create_storage_target(
    data: StorageTargetWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> ObjectStorageTarget:
    target = ObjectStorageTarget(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        status="unknown",
        **data.model_dump(),
    )
    if data.is_primary:
        await session.execute(
            ObjectStorageTarget.__table__.update()
            .where(ObjectStorageTarget.organization_id == org_id(membership))
            .values(is_primary=False)
        )
    session.add(target)
    await session.commit()
    await session.refresh(target)
    return target


@router.post("/storage-targets/{target_id}/test", response_model=StorageTestRead)
async def test_storage_target(
    target_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    settings: Settings = Depends(get_settings),
) -> StorageTestRead:
    target = await scoped(session, ObjectStorageTarget, target_id, org_id(membership))
    started = perf_counter()
    warnings: list[str] = []
    if target.provider == "s3":
        if target.secret_reference and target.secret_reference not in {"S3_ACCESS_KEY_ID", "platform-default"}:
            warnings.append("O secret_reference é apenas metadado; as credenciais vêm do ambiente do backend")
        adapter = S3CompatibleObjectStorage(
            endpoint_url=target.endpoint_url,
            bucket_name=target.bucket_name,
            region=target.region,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            prefix=target.prefix,
            use_ssl=settings.s3_use_ssl,
        )
    else:
        adapter = LocalObjectStorage(settings.object_storage_local_path)
    checks = await adapter.healthcheck()
    status = str(checks.get("status", "unavailable"))
    target.status = status
    target.last_tested_at = datetime.now(UTC)
    target.last_test_result = checks
    await session.commit()
    return StorageTestRead(
        target_id=target.id,
        status=status,
        latency_ms=float(checks.get("latency_ms", round((perf_counter() - started) * 1000, 3))),
        checks=checks,
        warnings=warnings,
    )


@router.get("/replication-links", response_model=list[ReplicationLinkRead])
async def list_replication_links(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[StorageReplicationLink]:
    return list((await session.scalars(select(StorageReplicationLink).where(StorageReplicationLink.organization_id == org_id(membership)).order_by(StorageReplicationLink.created_at.desc()))).all())


@router.post("/replication-links", response_model=ReplicationLinkRead)
async def create_replication_link(
    data: ReplicationLinkWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> StorageReplicationLink:
    source = await scoped(session, ObjectStorageTarget, data.source_target_id, org_id(membership))
    destination = await scoped(session, ObjectStorageTarget, data.destination_target_id, org_id(membership))
    link = StorageReplicationLink(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        status="configured" if source.status != "unavailable" and destination.status != "unavailable" else "degraded",
        **data.model_dump(),
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


@router.get("/dr-plans", response_model=list[DRPlanRead])
async def list_dr_plans(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[DisasterRecoveryPlan]:
    return list((await session.scalars(select(DisasterRecoveryPlan).where(DisasterRecoveryPlan.organization_id == org_id(membership)).order_by(DisasterRecoveryPlan.created_at.desc()))).all())


@router.post("/dr-plans", response_model=DRPlanRead)
async def create_dr_plan(
    data: DRPlanWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> DisasterRecoveryPlan:
    await scoped(session, InfrastructureCluster, data.primary_cluster_id, org_id(membership))
    await scoped(session, InfrastructureCluster, data.recovery_cluster_id, org_id(membership))
    if data.replication_link_id:
        await scoped(session, StorageReplicationLink, data.replication_link_id, org_id(membership))
    plan = DisasterRecoveryPlan(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        status="active",
        **data.model_dump(),
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


@router.get("/dr-plans/{plan_id}/readiness", response_model=DRReadiness)
async def get_dr_readiness(
    plan_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> DRReadiness:
    plan = await scoped(session, DisasterRecoveryPlan, plan_id, org_id(membership))
    primary = await scoped(session, InfrastructureCluster, plan.primary_cluster_id, org_id(membership))
    recovery = await scoped(session, InfrastructureCluster, plan.recovery_cluster_id, org_id(membership))
    replication = None
    if plan.replication_link_id:
        replication = await scoped(session, StorageReplicationLink, plan.replication_link_id, org_id(membership))
    return DRReadiness(**dr_readiness(plan, primary=primary, recovery=recovery, replication=replication))


@router.post("/dr-plans/{plan_id}/runs", response_model=DRRunRead)
async def create_dr_run(
    plan_id: UUID,
    data: DRRunCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> DisasterRecoveryRun:
    plan = await scoped(session, DisasterRecoveryPlan, plan_id, org_id(membership))
    if data.run_type in {"failover", "failback"}:
        require_global_operator(user)
    run = DisasterRecoveryRun(
        organization_id=org_id(membership),
        plan_id=plan.id,
        initiated_by_user_id=user.id,
        run_type=data.run_type,
        status="planned",
        current_step="readiness_check",
        checkpoint_json={"reason": data.reason, "automatic_execution": False},
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/failover-events", response_model=list[FailoverEventRead])
async def list_failover_events(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[FailoverEvent]:
    return list((await session.scalars(select(FailoverEvent).where(FailoverEvent.organization_id == org_id(membership)).order_by(FailoverEvent.created_at.desc()).limit(100))).all())


@router.post("/dr-plans/{plan_id}/failover-events", response_model=FailoverEventRead)
async def request_failover(
    plan_id: UUID,
    data: FailoverEventCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> FailoverEvent:
    plan = await scoped(session, DisasterRecoveryPlan, plan_id, org_id(membership))
    event = FailoverEvent(
        organization_id=org_id(membership),
        plan_id=plan.id,
        direction=data.direction,
        status="requested",
        reason=data.reason,
        requested_by_user_id=user.id,
        details={"automatic_execution": False, "requires_platform_operator": True},
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


@router.patch("/failover-events/{event_id}", response_model=FailoverEventRead)
async def decide_failover(
    event_id: UUID,
    data: FailoverEventDecision,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> FailoverEvent:
    require_global_operator(user)
    event = await scoped(session, FailoverEvent, event_id, org_id(membership))
    if event.status != "requested":
        raise HTTPException(status_code=409, detail="Evento já foi decidido")
    event.status = data.decision
    event.approved_by_user_id = user.id if data.decision == "approved" else None
    event.details = {**event.details, "decision_notes": data.notes, "automatic_execution": False}
    if data.decision == "approved":
        event.initiated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(event)
    return event


@router.get("/gitops-applications", response_model=list[GitOpsApplicationRead])
async def list_gitops_apps(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[GitOpsApplication]:
    return list((await session.scalars(select(GitOpsApplication).where(GitOpsApplication.organization_id == org_id(membership)).order_by(GitOpsApplication.environment, GitOpsApplication.name))).all())


@router.post("/gitops-applications", response_model=GitOpsApplicationRead)
async def create_gitops_app(
    data: GitOpsApplicationWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> GitOpsApplication:
    await scoped(session, InfrastructureCluster, data.cluster_id, org_id(membership))
    app = GitOpsApplication(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        **data.model_dump(),
    )
    session.add(app)
    await session.commit()
    await session.refresh(app)
    return app


@router.get("/gitops-applications/{application_id}/manifest")
async def get_gitops_manifest(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> Response:
    app = await scoped(session, GitOpsApplication, application_id, org_id(membership))
    cluster = await scoped(session, InfrastructureCluster, app.cluster_id, org_id(membership))
    return Response(render_argocd_application(app, cluster), media_type="application/yaml")


@router.get("/autoscaling-policies", response_model=list[AutoscalingPolicyRead])
async def list_autoscaling(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> list[AutoscalingPolicy]:
    return list((await session.scalars(select(AutoscalingPolicy).where(AutoscalingPolicy.organization_id == org_id(membership)).order_by(AutoscalingPolicy.environment, AutoscalingPolicy.component))).all())


@router.put("/autoscaling-policies", response_model=AutoscalingPolicyRead)
async def upsert_autoscaling(
    data: AutoscalingPolicyWrite,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> AutoscalingPolicy:
    policy = await session.scalar(select(AutoscalingPolicy).where(
        AutoscalingPolicy.organization_id == org_id(membership),
        AutoscalingPolicy.environment == data.environment,
        AutoscalingPolicy.component == data.component,
    ))
    if policy is None:
        policy = AutoscalingPolicy(organization_id=org_id(membership), created_by_user_id=user.id, **data.model_dump())
        session.add(policy)
    else:
        for field, value in data.model_dump().items():
            setattr(policy, field, value)
    await session.commit()
    await session.refresh(policy)
    return policy


@router.post("/autoscaling-policies/{policy_id}/recommend", response_model=CapacityRecommendation)
async def recommend_capacity(
    policy_id: UUID,
    current_replicas: int = 1,
    cpu_percent: float = 0,
    memory_percent: float = 0,
    queue_depth: int = 0,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> CapacityRecommendation:
    policy = await scoped(session, AutoscalingPolicy, policy_id, org_id(membership))
    return CapacityRecommendation(**calculate_capacity_recommendation(
        policy,
        current_replicas=current_replicas,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        queue_depth=queue_depth,
    ))


@router.get("/autoscaling-policies/{policy_id}/helm-values")
async def autoscaling_helm_values(
    policy_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> dict[str, object]:
    policy = await scoped(session, AutoscalingPolicy, policy_id, org_id(membership))
    return {policy.component: {"autoscaling": render_hpa_values(policy)}}
