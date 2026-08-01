from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import AdaptiveRecommendation
from app.models.analytics import (
    AlertStatus,
    InterventionStatus,
    LearningAlert,
    LearningIntervention,
    LearningInterventionEvent,
)
from app.models.education import ClassroomEnrollment
from app.services.consolidated_audit import append_domain_audit

from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import can_transition, safe_student_actions
from .schemas import (
    InterventionComplete,
    InterventionTransition,
    ProposalCreate,
    ProposalReview,
    StudentAcknowledgement,
)
from .services import (
    ACTIVE_INTERVENTION_STATUSES,
    add_event,
    alert_is_hq_linked,
    approve_proposal,
    complete_intervention,
    create_proposal,
    user_can_access_intervention,
)

router = APIRouter(
    prefix="/intervention-orchestration",
    tags=["intervention-orchestration"],
)
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

TEACHER_ROLES = {
    "OWNER",
    "ADMIN",
    "ORG_ADMIN",
    "PLATFORM_ADMIN",
    "TEACHER",
    "COORDINATOR",
    "PEDAGOGICAL_COORDINATOR",
}
HQ_RECOMMENDATION_SOURCE_KINDS = {
    "comic_reader_alert",
    "hq_learning_analytics",
}


def require_teacher(actor: ActorContext) -> None:
    roles = {str(role).upper() for role in actor.roles}
    if not roles.intersection(TEACHER_ROLES):
        raise HTTPException(
            status_code=403,
            detail="A operação exige perfil docente ou de gestão.",
        )


async def recommendation_or_404(
    session: AsyncSession,
    actor: ActorContext,
    recommendation_id: uuid.UUID,
    *,
    lock: bool = False,
) -> AdaptiveRecommendation:
    statement = select(AdaptiveRecommendation).where(
        AdaptiveRecommendation.organization_id == actor.organization_id,
        AdaptiveRecommendation.id == recommendation_id,
        AdaptiveRecommendation.source_kind.in_(HQ_RECOMMENDATION_SOURCE_KINDS),
    )
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        raise HTTPException(404, "Proposta de intervenção não encontrada.")
    return item


async def intervention_or_404(
    session: AsyncSession,
    actor: ActorContext,
    intervention_id: uuid.UUID,
    *,
    lock: bool = False,
) -> LearningIntervention:
    statement = select(LearningIntervention).where(
        LearningIntervention.organization_id == actor.organization_id,
        LearningIntervention.id == intervention_id,
    )
    if lock:
        statement = statement.with_for_update()
    item = await session.scalar(statement)
    if item is None:
        raise HTTPException(404, "Intervenção não encontrada.")
    return item


def recommendation_payload(item: AdaptiveRecommendation) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "student_id": str(item.student_id) if item.student_id else None,
        "classroom_id": str(item.classroom_id) if item.classroom_id else None,
        "source_alert_id": str(item.source_alert_id) if item.source_alert_id else None,
        "source_comic_release_id": (
            str(item.source_comic_release_id)
            if item.source_comic_release_id
            else None
        ),
        "source_ai_request_id": (
            str(item.source_ai_request_id) if item.source_ai_request_id else None
        ),
        "ai_requested": item.source_ai_request_id is not None,
        "recommendation_type": item.recommendation_type,
        "status": item.status,
        "priority": item.priority,
        "title": item.title,
        "rationale": item.rationale,
        "target_dimension_type": item.target_dimension_type,
        "target_dimension_code": item.target_dimension_code,
        "target_mastery": item.target_mastery,
        "confidence_score": item.confidence_score,
        "evidence_summary": item.evidence_summary,
        "proposed_materials": item.proposed_materials,
        "created_by_ai": item.created_by_ai,
        "review_notes": item.review_notes,
        "reviewed_at": item.reviewed_at,
        "created_at": item.created_at,
    }


def intervention_payload(item: LearningIntervention) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "teacher_id": str(item.teacher_id),
        "student_id": str(item.student_id) if item.student_id else None,
        "classroom_id": str(item.classroom_id) if item.classroom_id else None,
        "alert_id": str(item.alert_id) if item.alert_id else None,
        "assignment_id": str(item.assignment_id) if item.assignment_id else None,
        "source_recommendation_id": (
            str(item.source_recommendation_id)
            if item.source_recommendation_id
            else None
        ),
        "comic_release_id": (
            str(item.comic_release_id) if item.comic_release_id else None
        ),
        "adaptive_path_id": (
            str(item.adaptive_path_id) if item.adaptive_path_id else None
        ),
        "accessible_resource_version_id": (
            str(item.accessible_resource_version_id)
            if item.accessible_resource_version_id
            else None
        ),
        "ai_request_id": str(item.ai_request_id) if item.ai_request_id else None,
        "intervention_type": item.intervention_type.value,
        "status": item.status.value,
        "reason": item.reason,
        "notes": item.notes,
        "expected_outcome": item.expected_outcome,
        "result_summary": item.result_summary,
        "plan_snapshot": item.plan_snapshot,
        "baseline_snapshot": item.baseline_snapshot,
        "target_snapshot": item.target_snapshot,
        "human_review_required": item.human_review_required,
        "approved_at": item.approved_at,
        "started_at": item.started_at,
        "due_at": item.due_at,
        "evaluation_due_at": item.evaluation_due_at,
        "created_at": item.created_at,
        "completed_at": item.completed_at,
    }


def student_intervention_payload(item: LearningIntervention) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "intervention_type": item.intervention_type.value,
        "status": item.status.value,
        "expected_outcome": item.expected_outcome,
        "student_message": "Plano de apoio definido e revisado pelo professor.",
        "result_summary": item.result_summary,
        "actions": safe_student_actions(item.plan_snapshot),
        "comic_release_id": (
            str(item.comic_release_id) if item.comic_release_id else None
        ),
        "assignment_id": str(item.assignment_id) if item.assignment_id else None,
        "adaptive_path_id": (
            str(item.adaptive_path_id) if item.adaptive_path_id else None
        ),
        "due_at": item.due_at,
        "created_at": item.created_at,
        "completed_at": item.completed_at,
        "scope": "student" if item.student_id else "classroom",
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "sprint": "16.7.1",
        "module": "intervention-orchestration",
    }


@router.get("/dashboard")
async def dashboard(session: SessionDep, actor: ActorDep):
    require_teacher(actor)
    pending = await session.scalar(
        select(func.count(AdaptiveRecommendation.id)).where(
            AdaptiveRecommendation.organization_id == actor.organization_id,
            AdaptiveRecommendation.source_kind.in_(
                HQ_RECOMMENDATION_SOURCE_KINDS
            ),
            AdaptiveRecommendation.status == "pending_review",
        )
    )
    open_alerts = await session.scalar(
        select(func.count(LearningAlert.id)).where(
            LearningAlert.organization_id == actor.organization_id,
            LearningAlert.status.in_(
                [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]
            ),
        )
    )
    planned = await session.scalar(
        select(func.count(LearningIntervention.id)).where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.source_recommendation_id.is_not(None),
            LearningIntervention.status == InterventionStatus.PLANNED,
        )
    )
    active = await session.scalar(
        select(func.count(LearningIntervention.id)).where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.source_recommendation_id.is_not(None),
            LearningIntervention.status == InterventionStatus.ACTIVE,
        )
    )
    overdue = await session.scalar(
        select(func.count(LearningIntervention.id)).where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.source_recommendation_id.is_not(None),
            LearningIntervention.status.in_(
                [InterventionStatus.PLANNED, InterventionStatus.ACTIVE]
            ),
            LearningIntervention.due_at.is_not(None),
            LearningIntervention.due_at < datetime.now(UTC),
        )
    )
    return {
        "open_alerts": int(open_alerts or 0),
        "pending_proposals": int(pending or 0),
        "planned_interventions": int(planned or 0),
        "active_interventions": int(active or 0),
        "overdue_interventions": int(overdue or 0),
        "human_approval_required": True,
    }


@router.get("/alerts")
async def list_candidate_alerts(
    session: SessionDep,
    actor: ActorDep,
    limit: int = Query(default=100, ge=1, le=500),
):
    require_teacher(actor)
    candidates = list(
        (
            await session.scalars(
                select(LearningAlert)
                .where(
                    LearningAlert.organization_id == actor.organization_id,
                    LearningAlert.status.in_(
                        [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]
                    ),
                )
                .order_by(LearningAlert.created_at.desc())
                .limit(500)
            )
        ).all()
    )
    items: list[LearningAlert] = []
    for item in candidates:
        if await alert_is_hq_linked(
            session,
            organization_id=actor.organization_id,
            alert=item,
        ):
            items.append(item)
        if len(items) >= limit:
            break

    pending_alert_ids = set(
        (
            await session.scalars(
                select(AdaptiveRecommendation.source_alert_id).where(
                    AdaptiveRecommendation.organization_id
                    == actor.organization_id,
                    AdaptiveRecommendation.source_kind.in_(
                        HQ_RECOMMENDATION_SOURCE_KINDS
                    ),
                    AdaptiveRecommendation.source_alert_id.is_not(None),
                    AdaptiveRecommendation.status == "pending_review",
                )
            )
        ).all()
    )
    active_alert_ids = set(
        (
            await session.scalars(
                select(LearningIntervention.alert_id).where(
                    LearningIntervention.organization_id
                    == actor.organization_id,
                    LearningIntervention.alert_id.is_not(None),
                    LearningIntervention.status.in_(
                        ACTIVE_INTERVENTION_STATUSES
                    ),
                )
            )
        ).all()
    )
    blocked_alert_ids = pending_alert_ids | active_alert_ids
    return [
        {
            "id": str(item.id),
            "student_id": str(item.student_id) if item.student_id else None,
            "classroom_id": (
                str(item.classroom_id) if item.classroom_id else None
            ),
            "assignment_id": (
                str(item.assignment_id) if item.assignment_id else None
            ),
            "alert_type": item.alert_type,
            "severity": item.severity.value,
            "status": item.status.value,
            "title": item.title,
            "description": item.description,
            "explanation": item.explanation,
            "evidence": item.evidence,
            "rule_code": item.rule_code,
            "created_at": item.created_at,
            "has_proposal": item.id in blocked_alert_ids,
        }
        for item in items
    ]


@router.post(
    "/proposals/from-alert/{alert_id}",
    status_code=status.HTTP_201_CREATED,
)
async def proposal_from_alert(
    alert_id: uuid.UUID,
    data: ProposalCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_teacher(actor)
    alert = await session.scalar(
        select(LearningAlert).where(
            LearningAlert.organization_id == actor.organization_id,
            LearningAlert.id == alert_id,
        )
    )
    if alert is None:
        raise HTTPException(404, "Alerta pedagógico não encontrado.")
    if alert.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}:
        raise HTTPException(409, "O alerta não está aberto para intervenção.")

    item = await create_proposal(
        session,
        actor=actor,
        alert=alert,
        use_ai=data.use_ai,
        teacher_note=data.teacher_note,
        target_mastery=data.target_mastery,
    )
    item.evidence_summary = {
        **item.evidence_summary,
        "proposed_due_days": data.due_days,
        "proposed_evaluation_days": data.evaluation_days,
    }
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_orchestration",
        action="intervention.proposal.created",
        entity_type="adaptive_recommendation",
        entity_id=item.id,
        details={
            "alert_id": str(alert.id),
            "ai_requested": item.source_ai_request_id is not None,
            "created_by_ai": item.created_by_ai,
            "human_approval_required": True,
        },
    )
    await session.commit()
    await session.refresh(item)
    return recommendation_payload(item)


@router.get("/proposals")
async def list_proposals(
    session: SessionDep,
    actor: ActorDep,
    proposal_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
):
    require_teacher(actor)
    statement = select(AdaptiveRecommendation).where(
        AdaptiveRecommendation.organization_id == actor.organization_id,
        AdaptiveRecommendation.source_kind.in_(HQ_RECOMMENDATION_SOURCE_KINDS),
    )
    if proposal_status:
        statement = statement.where(
            AdaptiveRecommendation.status == proposal_status
        )
    items = list(
        (
            await session.scalars(
                statement.order_by(AdaptiveRecommendation.created_at.desc()).limit(
                    limit
                )
            )
        ).all()
    )
    return [recommendation_payload(item) for item in items]


@router.patch("/proposals/{recommendation_id}")
async def review_proposal(
    recommendation_id: uuid.UUID,
    data: ProposalReview,
    session: SessionDep,
    actor: ActorDep,
):
    require_teacher(actor)
    item = await recommendation_or_404(
        session,
        actor,
        recommendation_id,
        lock=True,
    )
    if item.status != "pending_review":
        raise HTTPException(409, "A proposta já foi revisada.")

    if data.edited_title:
        item.title = data.edited_title
    if data.edited_rationale:
        item.rationale = data.edited_rationale
    if data.edited_materials is not None:
        item.proposed_materials = data.edited_materials
    item.review_notes = data.review_notes
    item.reviewed_by_user_id = actor.user_id
    item.reviewed_at = datetime.now(UTC)

    if data.decision == "rejected":
        item.status = "rejected"
        await append_domain_audit(
            session,
            actor=actor,
            module_name="intervention_orchestration",
            action="intervention.proposal.rejected",
            entity_type="adaptive_recommendation",
            entity_id=item.id,
            details={"review_notes": data.review_notes},
        )
        await session.commit()
        return {
            "proposal": recommendation_payload(item),
            "intervention": None,
        }

    intervention = await approve_proposal(
        session,
        actor=actor,
        recommendation=item,
        due_days=data.due_days,
        evaluation_days=data.evaluation_days,
        create_adaptive_path=data.create_adaptive_path,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_orchestration",
        action="intervention.proposal.approved",
        entity_type="learning_intervention",
        entity_id=intervention.id,
        details={
            "recommendation_id": str(item.id),
            "adaptive_path_id": (
                str(intervention.adaptive_path_id)
                if intervention.adaptive_path_id
                else None
            ),
        },
    )
    await session.commit()
    await session.refresh(intervention)
    return {
        "proposal": recommendation_payload(item),
        "intervention": intervention_payload(intervention),
    }


@router.get("/interventions")
async def list_interventions(
    session: SessionDep,
    actor: ActorDep,
    intervention_status: str | None = Query(default=None, alias="status"),
    student_id: uuid.UUID | None = None,
    classroom_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    require_teacher(actor)
    statement = select(LearningIntervention).where(
        LearningIntervention.organization_id == actor.organization_id,
        LearningIntervention.source_recommendation_id.is_not(None),
    )
    if intervention_status:
        try:
            normalized_status = InterventionStatus(intervention_status)
        except ValueError as exc:
            raise HTTPException(422, "Status de intervenção inválido.") from exc
        statement = statement.where(
            LearningIntervention.status == normalized_status
        )
    if student_id:
        statement = statement.where(
            LearningIntervention.student_id == student_id
        )
    if classroom_id:
        statement = statement.where(
            LearningIntervention.classroom_id == classroom_id
        )
    items = list(
        (
            await session.scalars(
                statement.order_by(LearningIntervention.created_at.desc()).limit(
                    limit
                )
            )
        ).all()
    )
    return [intervention_payload(item) for item in items]


@router.post("/interventions/{intervention_id}/transition")
async def transition_intervention(
    intervention_id: uuid.UUID,
    data: InterventionTransition,
    session: SessionDep,
    actor: ActorDep,
):
    require_teacher(actor)
    item = await intervention_or_404(
        session,
        actor,
        intervention_id,
        lock=True,
    )
    target = InterventionStatus(data.target_status)
    if target == InterventionStatus.COMPLETED:
        raise HTTPException(
            422,
            "Use o endpoint de conclusão para registrar o resultado.",
        )
    if not can_transition(item.status, target):
        raise HTTPException(
            409,
            f"Transição inválida: {item.status.value} -> {target.value}",
        )
    previous = item.status
    item.status = target
    if target == InterventionStatus.ACTIVE:
        item.started_at = item.started_at or datetime.now(UTC)
    if target == InterventionStatus.CANCELED:
        item.completed_at = datetime.now(UTC)
        recommendation = (
            await session.get(
                AdaptiveRecommendation,
                item.source_recommendation_id,
            )
            if item.source_recommendation_id
            else None
        )
        if recommendation:
            recommendation.status = "canceled"
        alert = (
            await session.get(LearningAlert, item.alert_id)
            if item.alert_id
            else None
        )
        if alert:
            alert.status = AlertStatus.OPEN
            alert.resolved_at = None
    if data.notes:
        item.notes = f"{item.notes}\n{data.notes}".strip()

    await add_event(
        session,
        actor_user_id=actor.user_id,
        intervention=item,
        event_type=f"intervention.{target.value}",
        from_status=previous.value,
        to_status=target.value,
        data={"notes": data.notes},
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_orchestration",
        action=f"intervention.{target.value}",
        entity_type="learning_intervention",
        entity_id=item.id,
        details={"from_status": previous.value, "notes": data.notes},
    )
    await session.commit()
    return intervention_payload(item)


@router.post("/interventions/{intervention_id}/complete")
async def complete(
    intervention_id: uuid.UUID,
    data: InterventionComplete,
    session: SessionDep,
    actor: ActorDep,
):
    require_teacher(actor)
    item = await intervention_or_404(
        session,
        actor,
        intervention_id,
        lock=True,
    )
    if item.status != InterventionStatus.ACTIVE:
        raise HTTPException(
            409,
            "A intervenção precisa estar ativa antes da conclusão.",
        )
    outcome = await complete_intervention(
        session,
        actor=actor,
        intervention=item,
        result_summary=data.result_summary,
        teacher_notes=data.teacher_notes,
        observed_progress_percent=data.observed_progress_percent,
        observed_score_percent=data.observed_score_percent,
    )
    await session.flush()
    comparison = {
        key: item.target_snapshot.get(key)
        for key in (
            "metric",
            "before",
            "after",
            "gain",
            "outcome",
            "improved",
            "target_met",
            "comparable",
        )
    }
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_orchestration",
        action="intervention.outcome.recorded",
        entity_type=(
            "intervention_outcome" if outcome else "learning_intervention"
        ),
        entity_id=outcome.id if outcome else item.id,
        details={
            "intervention_id": str(item.id),
            **comparison,
            "scope": "student" if item.student_id else "classroom",
        },
    )
    await session.commit()
    return {
        "intervention": intervention_payload(item),
        "outcome": (
            {
                "id": str(outcome.id),
                "mastery_before": outcome.mastery_before,
                "mastery_after": outcome.mastery_after,
                "mastery_gain": outcome.mastery_gain,
                "outcome": outcome.outcome,
                "occurred_at": outcome.occurred_at,
                **comparison,
            }
            if outcome
            else {**comparison, "id": None}
        ),
    }


@router.get("/interventions/{intervention_id}/timeline")
async def timeline(
    intervention_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_teacher(actor)
    await intervention_or_404(session, actor, intervention_id)
    items = list(
        (
            await session.scalars(
                select(LearningInterventionEvent)
                .where(
                    LearningInterventionEvent.organization_id
                    == actor.organization_id,
                    LearningInterventionEvent.intervention_id
                    == intervention_id,
                )
                .order_by(LearningInterventionEvent.created_at)
            )
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "event_type": item.event_type,
            "actor_user_id": (
                str(item.actor_user_id) if item.actor_user_id else None
            ),
            "from_status": item.from_status,
            "to_status": item.to_status,
            "event_data": item.event_data,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.get("/my-interventions")
async def my_interventions(session: SessionDep, actor: ActorDep):
    classroom_ids = list(
        (
            await session.scalars(
                select(ClassroomEnrollment.classroom_id).where(
                    ClassroomEnrollment.user_id == actor.user_id,
                    ClassroomEnrollment.role == "student",
                )
            )
        ).all()
    )
    visibility = LearningIntervention.student_id == actor.user_id
    if classroom_ids:
        visibility = or_(
            visibility,
            and_(
                LearningIntervention.student_id.is_(None),
                LearningIntervention.classroom_id.in_(classroom_ids),
            ),
        )
    items = list(
        (
            await session.scalars(
                select(LearningIntervention)
                .where(
                    LearningIntervention.organization_id
                    == actor.organization_id,
                    visibility,
                    LearningIntervention.status.in_(
                        [
                            InterventionStatus.PLANNED,
                            InterventionStatus.ACTIVE,
                            InterventionStatus.COMPLETED,
                        ]
                    ),
                )
                .order_by(LearningIntervention.created_at.desc())
            )
        ).all()
    )
    return [student_intervention_payload(item) for item in items]


@router.post("/my-interventions/{intervention_id}/acknowledge")
async def acknowledge_intervention(
    intervention_id: uuid.UUID,
    data: StudentAcknowledgement,
    session: SessionDep,
    actor: ActorDep,
):
    item = await intervention_or_404(session, actor, intervention_id)
    if not await user_can_access_intervention(
        session,
        user_id=actor.user_id,
        intervention=item,
    ):
        raise HTTPException(403, "Esta intervenção não pertence ao estudante.")
    await add_event(
        session,
        actor_user_id=actor.user_id,
        intervention=item,
        event_type="intervention.student_acknowledged",
        from_status=item.status.value,
        to_status=item.status.value,
        data={"note": data.note},
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_orchestration",
        action="intervention.student_acknowledged",
        entity_type="learning_intervention",
        entity_id=item.id,
        details={"note": data.note},
    )
    await session.commit()
    return {"acknowledged": True}
