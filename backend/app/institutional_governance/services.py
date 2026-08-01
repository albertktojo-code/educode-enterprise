from __future__ import annotations

import csv
import io
import json
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from statistics import mean
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intervention_effectiveness.models import (
    InterventionEvaluationCheckpoint,
)
from app.models.adaptive import AdaptiveModelVersion, AdaptiveRecommendation
from app.models.ai_advanced import AIQualityEvaluation
from app.models.ai_runtime import (
    AIGenerationRequest,
    AIGenerationResult,
    AIGenerationReview,
    AIModel,
    AIModulePolicy,
    AIPromptTemplate,
)
from app.models.analytics import (
    InterventionType,
    LearningAlert,
    LearningIntervention,
)
from app.models.auth import Organization
from app.models.operations import BackgroundJob

from .compat import ActorContext
from .models import (
    InstitutionalGovernanceAsset,
    InstitutionalGovernanceEvent,
    InstitutionalGovernanceIncident,
    InstitutionalGovernanceReview,
    InstitutionalGovernanceSnapshot,
)
from .policies import (
    ACTIVE_STATUSES,
    ASSET_TYPES,
    canonical_hash,
    compare_documents,
    documentation_completeness,
    fairness_from_cohorts,
    monitoring_period,
    review_summary,
    threshold_breaches,
)


class GovernanceExecutionError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def date_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end, time.max, tzinfo=UTC),
    )


def _average(values: list[float]) -> float | None:
    return round(mean(values), 4) if values else None


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


async def add_event(
    session: AsyncSession,
    *,
    asset: InstitutionalGovernanceAsset,
    actor_user_id: uuid.UUID | None,
    event_type: str,
    from_status: str = "",
    to_status: str = "",
    data: dict[str, Any] | None = None,
) -> InstitutionalGovernanceEvent:
    item = InstitutionalGovernanceEvent(
        organization_id=asset.organization_id,
        asset_id=asset.id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        event_data=data or {},
    )
    session.add(item)
    await session.flush()
    return item


async def reference_snapshot(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    asset_type: str,
    adaptive_model_version_id: uuid.UUID | None = None,
    ai_model_id: uuid.UUID | None = None,
    prompt_template_id: uuid.UUID | None = None,
    module_policy_id: uuid.UUID | None = None,
    intervention_type: str | None = None,
    evidence_rule_code: str | None = None,
) -> dict[str, Any]:
    if asset_type == "adaptive_model":
        item = await session.scalar(
            select(AdaptiveModelVersion).where(
                AdaptiveModelVersion.organization_id == organization_id,
                AdaptiveModelVersion.id == adaptive_model_version_id,
            )
        )
        if item is None:
            raise HTTPException(409, "Modelo adaptativo não pertence à organização.")
        return {
            "reference_type": asset_type,
            "reference_id": str(item.id),
            "code": item.code,
            "version": item.version,
            "status": item.status,
            "rules_json": item.rules_json,
            "thresholds_json": item.thresholds_json,
            "minimum_evidence_count": item.minimum_evidence_count,
        }

    if asset_type == "ai_model":
        item = await session.scalar(
            select(AIModel).where(
                AIModel.organization_id == organization_id,
                AIModel.id == ai_model_id,
            )
        )
        if item is None:
            raise HTTPException(409, "Modelo de IA não pertence à organização.")
        return {
            "reference_type": asset_type,
            "reference_id": str(item.id),
            "name": item.name,
            "model_identifier": item.model_identifier,
            "capabilities": item.capabilities,
            "configuration": item.configuration,
            "is_active": item.is_active,
        }

    if asset_type == "prompt_template":
        item = await session.scalar(
            select(AIPromptTemplate).where(
                AIPromptTemplate.organization_id == organization_id,
                AIPromptTemplate.id == prompt_template_id,
            )
        )
        if item is None:
            raise HTTPException(409, "Template de prompt não pertence à organização.")
        return {
            "reference_type": asset_type,
            "reference_id": str(item.id),
            "purpose": item.purpose,
            "version": item.version,
            "status": item.status,
            "required_variables": item.required_variables,
            "output_schema": item.output_schema,
            "recommended_model_id": (
                str(item.recommended_model_id)
                if item.recommended_model_id
                else None
            ),
        }

    if asset_type == "module_policy":
        item = await session.scalar(
            select(AIModulePolicy).where(
                AIModulePolicy.organization_id == organization_id,
                AIModulePolicy.id == module_policy_id,
            )
        )
        if item is None:
            raise HTTPException(409, "Política de IA não pertence à organização.")
        return {
            "reference_type": asset_type,
            "reference_id": str(item.id),
            "module_name": item.module_name,
            "enabled": item.enabled,
            "allowed_actions": item.allowed_actions,
            "allowed_model_ids": item.allowed_model_ids,
            "human_approval_required": item.human_approval_required,
            "allow_student_data": item.allow_student_data,
            "policy_configuration": item.policy_configuration,
        }

    if asset_type == "intervention_strategy":
        try:
            normalized = InterventionType(str(intervention_type)).value
        except ValueError as error:
            raise HTTPException(409, "Tipo de intervenção desconhecido.") from error
        return {
            "reference_type": asset_type,
            "intervention_type": normalized,
        }

    if asset_type == "evidence_rule":
        if not evidence_rule_code:
            raise HTTPException(409, "Código da regra de evidência ausente.")
        usage_count = await session.scalar(
            select(func.count(LearningAlert.id)).where(
                LearningAlert.organization_id == organization_id,
                LearningAlert.rule_code == evidence_rule_code,
            )
        )
        return {
            "reference_type": asset_type,
            "evidence_rule_code": evidence_rule_code,
            "historical_alert_count": int(usage_count or 0),
        }

    raise HTTPException(422, "Tipo de ativo de governança inválido.")


async def create_asset(
    session: AsyncSession,
    *,
    actor: ActorContext,
    data: Any,
) -> InstitutionalGovernanceAsset:
    await session.execute(
        select(Organization.id)
        .where(Organization.id == actor.organization_id)
        .with_for_update()
    )
    version = int(getattr(data, "version", 1))
    duplicate = await session.scalar(
        select(InstitutionalGovernanceAsset.id).where(
            InstitutionalGovernanceAsset.organization_id
            == actor.organization_id,
            InstitutionalGovernanceAsset.code == data.code,
            InstitutionalGovernanceAsset.version == version,
        )
    )
    if duplicate:
        raise HTTPException(409, "Já existe um ativo com este código e versão.")

    lineage = await reference_snapshot(
        session,
        organization_id=actor.organization_id,
        asset_type=data.asset_type,
        adaptive_model_version_id=data.adaptive_model_version_id,
        ai_model_id=data.ai_model_id,
        prompt_template_id=data.prompt_template_id,
        module_policy_id=data.module_policy_id,
        intervention_type=data.intervention_type,
        evidence_rule_code=data.evidence_rule_code,
    )
    content = {
        "name": data.name,
        "risk_tier": data.risk_tier,
        "purpose": data.purpose,
        "intended_users": data.intended_users,
        "limitations": data.limitations,
        "prohibited_uses": data.prohibited_uses,
        "documentation": data.documentation,
        "approval_policy": data.approval_policy,
        "monitoring_policy": data.monitoring_policy,
        "lineage": lineage,
    }
    item = InstitutionalGovernanceAsset(
        organization_id=actor.organization_id,
        code=data.code,
        name=data.name,
        version=version,
        asset_type=data.asset_type,
        status="draft",
        risk_tier=data.risk_tier,
        owner_user_id=actor.user_id,
        adaptive_model_version_id=data.adaptive_model_version_id,
        ai_model_id=data.ai_model_id,
        prompt_template_id=data.prompt_template_id,
        module_policy_id=data.module_policy_id,
        intervention_type=data.intervention_type,
        evidence_rule_code=data.evidence_rule_code,
        purpose=data.purpose,
        intended_users=data.intended_users,
        limitations=data.limitations,
        prohibited_uses=data.prohibited_uses,
        documentation=data.documentation,
        approval_policy=data.approval_policy,
        monitoring_policy=data.monitoring_policy,
        lineage_snapshot=lineage,
        content_hash=canonical_hash(content),
    )
    session.add(item)
    await session.flush()
    await add_event(
        session,
        asset=item,
        actor_user_id=actor.user_id,
        event_type="governance.asset.created",
        to_status="draft",
        data={"content_hash": item.content_hash},
    )
    return item


async def clone_version(
    session: AsyncSession,
    *,
    actor: ActorContext,
    source: InstitutionalGovernanceAsset,
    change_summary: str,
) -> InstitutionalGovernanceAsset:
    await session.execute(
        select(Organization.id)
        .where(Organization.id == actor.organization_id)
        .with_for_update()
    )
    latest_version = await session.scalar(
        select(func.max(InstitutionalGovernanceAsset.version)).where(
            InstitutionalGovernanceAsset.organization_id
            == actor.organization_id,
            InstitutionalGovernanceAsset.code == source.code,
        )
    )
    item = InstitutionalGovernanceAsset(
        organization_id=source.organization_id,
        code=source.code,
        name=source.name,
        version=int(latest_version or 0) + 1,
        asset_type=source.asset_type,
        status="draft",
        risk_tier=source.risk_tier,
        owner_user_id=actor.user_id,
        adaptive_model_version_id=source.adaptive_model_version_id,
        ai_model_id=source.ai_model_id,
        prompt_template_id=source.prompt_template_id,
        module_policy_id=source.module_policy_id,
        intervention_type=source.intervention_type,
        evidence_rule_code=source.evidence_rule_code,
        purpose=source.purpose,
        intended_users=source.intended_users,
        limitations=source.limitations,
        prohibited_uses=source.prohibited_uses,
        documentation={
            **source.documentation,
            "change_summary": change_summary,
            "previous_governance_asset_id": str(source.id),
        },
        approval_policy=source.approval_policy,
        monitoring_policy=source.monitoring_policy,
        lineage_snapshot={
            **source.lineage_snapshot,
            "previous_governance_asset_id": str(source.id),
            "previous_content_hash": source.content_hash,
        },
    )
    item.content_hash = canonical_hash(
        {
            "name": item.name,
            "risk_tier": item.risk_tier,
            "purpose": item.purpose,
            "documentation": item.documentation,
            "approval_policy": item.approval_policy,
            "monitoring_policy": item.monitoring_policy,
            "lineage": item.lineage_snapshot,
        }
    )
    session.add(item)
    await session.flush()
    await add_event(
        session,
        asset=item,
        actor_user_id=actor.user_id,
        event_type="governance.asset.version_created",
        to_status="draft",
        data={
            "source_asset_id": str(source.id),
            "change_summary": change_summary,
        },
    )
    return item


async def review_state(
    session: AsyncSession,
    *,
    asset: InstitutionalGovernanceAsset,
    institutional_default: int,
) -> dict[str, Any]:
    reviews = list(
        (
            await session.scalars(
                select(InstitutionalGovernanceReview).where(
                    InstitutionalGovernanceReview.organization_id
                    == asset.organization_id,
                    InstitutionalGovernanceReview.asset_id == asset.id,
                )
            )
        ).all()
    )
    return review_summary(
        risk_tier=asset.risk_tier,
        approval_policy=asset.approval_policy,
        reviews=[
            {
                "review_stage": item.review_stage,
                "decision": item.decision,
                "reviewer_user_id": str(item.reviewer_user_id),
            }
            for item in reviews
        ],
        institutional_default=institutional_default,
    )


async def record_review(
    session: AsyncSession,
    *,
    actor: ActorContext,
    asset: InstitutionalGovernanceAsset,
    data: Any,
    institutional_default: int,
) -> tuple[InstitutionalGovernanceReview, dict[str, Any]]:
    if asset.owner_user_id == actor.user_id:
        raise HTTPException(
            409,
            "O responsável pelo ativo não pode aprovar a própria versão.",
        )
    if asset.status not in {"in_review", "changes_requested"}:
        raise HTTPException(409, "O ativo não está disponível para revisão.")

    item = await session.scalar(
        select(InstitutionalGovernanceReview).where(
            InstitutionalGovernanceReview.asset_id == asset.id,
            InstitutionalGovernanceReview.reviewer_user_id == actor.user_id,
            InstitutionalGovernanceReview.review_stage == data.review_stage,
        )
    )
    if item is None:
        item = InstitutionalGovernanceReview(
            organization_id=actor.organization_id,
            asset_id=asset.id,
            reviewer_user_id=actor.user_id,
            review_stage=data.review_stage,
        )
        session.add(item)
    item.decision = data.decision
    item.scorecard = data.scorecard
    item.findings = data.findings
    item.required_actions = data.required_actions
    item.comments = data.comments
    item.decided_at = utc_now()
    await session.flush()

    summary = await review_state(
        session,
        asset=asset,
        institutional_default=institutional_default,
    )
    previous = asset.status
    if data.decision == "rejected":
        asset.status = "rejected"
    elif data.decision == "changes_requested":
        asset.status = "changes_requested"
    elif summary["ready"]:
        asset.status = "approved"
        asset.approved_at = utc_now()
    else:
        asset.status = "in_review"

    await add_event(
        session,
        asset=asset,
        actor_user_id=actor.user_id,
        event_type="governance.review.decided",
        from_status=previous,
        to_status=asset.status,
        data={
            "review_id": str(item.id),
            "stage": data.review_stage,
            "decision": data.decision,
            "review_summary": summary,
        },
    )
    return item, summary


async def sync_reference_status(
    session: AsyncSession,
    *,
    asset: InstitutionalGovernanceAsset,
    active: bool,
) -> None:
    if asset.adaptive_model_version_id:
        item = await session.get(
            AdaptiveModelVersion,
            asset.adaptive_model_version_id,
        )
        if item:
            item.status = "active" if active else "suspended"
    if asset.ai_model_id:
        item = await session.get(AIModel, asset.ai_model_id)
        if item:
            item.is_active = active
    if asset.prompt_template_id:
        item = await session.get(
            AIPromptTemplate,
            asset.prompt_template_id,
        )
        if item:
            item.status = "active" if active else "suspended"
    if asset.module_policy_id:
        item = await session.get(AIModulePolicy, asset.module_policy_id)
        if item:
            item.enabled = active


async def activate_asset(
    session: AsyncSession,
    *,
    actor: ActorContext,
    asset: InstitutionalGovernanceAsset,
    minimum_documentation: float,
) -> None:
    if asset.status != "approved":
        raise HTTPException(409, "Somente versões aprovadas podem ser ativadas.")
    completeness = documentation_completeness(asset.documentation)
    if completeness < minimum_documentation:
        raise HTTPException(
            409,
            {
                "code": "GOVERNANCE_DOCUMENTATION_INCOMPLETE",
                "completeness": completeness,
                "required": minimum_documentation,
            },
        )
    blocker = await session.scalar(
        select(InstitutionalGovernanceIncident.id).where(
            InstitutionalGovernanceIncident.organization_id
            == actor.organization_id,
            InstitutionalGovernanceIncident.asset_id == asset.id,
            InstitutionalGovernanceIncident.status == "open",
            InstitutionalGovernanceIncident.severity.in_(["high", "critical"]),
        )
    )
    if blocker:
        raise HTTPException(409, "Há incidente grave aberto para esta versão.")

    active_versions = list(
        (
            await session.scalars(
                select(InstitutionalGovernanceAsset)
                .where(
                    InstitutionalGovernanceAsset.organization_id
                    == actor.organization_id,
                    InstitutionalGovernanceAsset.code == asset.code,
                    InstitutionalGovernanceAsset.status == "active",
                    InstitutionalGovernanceAsset.id != asset.id,
                )
                .with_for_update()
            )
        ).all()
    )
    for previous in active_versions:
        previous.status = "retired"
        previous.retired_at = utc_now()
        await sync_reference_status(
            session,
            asset=previous,
            active=False,
        )
        await add_event(
            session,
            asset=previous,
            actor_user_id=actor.user_id,
            event_type="governance.asset.retired_by_new_version",
            from_status="active",
            to_status="retired",
            data={"replacement_asset_id": str(asset.id)},
        )

    previous_status = asset.status
    asset.status = "active"
    asset.activated_at = utc_now()
    asset.suspended_at = None
    await sync_reference_status(session, asset=asset, active=True)
    await add_event(
        session,
        asset=asset,
        actor_user_id=actor.user_id,
        event_type="governance.asset.activated",
        from_status=previous_status,
        to_status="active",
        data={"documentation_completeness": completeness},
    )


async def suspend_asset(
    session: AsyncSession,
    *,
    actor: ActorContext,
    asset: InstitutionalGovernanceAsset,
    reason: str,
) -> InstitutionalGovernanceIncident:
    if asset.status not in {"active", "review_required", "approved"}:
        raise HTTPException(409, "O ativo não pode ser suspenso neste estado.")
    previous = asset.status
    asset.status = "suspended"
    asset.suspended_at = utc_now()
    await sync_reference_status(session, asset=asset, active=False)
    incident = InstitutionalGovernanceIncident(
        organization_id=actor.organization_id,
        asset_id=asset.id,
        opened_by_user_id=actor.user_id,
        category="manual_suspension",
        severity="high",
        status="open",
        title=f"Suspensão de {asset.name}",
        description=reason,
        evidence={"previous_status": previous},
    )
    session.add(incident)
    await session.flush()
    await add_event(
        session,
        asset=asset,
        actor_user_id=actor.user_id,
        event_type="governance.asset.suspended",
        from_status=previous,
        to_status="suspended",
        data={"incident_id": str(incident.id), "reason": reason},
    )
    return incident


async def reinstate_asset(
    session: AsyncSession,
    *,
    actor: ActorContext,
    asset: InstitutionalGovernanceAsset,
    reason: str,
) -> None:
    if asset.status != "suspended":
        raise HTTPException(409, "Somente ativos suspensos podem ser reativados.")
    open_high = await session.scalar(
        select(InstitutionalGovernanceIncident.id).where(
            InstitutionalGovernanceIncident.organization_id
            == actor.organization_id,
            InstitutionalGovernanceIncident.asset_id == asset.id,
            InstitutionalGovernanceIncident.status == "open",
            InstitutionalGovernanceIncident.severity.in_(["high", "critical"]),
        )
    )
    if open_high:
        raise HTTPException(
            409,
            "Resolva os incidentes graves antes da reativação.",
        )
    asset.status = "active"
    asset.suspended_at = None
    asset.activated_at = utc_now()
    await sync_reference_status(session, asset=asset, active=True)
    await add_event(
        session,
        asset=asset,
        actor_user_id=actor.user_id,
        event_type="governance.asset.reinstated",
        from_status="suspended",
        to_status="active",
        data={"reason": reason},
    )


async def governance_asset_for_reference(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    adaptive_model_version_id: uuid.UUID | None = None,
    ai_model_id: uuid.UUID | None = None,
    prompt_template_id: uuid.UUID | None = None,
    module_policy_id: uuid.UUID | None = None,
    intervention_type: str | None = None,
    evidence_rule_code: str | None = None,
) -> InstitutionalGovernanceAsset | None:
    filters = []
    if adaptive_model_version_id:
        filters.append(
            InstitutionalGovernanceAsset.adaptive_model_version_id
            == adaptive_model_version_id
        )
    if ai_model_id:
        filters.append(InstitutionalGovernanceAsset.ai_model_id == ai_model_id)
    if prompt_template_id:
        filters.append(
            InstitutionalGovernanceAsset.prompt_template_id
            == prompt_template_id
        )
    if module_policy_id:
        filters.append(
            InstitutionalGovernanceAsset.module_policy_id == module_policy_id
        )
    if intervention_type:
        filters.append(
            InstitutionalGovernanceAsset.intervention_type
            == intervention_type
        )
    if evidence_rule_code:
        filters.append(
            InstitutionalGovernanceAsset.evidence_rule_code
            == evidence_rule_code
        )
    if not filters:
        return None
    active = await session.scalar(
        select(InstitutionalGovernanceAsset)
        .where(
            InstitutionalGovernanceAsset.organization_id == organization_id,
            or_(*filters),
            InstitutionalGovernanceAsset.status == "active",
        )
        .order_by(InstitutionalGovernanceAsset.version.desc())
        .limit(1)
    )
    if active is not None:
        return active
    return await session.scalar(
        select(InstitutionalGovernanceAsset)
        .where(
            InstitutionalGovernanceAsset.organization_id == organization_id,
            or_(*filters),
        )
        .order_by(InstitutionalGovernanceAsset.version.desc())
        .limit(1)
    )


async def assert_reference_allowed(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    enforcement_mode: str,
    **reference: Any,
) -> dict[str, Any]:
    if enforcement_mode == "off":
        return {"allowed": True, "mode": enforcement_mode, "managed": False}
    asset = await governance_asset_for_reference(
        session,
        organization_id=organization_id,
        **reference,
    )
    if asset is None:
        if enforcement_mode == "enforce":
            raise GovernanceExecutionError(
                "O recurso não possui registro de governança institucional."
            )
        return {
            "allowed": True,
            "mode": enforcement_mode,
            "managed": False,
            "reason": "legacy_unmanaged",
        }
    if asset.status not in ACTIVE_STATUSES:
        if enforcement_mode == "enforce":
            raise GovernanceExecutionError(
                f"O recurso está bloqueado pela governança: {asset.status}."
            )
        return {
            "allowed": True,
            "mode": enforcement_mode,
            "managed": True,
            "asset_id": str(asset.id),
            "status": asset.status,
            "warning": "governance_not_active",
        }
    return {
        "allowed": True,
        "mode": enforcement_mode,
        "managed": True,
        "asset_id": str(asset.id),
        "status": asset.status,
    }


async def assert_ai_execution_allowed(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    enforcement_mode: str,
    model_id: uuid.UUID | None,
    prompt_template_id: uuid.UUID | None,
    module_policy_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    results = []
    references = (
        {"ai_model_id": model_id} if model_id else None,
        {"prompt_template_id": prompt_template_id}
        if prompt_template_id
        else None,
        {"module_policy_id": module_policy_id}
        if module_policy_id
        else None,
    )
    if enforcement_mode == "enforce" and not any(references):
        raise GovernanceExecutionError(
            "A execução de IA não possui referência governada selecionada."
        )
    for reference in references:
        if reference:
            results.append(
                await assert_reference_allowed(
                    session,
                    organization_id=organization_id,
                    enforcement_mode=enforcement_mode,
                    **reference,
                )
            )
    return results


async def assert_adaptive_model_allowed(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    enforcement_mode: str,
    model_version_id: uuid.UUID,
) -> dict[str, Any]:
    return await assert_reference_allowed(
        session,
        organization_id=organization_id,
        enforcement_mode=enforcement_mode,
        adaptive_model_version_id=model_version_id,
    )


def _split_drift(rows: list[tuple[datetime, float]]) -> float | None:
    if len(rows) < 4:
        return None
    ordered = sorted(rows, key=lambda row: row[0])
    middle = len(ordered) // 2
    early = _average([value for _, value in ordered[:middle]])
    late = _average([value for _, value in ordered[middle:]])
    if early is None or late is None:
        return None
    return round(abs(late - early), 4)


async def _ai_metrics(
    session: AsyncSession,
    *,
    asset: InstitutionalGovernanceAsset,
    start: datetime,
    end: datetime,
    minimum_group_size: int,
) -> dict[str, Any]:
    query = select(AIGenerationRequest).where(
        AIGenerationRequest.organization_id == asset.organization_id,
        AIGenerationRequest.created_at >= start,
        AIGenerationRequest.created_at <= end,
    )
    if asset.ai_model_id:
        query = query.where(AIGenerationRequest.model_id == asset.ai_model_id)
    if asset.prompt_template_id:
        query = query.where(
            AIGenerationRequest.prompt_template_id
            == asset.prompt_template_id
        )
    if asset.module_policy_id:
        policy = await session.get(AIModulePolicy, asset.module_policy_id)
        if policy:
            query = query.where(
                AIGenerationRequest.module_name == policy.module_name
            )
    requests = list((await session.scalars(query)).all())
    request_ids = [item.id for item in requests]
    results = (
        list(
            (
                await session.scalars(
                    select(AIGenerationResult).where(
                        AIGenerationResult.request_id.in_(request_ids)
                    )
                )
            ).all()
        )
        if request_ids
        else []
    )
    result_ids = [item.id for item in results]
    evaluations = (
        list(
            (
                await session.scalars(
                    select(AIQualityEvaluation).where(
                        AIQualityEvaluation.result_id.in_(result_ids)
                    )
                )
            ).all()
        )
        if result_ids
        else []
    )
    reviews = (
        list(
            (
                await session.scalars(
                    select(AIGenerationReview).where(
                        AIGenerationReview.result_id.in_(result_ids)
                    )
                )
            ).all()
        )
        if result_ids
        else []
    )

    quality_values = [
        mean(
            [
                item.structural_validity,
                item.pedagogical_alignment,
                item.source_coverage,
                item.age_appropriateness,
                item.narrative_consistency,
                item.confidence_score,
            ]
        )
        for item in evaluations
    ]
    safety_values = [item.safety_score for item in evaluations]
    approved = sum(item.decision == "approved" for item in reviews)
    failures = sum(
        item.status in {"failed", "cancelled", "expired"}
        for item in requests
    )
    success_rows = [
        (
            item.created_at,
            0.0
            if item.status in {"failed", "cancelled", "expired"}
            else 1.0,
        )
        for item in requests
    ]
    cohorts: dict[str, list[float]] = defaultdict(list)
    for item in requests:
        key = item.module_name
        cohorts[key].append(
            0.0
            if item.status in {"failed", "cancelled", "expired"}
            else 1.0
        )
    cohort_metrics = [
        {
            "cohort": key,
            "sample_size": len(values),
            "success_rate": round(mean(values), 4),
        }
        for key, values in cohorts.items()
        if len(values) >= minimum_group_size
    ]
    fairness, disparity = fairness_from_cohorts(
        [item["success_rate"] for item in cohort_metrics]
    )
    return {
        "sample_size": len(requests),
        "quality_score": _average(quality_values),
        "safety_score": _average(safety_values),
        "effectiveness_score": _rate(approved, len(reviews)),
        "fairness_score": fairness,
        "drift_score": _split_drift(success_rows),
        "error_rate": _rate(failures, len(requests)),
        "recurrence_rate": None,
        "cohort_metrics": cohort_metrics,
        "metrics": {
            "request_count": len(requests),
            "result_count": len(results),
            "review_count": len(reviews),
            "approved_review_count": approved,
            "quality_evaluation_count": len(evaluations),
            "cohort_disparity": disparity,
        },
    }


async def _intervention_metrics(
    session: AsyncSession,
    *,
    asset: InstitutionalGovernanceAsset,
    start: datetime,
    end: datetime,
    minimum_group_size: int,
) -> dict[str, Any]:
    query = (
        select(
            InterventionEvaluationCheckpoint,
            LearningIntervention,
        )
        .join(
            LearningIntervention,
            LearningIntervention.id
            == InterventionEvaluationCheckpoint.intervention_id,
        )
        .where(
            InterventionEvaluationCheckpoint.organization_id
            == asset.organization_id,
            InterventionEvaluationCheckpoint.evaluated_at.is_not(None),
            InterventionEvaluationCheckpoint.evaluated_at >= start,
            InterventionEvaluationCheckpoint.evaluated_at <= end,
            InterventionEvaluationCheckpoint.privacy_suppressed.is_(False),
        )
    )
    if asset.intervention_type:
        query = query.where(
            LearningIntervention.intervention_type
            == InterventionType(asset.intervention_type)
        )
    if asset.adaptive_model_version_id:
        query = query.join(
            AdaptiveRecommendation,
            AdaptiveRecommendation.id
            == LearningIntervention.source_recommendation_id,
        ).where(
            AdaptiveRecommendation.model_version_id
            == asset.adaptive_model_version_id
        )
    if asset.evidence_rule_code:
        query = query.join(
            LearningAlert,
            LearningAlert.id == LearningIntervention.alert_id,
        ).where(
            LearningAlert.rule_code == asset.evidence_rule_code
        )
    rows = list((await session.execute(query)).all())
    checkpoints = [row[0] for row in rows]
    comparable = [item for item in checkpoints if item.comparable]
    successful = [
        item for item in comparable if item.improved or item.target_met
    ]
    recurrence = [item for item in comparable if item.alert_recurred]
    quality_score = _rate(len(comparable), len(checkpoints))
    effectiveness = _rate(len(successful), len(comparable))
    recurrence_rate = _rate(len(recurrence), len(comparable))

    temporal = [
        (
            item.evaluated_at,
            1.0 if item.improved or item.target_met else 0.0,
        )
        for item in comparable
        if item.evaluated_at
    ]
    cohorts: dict[str, list[float]] = defaultdict(list)
    for item in comparable:
        key = (
            str(item.classroom_id)
            if item.classroom_id
            else "organization"
        )
        cohorts[key].append(
            1.0 if item.improved or item.target_met else 0.0
        )
    cohort_metrics = [
        {
            "cohort": key,
            "sample_size": len(values),
            "effectiveness_rate": round(mean(values), 4),
        }
        for key, values in cohorts.items()
        if len(values) >= minimum_group_size
    ]
    fairness, disparity = fairness_from_cohorts(
        [item["effectiveness_rate"] for item in cohort_metrics]
    )
    return {
        "sample_size": len(checkpoints),
        "quality_score": quality_score,
        "safety_score": None,
        "effectiveness_score": effectiveness,
        "fairness_score": fairness,
        "drift_score": _split_drift(temporal),
        "error_rate": _rate(
            len(checkpoints) - len(comparable),
            len(checkpoints),
        ),
        "recurrence_rate": recurrence_rate,
        "cohort_metrics": cohort_metrics,
        "metrics": {
            "checkpoint_count": len(checkpoints),
            "comparable_count": len(comparable),
            "successful_count": len(successful),
            "recurrence_count": len(recurrence),
            "cohort_disparity": disparity,
        },
    }


async def monitor_asset(
    session: AsyncSession,
    *,
    asset: InstitutionalGovernanceAsset,
    period_start: date,
    period_end: date,
    background_job_id: uuid.UUID,
    minimum_group_size: int,
    open_incidents: bool,
) -> InstitutionalGovernanceSnapshot:
    start, end = date_bounds(period_start, period_end)
    if asset.asset_type in {
        "ai_model",
        "prompt_template",
        "module_policy",
    }:
        result = await _ai_metrics(
            session,
            asset=asset,
            start=start,
            end=end,
            minimum_group_size=minimum_group_size,
        )
    else:
        result = await _intervention_metrics(
            session,
            asset=asset,
            start=start,
            end=end,
            minimum_group_size=minimum_group_size,
        )

    privacy_suppressed = (
        int(result["sample_size"]) < minimum_group_size
    )
    breaches = (
        []
        if privacy_suppressed
        else threshold_breaches(result, asset.monitoring_policy)
    )
    existing = await session.scalar(
        select(InstitutionalGovernanceSnapshot).where(
            InstitutionalGovernanceSnapshot.organization_id
            == asset.organization_id,
            InstitutionalGovernanceSnapshot.asset_id == asset.id,
            InstitutionalGovernanceSnapshot.period_start == period_start,
            InstitutionalGovernanceSnapshot.period_end == period_end,
        )
    )
    snapshot = existing or InstitutionalGovernanceSnapshot(
        organization_id=asset.organization_id,
        asset_id=asset.id,
        period_start=period_start,
        period_end=period_end,
    )
    snapshot.background_job_id = background_job_id
    snapshot.sample_size = int(result["sample_size"])
    snapshot.quality_score = result["quality_score"]
    snapshot.safety_score = result["safety_score"]
    snapshot.effectiveness_score = result["effectiveness_score"]
    snapshot.fairness_score = result["fairness_score"]
    snapshot.drift_score = result["drift_score"]
    snapshot.error_rate = result["error_rate"]
    snapshot.recurrence_rate = result["recurrence_rate"]
    snapshot.complaint_count = int(
        await session.scalar(
            select(func.count(InstitutionalGovernanceIncident.id)).where(
                InstitutionalGovernanceIncident.organization_id
                == asset.organization_id,
                InstitutionalGovernanceIncident.asset_id == asset.id,
                InstitutionalGovernanceIncident.status == "open",
                InstitutionalGovernanceIncident.category.in_(
                    ["complaint", "quality", "safety", "privacy"]
                ),
            )
        )
        or 0
    )
    snapshot.threshold_breached = bool(breaches)
    snapshot.threshold_breaches = breaches
    snapshot.cohort_metrics = result["cohort_metrics"]
    snapshot.metrics = result["metrics"]
    snapshot.privacy_suppressed = privacy_suppressed
    snapshot.calculated_at = utc_now()
    if existing is None:
        session.add(snapshot)
    await session.flush()

    if breaches and open_incidents:
        duplicate = await session.scalar(
            select(InstitutionalGovernanceIncident.id).where(
                InstitutionalGovernanceIncident.organization_id
                == asset.organization_id,
                InstitutionalGovernanceIncident.asset_id == asset.id,
                InstitutionalGovernanceIncident.category
                == "monitoring_threshold",
                InstitutionalGovernanceIncident.status == "open",
            )
        )
        if duplicate is None:
            severity = (
                "critical"
                if asset.risk_tier == "critical"
                else "high"
                if asset.risk_tier == "high"
                else "moderate"
            )
            incident = InstitutionalGovernanceIncident(
                organization_id=asset.organization_id,
                asset_id=asset.id,
                snapshot_id=snapshot.id,
                category="monitoring_threshold",
                severity=severity,
                status="open",
                title=f"Limite de governança excedido: {asset.name}",
                description=(
                    "O monitoramento encontrou indicadores fora dos "
                    "limites institucionais. A suspensão não é automática; "
                    "uma decisão humana é necessária."
                ),
                evidence={"breaches": breaches},
            )
            session.add(incident)
            await session.flush()
            previous = asset.status
            if asset.status == "active":
                asset.status = "review_required"
            await add_event(
                session,
                asset=asset,
                actor_user_id=None,
                event_type="governance.monitoring.threshold_breached",
                from_status=previous,
                to_status=asset.status,
                data={
                    "snapshot_id": str(snapshot.id),
                    "incident_id": str(incident.id),
                    "breaches": breaches,
                },
            )
    return snapshot


async def refresh_monitoring(
    session: AsyncSession,
    *,
    actor: ActorContext,
    period_start: date | None,
    period_end: date | None,
    asset_ids: list[uuid.UUID],
    open_incidents: bool,
    lookback_days: int,
    minimum_group_size: int,
) -> dict[str, Any]:
    start, end = monitoring_period(
        period_start,
        period_end,
        lookback_days,
    )
    asset_query = select(InstitutionalGovernanceAsset).where(
        InstitutionalGovernanceAsset.organization_id
        == actor.organization_id,
        InstitutionalGovernanceAsset.status.in_(
            ["approved", "active", "review_required", "suspended"]
        ),
    )
    if asset_ids:
        asset_query = asset_query.where(
            InstitutionalGovernanceAsset.id.in_(asset_ids)
        )
    assets = list((await session.scalars(asset_query)).all())
    latest = max(
        [item.updated_at for item in assets if item.updated_at],
        default=None,
    )
    source_version = (
        await session.execute(
            select(
                func.count(AIGenerationRequest.id),
                func.max(AIGenerationRequest.created_at),
            ).where(
                AIGenerationRequest.organization_id
                == actor.organization_id
            )
        )
    ).one()
    checkpoint_version = (
        await session.execute(
            select(
                func.count(InterventionEvaluationCheckpoint.id),
                func.max(InterventionEvaluationCheckpoint.updated_at),
            ).where(
                InterventionEvaluationCheckpoint.organization_id
                == actor.organization_id
            )
        )
    ).one()
    fingerprint = canonical_hash(
        {
            "organization_id": actor.organization_id,
            "period_start": start,
            "period_end": end,
            "asset_ids": sorted(str(item.id) for item in assets),
            "latest_asset_update": latest,
            "ai_request_count": int(source_version[0] or 0),
            "latest_ai_request": source_version[1],
            "checkpoint_count": int(checkpoint_version[0] or 0),
            "latest_checkpoint": checkpoint_version[1],
            "open_incidents": open_incidents,
        }
    )
    key = f"institutional-governance:{fingerprint[:48]}"
    job = await session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.organization_id == actor.organization_id,
            BackgroundJob.idempotency_key == key,
        )
    )
    if job and job.status == "completed":
        return {
            "job_id": str(job.id),
            "reused": True,
            **job.result_reference,
        }
    if job is None:
        job = BackgroundJob(
            organization_id=actor.organization_id,
            requested_by_user_id=actor.user_id,
            job_type="institutional_governance_monitoring",
            queue_name="default",
            module_name="institutional_governance",
            entity_type="organization",
            entity_id=actor.organization_id,
            status="processing",
            priority=35,
            progress_percent=5,
            current_step="Preparando monitoramento",
            total_steps=max(1, len(assets)),
            idempotency_key=key,
            input_snapshot={
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "asset_ids": [str(item.id) for item in assets],
                "open_incidents": open_incidents,
            },
            queued_at=utc_now(),
            started_at=utc_now(),
        )
        session.add(job)
        await session.flush()
    else:
        job.status = "processing"
        job.progress_percent = 5

    snapshots: list[InstitutionalGovernanceSnapshot] = []
    for index, asset in enumerate(assets, start=1):
        snapshot = await monitor_asset(
            session,
            asset=asset,
            period_start=start,
            period_end=end,
            background_job_id=job.id,
            minimum_group_size=minimum_group_size,
            open_incidents=open_incidents,
        )
        snapshots.append(snapshot)
        job.progress_percent = round(index / max(1, len(assets)) * 95)
        job.current_step = f"Monitorando {asset.name}"

    result = {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "assets_monitored": len(assets),
        "threshold_breaches": sum(
            item.threshold_breached for item in snapshots
        ),
        "privacy_suppressed": sum(
            item.privacy_suppressed for item in snapshots
        ),
    }
    job.status = "completed"
    job.progress_percent = 100
    job.current_step = "Monitoramento concluído"
    job.result_reference = result
    job.completed_at = utc_now()
    await session.flush()
    return {"job_id": str(job.id), "reused": False, **result}


async def compare_versions(
    session: AsyncSession,
    *,
    left: InstitutionalGovernanceAsset,
    right: InstitutionalGovernanceAsset,
) -> dict[str, Any]:
    if left.code != right.code:
        raise HTTPException(409, "Somente versões do mesmo código podem ser comparadas.")
    snapshots = list(
        (
            await session.scalars(
                select(InstitutionalGovernanceSnapshot)
                .where(
                    InstitutionalGovernanceSnapshot.asset_id.in_(
                        [left.id, right.id]
                    )
                )
                .order_by(
                    InstitutionalGovernanceSnapshot.calculated_at.desc()
                )
            )
        ).all()
    )
    latest: dict[uuid.UUID, InstitutionalGovernanceSnapshot] = {}
    for item in snapshots:
        latest.setdefault(item.asset_id, item)
    return {
        "code": left.code,
        "left": {
            "id": str(left.id),
            "version": left.version,
            "status": left.status,
            "content_hash": left.content_hash,
            "documentation_completeness": documentation_completeness(
                left.documentation
            ),
            "latest_snapshot": snapshot_summary(latest.get(left.id)),
        },
        "right": {
            "id": str(right.id),
            "version": right.version,
            "status": right.status,
            "content_hash": right.content_hash,
            "documentation_completeness": documentation_completeness(
                right.documentation
            ),
            "latest_snapshot": snapshot_summary(latest.get(right.id)),
        },
        "documentation_diff": compare_documents(
            left.documentation,
            right.documentation,
        ),
        "monitoring_policy_diff": compare_documents(
            left.monitoring_policy,
            right.monitoring_policy,
        ),
        "approval_policy_diff": compare_documents(
            left.approval_policy,
            right.approval_policy,
        ),
    }


def snapshot_summary(
    item: InstitutionalGovernanceSnapshot | None,
) -> dict[str, Any] | None:
    if item is None:
        return None
    suppressed = item.privacy_suppressed
    return {
        "id": str(item.id),
        "period_start": item.period_start,
        "period_end": item.period_end,
        "sample_size": item.sample_size,
        "quality_score": None if suppressed else item.quality_score,
        "safety_score": None if suppressed else item.safety_score,
        "effectiveness_score": (
            None if suppressed else item.effectiveness_score
        ),
        "fairness_score": None if suppressed else item.fairness_score,
        "drift_score": None if suppressed else item.drift_score,
        "error_rate": None if suppressed else item.error_rate,
        "recurrence_rate": (
            None if suppressed else item.recurrence_rate
        ),
        "threshold_breached": item.threshold_breached,
        "threshold_breaches": item.threshold_breaches,
        "privacy_suppressed": suppressed,
        "calculated_at": item.calculated_at,
    }


async def bootstrap_assets(
    session: AsyncSession,
    *,
    actor: ActorContext,
    options: Any,
) -> dict[str, int]:
    await session.execute(
        select(Organization.id)
        .where(Organization.id == actor.organization_id)
        .with_for_update()
    )
    created = defaultdict(int)

    async def add_if_missing(
        *,
        code: str,
        name: str,
        asset_type: str,
        reference: dict[str, Any],
        risk_tier: str,
        purpose: str,
        governance_version: int = 1,
    ) -> None:
        exists = await session.scalar(
            select(InstitutionalGovernanceAsset.id).where(
                InstitutionalGovernanceAsset.organization_id
                == actor.organization_id,
                InstitutionalGovernanceAsset.code == code,
                InstitutionalGovernanceAsset.version
                == governance_version,
            )
        )
        if exists:
            return
        class Data:
            pass
        data = Data()
        data.code = code
        data.name = name
        data.version = governance_version
        data.asset_type = asset_type
        data.risk_tier = risk_tier
        data.adaptive_model_version_id = reference.get(
            "adaptive_model_version_id"
        )
        data.ai_model_id = reference.get("ai_model_id")
        data.prompt_template_id = reference.get("prompt_template_id")
        data.module_policy_id = reference.get("module_policy_id")
        data.intervention_type = reference.get("intervention_type")
        data.evidence_rule_code = reference.get("evidence_rule_code")
        data.purpose = purpose
        data.intended_users = ["professores", "gestores"]
        data.limitations = [
            "Requer validação institucional antes da ativação."
        ]
        data.prohibited_uses = [
            "Decisão automática sem supervisão humana."
        ]
        data.documentation = {
            "summary": purpose,
            "data_sources": ["registros institucionais do EduCode"],
            "decision_logic": "Consultar a referência vinculada.",
            "human_oversight": "Aprovação institucional obrigatória.",
            "known_limitations": data.limitations,
            "validation_evidence": "A preencher durante a revisão.",
            "rollback_plan": "Suspender o ativo e reativar a versão anterior.",
        }
        data.approval_policy = {}
        data.monitoring_policy = {}
        await create_asset(session, actor=actor, data=data)
        created[asset_type] += 1

    if options.include_adaptive_models:
        rows = list(
            (
                await session.scalars(
                    select(AdaptiveModelVersion).where(
                        AdaptiveModelVersion.organization_id
                        == actor.organization_id
                    )
                )
            ).all()
        )
        for item in rows:
            await add_if_missing(
                code=f"adaptive:{item.code}",
                name=item.name,
                asset_type="adaptive_model",
                reference={"adaptive_model_version_id": item.id},
                risk_tier="high",
                purpose=item.description or "Modelo adaptativo institucional.",
                governance_version=item.version,
            )

    if options.include_ai_models:
        rows = list(
            (
                await session.scalars(
                    select(AIModel).where(
                        AIModel.organization_id == actor.organization_id
                    )
                )
            ).all()
        )
        for item in rows:
            await add_if_missing(
                code=f"ai-model:{item.model_identifier}",
                name=item.name,
                asset_type="ai_model",
                reference={"ai_model_id": item.id},
                risk_tier="high",
                purpose="Modelo de IA autorizado para módulos institucionais.",
            )

    if options.include_prompt_templates:
        rows = list(
            (
                await session.scalars(
                    select(AIPromptTemplate).where(
                        AIPromptTemplate.organization_id
                        == actor.organization_id
                    )
                )
            ).all()
        )
        for item in rows:
            await add_if_missing(
                code=f"prompt:{item.purpose}",
                name=item.name,
                asset_type="prompt_template",
                reference={"prompt_template_id": item.id},
                risk_tier="moderate",
                purpose=f"Template institucional para {item.purpose}.",
                governance_version=item.version,
            )

    if options.include_module_policies:
        rows = list(
            (
                await session.scalars(
                    select(AIModulePolicy).where(
                        AIModulePolicy.organization_id
                        == actor.organization_id
                    )
                )
            ).all()
        )
        for item in rows:
            await add_if_missing(
                code=f"ai-policy:{item.module_name}",
                name=f"Política de IA — {item.module_name}",
                asset_type="module_policy",
                reference={"module_policy_id": item.id},
                risk_tier="high",
                purpose="Controlar ações, modelos, custos e dados do módulo.",
            )

    if options.include_intervention_types:
        for item in InterventionType:
            await add_if_missing(
                code=f"intervention:{item.value}",
                name=f"Estratégia — {item.value}",
                asset_type="intervention_strategy",
                reference={"intervention_type": item.value},
                risk_tier="high",
                purpose="Estratégia institucional de intervenção pedagógica.",
            )

    if options.include_evidence_rules:
        rules = list(
            (
                await session.scalars(
                    select(LearningAlert.rule_code)
                    .where(
                        LearningAlert.organization_id
                        == actor.organization_id
                    )
                    .distinct()
                )
            ).all()
        )
        for rule in rules:
            await add_if_missing(
                code=f"evidence-rule:{rule}",
                name=f"Regra de evidência — {rule}",
                asset_type="evidence_rule",
                reference={"evidence_rule_code": rule},
                risk_tier="moderate",
                purpose="Regra que transforma evidências em alerta pedagógico.",
            )

    return dict(created)


def governance_csv(
    assets: list[InstitutionalGovernanceAsset],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "code",
            "name",
            "version",
            "asset_type",
            "status",
            "risk_tier",
            "owner_user_id",
            "content_hash",
            "submitted_at",
            "approved_at",
            "activated_at",
            "suspended_at",
            "retired_at",
        ]
    )
    for item in assets:
        writer.writerow(
            [
                item.code,
                item.name,
                item.version,
                item.asset_type,
                item.status,
                item.risk_tier,
                item.owner_user_id,
                item.content_hash,
                item.submitted_at,
                item.approved_at,
                item.activated_at,
                item.suspended_at,
                item.retired_at,
            ]
        )
    return output.getvalue()
