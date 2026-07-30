from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.consolidated_audit import append_domain_audit

from .compat import ActorContext, get_project_session, resolve_actor_context
from .models import (
    InstitutionalGovernanceAsset,
    InstitutionalGovernanceEvent,
    InstitutionalGovernanceIncident,
    InstitutionalGovernanceReview,
    InstitutionalGovernanceSnapshot,
)
from .policies import canonical_hash, documentation_completeness
from .schemas import (
    GovernanceActionRequest,
    GovernanceAssetCreate,
    GovernanceAssetUpdate,
    GovernanceBootstrapRequest,
    GovernanceIncidentCreate,
    GovernanceIncidentResolve,
    GovernanceRefreshRequest,
    GovernanceReviewCreate,
    GovernanceVersionCreate,
)
from .services import (
    activate_asset,
    add_event,
    bootstrap_assets,
    clone_version,
    compare_versions,
    create_asset,
    governance_csv,
    record_review,
    refresh_monitoring,
    reinstate_asset,
    review_state,
    snapshot_summary,
    suspend_asset,
)

router = APIRouter(
    prefix="/institutional-governance",
    tags=["institutional-governance"],
)
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

VIEW_ROLES = {
    "OWNER",
    "ADMIN",
    "ORG_ADMIN",
    "PLATFORM_ADMIN",
    "TEACHER",
    "COORDINATOR",
    "PEDAGOGICAL_COORDINATOR",
}
ADMIN_ROLES = {
    "OWNER",
    "ADMIN",
    "ORG_ADMIN",
    "PLATFORM_ADMIN",
    "COORDINATOR",
    "PEDAGOGICAL_COORDINATOR",
}


def require_view(actor: ActorContext) -> None:
    if not set(actor.roles).intersection(VIEW_ROLES):
        raise HTTPException(403, "Acesso à governança não autorizado.")


def require_admin(actor: ActorContext) -> None:
    if not set(actor.roles).intersection(ADMIN_ROLES):
        raise HTTPException(403, "A operação exige perfil de governança.")


async def asset_or_404(
    session: AsyncSession,
    actor: ActorContext,
    asset_id: uuid.UUID,
    *,
    lock: bool = False,
) -> InstitutionalGovernanceAsset:
    statement = select(InstitutionalGovernanceAsset).where(
        InstitutionalGovernanceAsset.organization_id
        == actor.organization_id,
        InstitutionalGovernanceAsset.id == asset_id,
    )
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        raise HTTPException(404, "Ativo de governança não encontrado.")
    return item


def asset_payload(
    item: InstitutionalGovernanceAsset,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "code": item.code,
        "name": item.name,
        "version": item.version,
        "asset_type": item.asset_type,
        "status": item.status,
        "risk_tier": item.risk_tier,
        "owner_user_id": str(item.owner_user_id),
        "adaptive_model_version_id": (
            str(item.adaptive_model_version_id)
            if item.adaptive_model_version_id
            else None
        ),
        "ai_model_id": str(item.ai_model_id) if item.ai_model_id else None,
        "prompt_template_id": (
            str(item.prompt_template_id)
            if item.prompt_template_id
            else None
        ),
        "module_policy_id": (
            str(item.module_policy_id)
            if item.module_policy_id
            else None
        ),
        "intervention_type": item.intervention_type,
        "evidence_rule_code": item.evidence_rule_code,
        "purpose": item.purpose,
        "intended_users": item.intended_users,
        "limitations": item.limitations,
        "prohibited_uses": item.prohibited_uses,
        "documentation": item.documentation,
        "documentation_completeness": documentation_completeness(
            item.documentation
        ),
        "approval_policy": item.approval_policy,
        "monitoring_policy": item.monitoring_policy,
        "lineage_snapshot": item.lineage_snapshot,
        "content_hash": item.content_hash,
        "review_summary": summary,
        "submitted_at": item.submitted_at,
        "approved_at": item.approved_at,
        "activated_at": item.activated_at,
        "suspended_at": item.suspended_at,
        "retired_at": item.retired_at,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def incident_payload(
    item: InstitutionalGovernanceIncident,
) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "asset_id": str(item.asset_id),
        "snapshot_id": str(item.snapshot_id) if item.snapshot_id else None,
        "category": item.category,
        "severity": item.severity,
        "status": item.status,
        "title": item.title,
        "description": item.description,
        "evidence": item.evidence,
        "remediation_plan": item.remediation_plan,
        "resolution_summary": item.resolution_summary,
        "detected_at": item.detected_at,
        "resolved_at": item.resolved_at,
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "sprint": "16.9",
        "module": "institutional-governance",
    }


@router.get("/dashboard")
async def dashboard(session: SessionDep, actor: ActorDep):
    require_view(actor)
    counts = {}
    for status in (
        "draft",
        "in_review",
        "approved",
        "active",
        "review_required",
        "suspended",
        "retired",
    ):
        counts[status] = int(
            await session.scalar(
                select(func.count(InstitutionalGovernanceAsset.id)).where(
                    InstitutionalGovernanceAsset.organization_id
                    == actor.organization_id,
                    InstitutionalGovernanceAsset.status == status,
                )
            )
            or 0
        )
    open_incidents = int(
        await session.scalar(
            select(func.count(InstitutionalGovernanceIncident.id)).where(
                InstitutionalGovernanceIncident.organization_id
                == actor.organization_id,
                InstitutionalGovernanceIncident.status == "open",
            )
        )
        or 0
    )
    threshold_breaches = int(
        await session.scalar(
            select(func.count(InstitutionalGovernanceSnapshot.id)).where(
                InstitutionalGovernanceSnapshot.organization_id
                == actor.organization_id,
                InstitutionalGovernanceSnapshot.threshold_breached.is_(True),
            )
        )
        or 0
    )
    return {
        "asset_counts": counts,
        "open_incidents": open_incidents,
        "threshold_breaches": threshold_breaches,
        "enforcement_mode": get_settings().governance_enforcement_mode,
        "human_suspension_required": True,
    }


@router.post("/bootstrap")
async def bootstrap(
    data: GovernanceBootstrapRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    result = await bootstrap_assets(
        session,
        actor=actor,
        options=data,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.bootstrap.completed",
        entity_type="organization",
        entity_id=actor.organization_id,
        details={"created": result},
    )
    await session.commit()
    return {"created": result}


@router.get("/assets")
async def list_assets(
    session: SessionDep,
    actor: ActorDep,
    asset_status: str | None = Query(default=None, alias="status"),
    asset_type: str | None = None,
    risk_tier: str | None = None,
    code: str | None = None,
    limit: int = Query(default=300, ge=1, le=2000),
):
    require_view(actor)
    statement = select(InstitutionalGovernanceAsset).where(
        InstitutionalGovernanceAsset.organization_id
        == actor.organization_id
    )
    if asset_status:
        statement = statement.where(
            InstitutionalGovernanceAsset.status == asset_status
        )
    if asset_type:
        statement = statement.where(
            InstitutionalGovernanceAsset.asset_type == asset_type
        )
    if risk_tier:
        statement = statement.where(
            InstitutionalGovernanceAsset.risk_tier == risk_tier
        )
    if code:
        statement = statement.where(
            InstitutionalGovernanceAsset.code.ilike(f"%{code}%")
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    InstitutionalGovernanceAsset.code,
                    InstitutionalGovernanceAsset.version.desc(),
                ).limit(limit)
            )
        ).all()
    )
    return [asset_payload(item) for item in rows]


@router.post("/assets", status_code=201)
async def add_asset(
    data: GovernanceAssetCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await create_asset(session, actor=actor, data=data)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.created",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={
            "code": item.code,
            "version": item.version,
            "asset_type": item.asset_type,
            "risk_tier": item.risk_tier,
        },
    )
    await session.commit()
    return asset_payload(item)


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_view(actor)
    item = await asset_or_404(session, actor, asset_id)
    summary = await review_state(
        session,
        asset=item,
        institutional_default=get_settings().governance_min_approvals,
    )
    reviews = list(
        (
            await session.scalars(
                select(InstitutionalGovernanceReview)
                .where(
                    InstitutionalGovernanceReview.organization_id
                    == actor.organization_id,
                    InstitutionalGovernanceReview.asset_id == item.id,
                )
                .order_by(InstitutionalGovernanceReview.created_at)
            )
        ).all()
    )
    latest_snapshot = await session.scalar(
        select(InstitutionalGovernanceSnapshot)
        .where(
            InstitutionalGovernanceSnapshot.organization_id
            == actor.organization_id,
            InstitutionalGovernanceSnapshot.asset_id == item.id,
        )
        .order_by(InstitutionalGovernanceSnapshot.calculated_at.desc())
        .limit(1)
    )
    return {
        **asset_payload(item, summary),
        "reviews": [
            {
                "id": str(review.id),
                "reviewer_user_id": str(review.reviewer_user_id),
                "review_stage": review.review_stage,
                "decision": review.decision,
                "scorecard": review.scorecard,
                "findings": review.findings,
                "required_actions": review.required_actions,
                "comments": review.comments,
                "decided_at": review.decided_at,
            }
            for review in reviews
        ],
        "latest_snapshot": snapshot_summary(latest_snapshot),
    }


@router.patch("/assets/{asset_id}")
async def update_asset(
    asset_id: uuid.UUID,
    data: GovernanceAssetUpdate,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    if item.status not in {"draft", "changes_requested"}:
        raise HTTPException(
            409,
            "Somente rascunhos ou versões com ajustes podem ser editados.",
        )
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(item, key, value)
    item.content_hash = canonical_hash(
        {
            "name": item.name,
            "risk_tier": item.risk_tier,
            "purpose": item.purpose,
            "intended_users": item.intended_users,
            "limitations": item.limitations,
            "prohibited_uses": item.prohibited_uses,
            "documentation": item.documentation,
            "approval_policy": item.approval_policy,
            "monitoring_policy": item.monitoring_policy,
            "lineage_snapshot": item.lineage_snapshot,
        }
    )
    previous = item.status
    item.status = "draft"
    await add_event(
        session,
        asset=item,
        actor_user_id=actor.user_id,
        event_type="governance.asset.updated",
        from_status=previous,
        to_status="draft",
        data={"changed_fields": sorted(changes)},
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.updated",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={"changed_fields": sorted(changes)},
    )
    await session.commit()
    return asset_payload(item)


@router.post("/assets/{asset_id}/version", status_code=201)
async def create_version(
    asset_id: uuid.UUID,
    data: GovernanceVersionCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    source = await asset_or_404(session, actor, asset_id)
    item = await clone_version(
        session,
        actor=actor,
        source=source,
        change_summary=data.change_summary,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.version_created",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={
            "source_asset_id": str(source.id),
            "version": item.version,
            "change_summary": data.change_summary,
        },
    )
    await session.commit()
    return asset_payload(item)


@router.post("/assets/{asset_id}/submit")
async def submit_asset(
    asset_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    if item.status not in {"draft", "changes_requested"}:
        raise HTTPException(409, "O ativo não pode ser submetido neste estado.")
    previous = item.status
    item.status = "in_review"
    item.submitted_at = datetime.now(UTC)
    await add_event(
        session,
        asset=item,
        actor_user_id=actor.user_id,
        event_type="governance.asset.submitted",
        from_status=previous,
        to_status="in_review",
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.submitted",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={"code": item.code, "version": item.version},
    )
    await session.commit()
    return asset_payload(item)


@router.post("/assets/{asset_id}/reviews")
async def review_asset(
    asset_id: uuid.UUID,
    data: GovernanceReviewCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    review, summary = await record_review(
        session,
        actor=actor,
        asset=item,
        data=data,
        institutional_default=get_settings().governance_min_approvals,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.review.decided",
        entity_type="institutional_governance_review",
        entity_id=review.id,
        details={
            "asset_id": str(item.id),
            "stage": review.review_stage,
            "decision": review.decision,
            "summary": summary,
        },
    )
    await session.commit()
    return {
        "asset": asset_payload(item, summary),
        "review_id": str(review.id),
    }


@router.post("/assets/{asset_id}/activate")
async def activate(
    asset_id: uuid.UUID,
    data: GovernanceActionRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    await activate_asset(
        session,
        actor=actor,
        asset=item,
        minimum_documentation=(
            get_settings().governance_min_documentation_completeness
        ),
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.activated",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={"reason": data.reason},
    )
    await session.commit()
    return asset_payload(item)


@router.post("/assets/{asset_id}/suspend")
async def suspend(
    asset_id: uuid.UUID,
    data: GovernanceActionRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    incident = await suspend_asset(
        session,
        actor=actor,
        asset=item,
        reason=data.reason,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.suspended",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={
            "reason": data.reason,
            "incident_id": str(incident.id),
        },
    )
    await session.commit()
    return {
        "asset": asset_payload(item),
        "incident": incident_payload(incident),
    }


@router.post("/assets/{asset_id}/reinstate")
async def reinstate(
    asset_id: uuid.UUID,
    data: GovernanceActionRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    await reinstate_asset(
        session,
        actor=actor,
        asset=item,
        reason=data.reason,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.reinstated",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={"reason": data.reason},
    )
    await session.commit()
    return asset_payload(item)


@router.post("/assets/{asset_id}/retire")
async def retire(
    asset_id: uuid.UUID,
    data: GovernanceActionRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await asset_or_404(session, actor, asset_id, lock=True)
    if item.status == "retired":
        return asset_payload(item)
    previous = item.status
    item.status = "retired"
    item.retired_at = datetime.now(UTC)
    from .services import sync_reference_status
    await sync_reference_status(session, asset=item, active=False)
    await add_event(
        session,
        asset=item,
        actor_user_id=actor.user_id,
        event_type="governance.asset.retired",
        from_status=previous,
        to_status="retired",
        data={"reason": data.reason},
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.asset.retired",
        entity_type="institutional_governance_asset",
        entity_id=item.id,
        details={"reason": data.reason},
    )
    await session.commit()
    return asset_payload(item)


@router.get("/compare")
async def compare(
    left_id: uuid.UUID,
    right_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_view(actor)
    left = await asset_or_404(session, actor, left_id)
    right = await asset_or_404(session, actor, right_id)
    return await compare_versions(session, left=left, right=right)


@router.post("/monitoring/refresh")
async def refresh(
    data: GovernanceRefreshRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    result = await refresh_monitoring(
        session,
        actor=actor,
        period_start=data.period_start,
        period_end=data.period_end,
        asset_ids=data.asset_ids,
        open_incidents=data.open_incidents,
        lookback_days=get_settings().governance_monitoring_lookback_days,
        minimum_group_size=get_settings().governance_min_group_size,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.monitoring.refreshed",
        entity_type="background_job",
        entity_id=uuid.UUID(result["job_id"]),
        details=data.model_dump(mode="json"),
    )
    await session.commit()
    return result


@router.get("/monitoring/snapshots")
async def snapshots(
    session: SessionDep,
    actor: ActorDep,
    asset_id: uuid.UUID | None = None,
    breached_only: bool = False,
    limit: int = Query(default=500, ge=1, le=2000),
):
    require_view(actor)
    statement = select(InstitutionalGovernanceSnapshot).where(
        InstitutionalGovernanceSnapshot.organization_id
        == actor.organization_id
    )
    if asset_id:
        statement = statement.where(
            InstitutionalGovernanceSnapshot.asset_id == asset_id
        )
    if breached_only:
        statement = statement.where(
            InstitutionalGovernanceSnapshot.threshold_breached.is_(True)
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    InstitutionalGovernanceSnapshot.calculated_at.desc()
                ).limit(limit)
            )
        ).all()
    )
    return [
        {
            "asset_id": str(item.asset_id),
            **(snapshot_summary(item) or {}),
        }
        for item in rows
    ]


@router.get("/incidents")
async def incidents(
    session: SessionDep,
    actor: ActorDep,
    incident_status: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    asset_id: uuid.UUID | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
):
    require_view(actor)
    statement = select(InstitutionalGovernanceIncident).where(
        InstitutionalGovernanceIncident.organization_id
        == actor.organization_id
    )
    if incident_status:
        statement = statement.where(
            InstitutionalGovernanceIncident.status == incident_status
        )
    if severity:
        statement = statement.where(
            InstitutionalGovernanceIncident.severity == severity
        )
    if asset_id:
        statement = statement.where(
            InstitutionalGovernanceIncident.asset_id == asset_id
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    InstitutionalGovernanceIncident.detected_at.desc()
                ).limit(limit)
            )
        ).all()
    )
    return [incident_payload(item) for item in rows]


@router.post("/assets/{asset_id}/incidents", status_code=201)
async def create_incident(
    asset_id: uuid.UUID,
    data: GovernanceIncidentCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    asset = await asset_or_404(session, actor, asset_id)
    item = InstitutionalGovernanceIncident(
        organization_id=actor.organization_id,
        asset_id=asset.id,
        opened_by_user_id=actor.user_id,
        category=data.category,
        severity=data.severity,
        status="open",
        title=data.title,
        description=data.description,
        evidence=data.evidence,
        remediation_plan=data.remediation_plan,
    )
    session.add(item)
    await session.flush()
    await add_event(
        session,
        asset=asset,
        actor_user_id=actor.user_id,
        event_type="governance.incident.opened",
        from_status=asset.status,
        to_status=asset.status,
        data={"incident_id": str(item.id), "severity": item.severity},
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.incident.opened",
        entity_type="institutional_governance_incident",
        entity_id=item.id,
        details={"asset_id": str(asset.id), "severity": item.severity},
    )
    await session.commit()
    return incident_payload(item)


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: uuid.UUID,
    data: GovernanceIncidentResolve,
    session: SessionDep,
    actor: ActorDep,
):
    require_admin(actor)
    item = await session.scalar(
        select(InstitutionalGovernanceIncident)
        .where(
            InstitutionalGovernanceIncident.organization_id
            == actor.organization_id,
            InstitutionalGovernanceIncident.id == incident_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Incidente não encontrado.")
    if item.status == "resolved":
        return incident_payload(item)
    item.status = "resolved"
    item.resolution_summary = data.resolution_summary
    item.resolved_by_user_id = actor.user_id
    item.resolved_at = datetime.now(UTC)
    asset = await asset_or_404(session, actor, item.asset_id)
    await add_event(
        session,
        asset=asset,
        actor_user_id=actor.user_id,
        event_type="governance.incident.resolved",
        from_status=asset.status,
        to_status=asset.status,
        data={"incident_id": str(item.id)},
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.incident.resolved",
        entity_type="institutional_governance_incident",
        entity_id=item.id,
        details={"resolution_summary": data.resolution_summary},
    )
    await session.commit()
    return incident_payload(item)


@router.get("/assets/{asset_id}/timeline")
async def timeline(
    asset_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_view(actor)
    await asset_or_404(session, actor, asset_id)
    rows = list(
        (
            await session.scalars(
                select(InstitutionalGovernanceEvent)
                .where(
                    InstitutionalGovernanceEvent.organization_id
                    == actor.organization_id,
                    InstitutionalGovernanceEvent.asset_id == asset_id,
                )
                .order_by(InstitutionalGovernanceEvent.created_at)
            )
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "actor_user_id": (
                str(item.actor_user_id) if item.actor_user_id else None
            ),
            "event_type": item.event_type,
            "from_status": item.from_status,
            "to_status": item.to_status,
            "event_data": item.event_data,
            "created_at": item.created_at,
        }
        for item in rows
    ]


@router.get("/export.csv")
async def export_csv(session: SessionDep, actor: ActorDep):
    require_admin(actor)
    assets = list(
        (
            await session.scalars(
                select(InstitutionalGovernanceAsset)
                .where(
                    InstitutionalGovernanceAsset.organization_id
                    == actor.organization_id
                )
                .order_by(
                    InstitutionalGovernanceAsset.code,
                    InstitutionalGovernanceAsset.version,
                )
            )
        ).all()
    )
    content = governance_csv(assets)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="institutional_governance",
        action="governance.registry.exported",
        entity_type="organization",
        entity_id=actor.organization_id,
        details={"rows": len(assets)},
    )
    await session.commit()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
            'attachment; filename="institutional-governance.csv"'
        },
    )
