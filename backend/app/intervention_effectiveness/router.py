from __future__ import annotations

import io
import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import InterventionStatus, LearningIntervention
from app.services.consolidated_audit import append_domain_audit

from .compat import ActorContext, get_project_session, resolve_actor_context
from .models import (
    InterventionEffectivenessMetric,
    InterventionEvaluationCheckpoint,
)
from .policies import period_bounds, window_definitions
from .schemas import (
    CheckpointEvaluationRequest,
    EffectivenessRefreshRequest,
    ScheduleCheckpointsRequest,
)
from .services import (
    evaluate_checkpoint,
    metrics_csv,
    refresh_effectiveness,
    schedule_checkpoints,
)

router = APIRouter(
    prefix="/intervention-effectiveness",
    tags=["intervention-effectiveness"],
)
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ANALYTICS_ROLES = {
    "OWNER",
    "ADMIN",
    "ORG_ADMIN",
    "PLATFORM_ADMIN",
    "TEACHER",
    "COORDINATOR",
    "PEDAGOGICAL_COORDINATOR",
}


def require_analytics(actor: ActorContext) -> None:
    if not set(actor.roles).intersection(ANALYTICS_ROLES):
        raise HTTPException(
            403,
            "Permissão insuficiente para eficácia de intervenções.",
        )


def checkpoint_payload(
    item: InterventionEvaluationCheckpoint,
) -> dict[str, object]:
    return {
        "id": str(item.id),
        "intervention_id": str(item.intervention_id),
        "student_id": str(item.student_id) if item.student_id else None,
        "classroom_id": (
            str(item.classroom_id) if item.classroom_id else None
        ),
        "comic_release_id": (
            str(item.comic_release_id) if item.comic_release_id else None
        ),
        "assignment_id": (
            str(item.assignment_id) if item.assignment_id else None
        ),
        "window_code": item.window_code,
        "window_days": item.window_days,
        "scheduled_for": item.scheduled_for,
        "status": item.status,
        "metric_name": item.metric_name,
        "baseline_value": item.baseline_value,
        "observed_value": item.observed_value,
        "delta_value": item.delta_value,
        "target_value": item.target_value,
        "target_met": item.target_met,
        "improved": item.improved,
        "retained": item.retained,
        "alert_recurred": item.alert_recurred,
        "comparable": item.comparable,
        "evidence_count": item.evidence_count,
        "privacy_suppressed": item.privacy_suppressed,
        "evaluated_at": item.evaluated_at,
    }


def metric_payload(
    item: InterventionEffectivenessMetric,
) -> dict[str, object]:
    suppressed = item.privacy_suppressed
    return {
        "id": str(item.id),
        "scope_type": item.scope_type,
        "scope_key": item.scope_key,
        "period_start": item.period_start,
        "period_end": item.period_end,
        "window_code": item.window_code,
        "dimension_type": item.dimension_type,
        "dimension_key": item.dimension_key,
        "intervention_type": item.intervention_type,
        "comic_release_id": (
            str(item.comic_release_id) if item.comic_release_id else None
        ),
        "assignment_id": (
            str(item.assignment_id) if item.assignment_id else None
        ),
        "accessible_resource_version_id": (
            str(item.accessible_resource_version_id)
            if item.accessible_resource_version_id
            else None
        ),
        "adaptive_path_used": item.adaptive_path_used,
        "sample_size": item.sample_size,
        "completion_rate": None if suppressed else item.completion_rate,
        "improved_rate": None if suppressed else item.improved_rate,
        "target_met_rate": None if suppressed else item.target_met_rate,
        "retention_rate": None if suppressed else item.retention_rate,
        "recurrence_rate": None if suppressed else item.recurrence_rate,
        "average_gain": None if suppressed else item.average_gain,
        "median_days_to_improvement": (
            None if suppressed else item.median_days_to_improvement
        ),
        "privacy_suppressed": suppressed,
        "calculated_at": item.calculated_at,
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "sprint": "16.8",
        "module": "intervention-effectiveness",
    }


@router.get("/windows")
async def windows(actor: ActorDep):
    require_analytics(actor)
    return window_definitions()


@router.get("/dashboard")
async def dashboard(
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    require_analytics(actor)
    try:
        start, end = period_bounds(period_start, period_end)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error

    pending = await session.scalar(
        select(func.count(InterventionEvaluationCheckpoint.id)).where(
            InterventionEvaluationCheckpoint.organization_id
            == actor.organization_id,
            InterventionEvaluationCheckpoint.status.in_(
                ["pending", "insufficient_evidence"]
            ),
        )
    )
    overdue = await session.scalar(
        select(func.count(InterventionEvaluationCheckpoint.id)).where(
            InterventionEvaluationCheckpoint.organization_id
            == actor.organization_id,
            InterventionEvaluationCheckpoint.status.in_(
                ["pending", "insufficient_evidence"]
            ),
            InterventionEvaluationCheckpoint.scheduled_for
            < datetime.now(UTC),
        )
    )
    completed_interventions = await session.scalar(
        select(func.count(LearningIntervention.id)).where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.status == InterventionStatus.COMPLETED,
            func.date(LearningIntervention.completed_at) >= start,
            func.date(LearningIntervention.completed_at) <= end,
        )
    )
    overall = list(
        (
            await session.scalars(
                select(InterventionEffectivenessMetric)
                .where(
                    InterventionEffectivenessMetric.organization_id
                    == actor.organization_id,
                    InterventionEffectivenessMetric.scope_key
                    == "ORGANIZATION",
                    InterventionEffectivenessMetric.dimension_type
                    == "overall",
                    InterventionEffectivenessMetric.period_start == start,
                    InterventionEffectivenessMetric.period_end == end,
                )
                .order_by(
                    InterventionEffectivenessMetric.window_code
                )
            )
        ).all()
    )
    return {
        "period_start": start,
        "period_end": end,
        "completed_interventions": int(completed_interventions or 0),
        "pending_checkpoints": int(pending or 0),
        "overdue_checkpoints": int(overdue or 0),
        "windows": [metric_payload(item) for item in overall],
        "privacy_applied": True,
    }


@router.post("/interventions/{intervention_id}/schedule")
async def schedule_intervention(
    intervention_id: uuid.UUID,
    data: ScheduleCheckpointsRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_analytics(actor)
    intervention = await session.scalar(
        select(LearningIntervention)
        .where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.id == intervention_id,
        )
        .with_for_update()
    )
    if intervention is None:
        raise HTTPException(404, "Intervenção não encontrada.")
    if intervention.status != InterventionStatus.COMPLETED:
        raise HTTPException(
            409,
            "Somente intervenções concluídas podem ser acompanhadas.",
        )
    rows = await schedule_checkpoints(
        session,
        intervention=intervention,
        replace_pending=data.replace_pending,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_effectiveness",
        action="intervention.effectiveness.scheduled",
        entity_type="learning_intervention",
        entity_id=intervention.id,
        details={
            "windows": [item.window_code for item in rows],
            "replace_pending": data.replace_pending,
        },
    )
    await session.commit()
    return [checkpoint_payload(item) for item in rows]


@router.get("/checkpoints")
async def checkpoints(
    session: SessionDep,
    actor: ActorDep,
    checkpoint_status: str | None = Query(default=None, alias="status"),
    window_code: str | None = None,
    intervention_id: uuid.UUID | None = None,
    due_only: bool = False,
    limit: int = Query(default=200, ge=1, le=1000),
):
    require_analytics(actor)
    statement = select(InterventionEvaluationCheckpoint).where(
        InterventionEvaluationCheckpoint.organization_id
        == actor.organization_id
    )
    if checkpoint_status:
        statement = statement.where(
            InterventionEvaluationCheckpoint.status == checkpoint_status
        )
    if window_code:
        statement = statement.where(
            InterventionEvaluationCheckpoint.window_code == window_code
        )
    if intervention_id:
        statement = statement.where(
            InterventionEvaluationCheckpoint.intervention_id
            == intervention_id
        )
    if due_only:
        statement = statement.where(
            InterventionEvaluationCheckpoint.scheduled_for
            <= datetime.now(UTC),
            InterventionEvaluationCheckpoint.status.in_(
                ["pending", "insufficient_evidence"]
            ),
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    InterventionEvaluationCheckpoint.scheduled_for,
                    InterventionEvaluationCheckpoint.created_at,
                ).limit(limit)
            )
        ).all()
    )
    return [checkpoint_payload(item) for item in rows]


@router.post("/checkpoints/{checkpoint_id}/evaluate")
async def evaluate(
    checkpoint_id: uuid.UUID,
    data: CheckpointEvaluationRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_analytics(actor)
    item = await session.scalar(
        select(InterventionEvaluationCheckpoint).where(
            InterventionEvaluationCheckpoint.organization_id
            == actor.organization_id,
            InterventionEvaluationCheckpoint.id == checkpoint_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Checkpoint não encontrado.")
    try:
        item = await evaluate_checkpoint(
            session,
            checkpoint=item,
            force=data.force,
            observed_progress_percent=data.observed_progress_percent,
            observed_score_percent=data.observed_score_percent,
        )
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_effectiveness",
        action="intervention.effectiveness.evaluated",
        entity_type="intervention_evaluation_checkpoint",
        entity_id=item.id,
        details={
            "window_code": item.window_code,
            "status": item.status,
            "metric_name": item.metric_name,
            "target_met": item.target_met,
            "retained": item.retained,
            "alert_recurred": item.alert_recurred,
        },
    )
    await session.commit()
    return checkpoint_payload(item)


@router.post("/refresh")
async def refresh(
    data: EffectivenessRefreshRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_analytics(actor)
    result = await refresh_effectiveness(
        session,
        actor=actor,
        period_start=data.period_start,
        period_end=data.period_end,
        classroom_id=data.classroom_id,
        window_code=data.window_code,
        evaluate_due=data.evaluate_due,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_effectiveness",
        action="intervention.effectiveness.refreshed",
        entity_type="background_job",
        entity_id=uuid.UUID(result["job_id"]),
        details=data.model_dump(mode="json"),
    )
    await session.commit()
    return result


@router.get("/metrics")
async def metrics(
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    window_code: str | None = None,
    dimension_type: str | None = None,
    classroom_id: uuid.UUID | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
):
    require_analytics(actor)
    try:
        start, end = period_bounds(period_start, period_end)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    statement = select(InterventionEffectivenessMetric).where(
        InterventionEffectivenessMetric.organization_id
        == actor.organization_id,
        InterventionEffectivenessMetric.period_start == start,
        InterventionEffectivenessMetric.period_end == end,
    )
    if window_code:
        statement = statement.where(
            InterventionEffectivenessMetric.window_code == window_code
        )
    if dimension_type:
        statement = statement.where(
            InterventionEffectivenessMetric.dimension_type
            == dimension_type
        )
    if classroom_id:
        statement = statement.where(
            InterventionEffectivenessMetric.scope_key
            == f"CLASSROOM:{classroom_id}"
        )
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    InterventionEffectivenessMetric.window_code,
                    InterventionEffectivenessMetric.dimension_type,
                    InterventionEffectivenessMetric.dimension_key,
                ).limit(limit)
            )
        ).all()
    )
    return [metric_payload(item) for item in rows]


@router.get("/interventions/{intervention_id}")
async def intervention_history(
    intervention_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_analytics(actor)
    intervention = await session.scalar(
        select(LearningIntervention).where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.id == intervention_id,
        )
    )
    if intervention is None:
        raise HTTPException(404, "Intervenção não encontrada.")
    rows = list(
        (
            await session.scalars(
                select(InterventionEvaluationCheckpoint)
                .where(
                    InterventionEvaluationCheckpoint.organization_id
                    == actor.organization_id,
                    InterventionEvaluationCheckpoint.intervention_id
                    == intervention_id,
                )
                .order_by(
                    InterventionEvaluationCheckpoint.window_days
                )
            )
        ).all()
    )
    return {
        "intervention_id": str(intervention.id),
        "intervention_type": intervention.intervention_type.value,
        "student_id": (
            str(intervention.student_id) if intervention.student_id else None
        ),
        "classroom_id": (
            str(intervention.classroom_id)
            if intervention.classroom_id
            else None
        ),
        "completed_at": intervention.completed_at,
        "target_snapshot": intervention.target_snapshot,
        "checkpoints": [checkpoint_payload(item) for item in rows],
    }


@router.get("/export.csv")
async def export_csv(
    session: SessionDep,
    actor: ActorDep,
    period_start: date,
    period_end: date,
    window_code: str | None = None,
    dimension_type: str | None = None,
):
    require_analytics(actor)
    statement = select(InterventionEffectivenessMetric).where(
        InterventionEffectivenessMetric.organization_id
        == actor.organization_id,
        InterventionEffectivenessMetric.period_start == period_start,
        InterventionEffectivenessMetric.period_end == period_end,
    )
    if window_code:
        statement = statement.where(
            InterventionEffectivenessMetric.window_code == window_code
        )
    if dimension_type:
        statement = statement.where(
            InterventionEffectivenessMetric.dimension_type
            == dimension_type
        )
    rows = list((await session.scalars(statement)).all())
    content = metrics_csv(rows)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="intervention_effectiveness",
        action="intervention.effectiveness.exported",
        entity_type="organization",
        entity_id=actor.organization_id,
        details={
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "window_code": window_code,
            "dimension_type": dimension_type,
            "rows": len(rows),
        },
    )
    await session.commit()
    filename = (
        f"intervention-effectiveness-{period_start}-{period_end}.csv"
    )
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8-sig")),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
