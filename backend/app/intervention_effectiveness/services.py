from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_insights.models import InterventionOutcomeRecord
from app.comic_reader_access.models import ComicReadingCheckpoint
from app.comic_reader_analytics.models import ComicReaderSessionMetric
from app.core.config import get_settings
from app.models.analytics import (
    InterventionStatus,
    LearningAlert,
    LearningIntervention,
)
from app.models.delivery import StudentAttempt
from app.models.education import ClassroomEnrollment
from app.models.operations import BackgroundJob

from .compat import ActorContext
from .models import (
    InterventionEffectivenessMetric,
    InterventionEvaluationCheckpoint,
)
from .policies import (
    WINDOWS,
    average,
    classify_followup,
    dimension_key,
    median_value,
    metric_from_intervention,
    privacy_guard,
    safe_rate,
    scheduled_for,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def date_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end, time.max, tzinfo=UTC),
    )


def stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


async def schedule_checkpoints(
    session: AsyncSession,
    *,
    intervention: LearningIntervention,
    outcome_id: uuid.UUID | None = None,
    replace_pending: bool = False,
) -> list[InterventionEvaluationCheckpoint]:
    completed_at = intervention.completed_at or utc_now()
    if replace_pending:
        await session.execute(
            delete(InterventionEvaluationCheckpoint).where(
                InterventionEvaluationCheckpoint.organization_id
                == intervention.organization_id,
                InterventionEvaluationCheckpoint.intervention_id
                == intervention.id,
                InterventionEvaluationCheckpoint.status == "pending",
            )
        )

    existing = {
        item.window_code: item
        for item in (
            await session.scalars(
                select(InterventionEvaluationCheckpoint).where(
                    InterventionEvaluationCheckpoint.organization_id
                    == intervention.organization_id,
                    InterventionEvaluationCheckpoint.intervention_id
                    == intervention.id,
                )
            )
        ).all()
    }
    rows: list[InterventionEvaluationCheckpoint] = []
    for code, days in WINDOWS:
        item = existing.get(code)
        if item is None:
            item = InterventionEvaluationCheckpoint(
                organization_id=intervention.organization_id,
                intervention_id=intervention.id,
                outcome_id=outcome_id,
                student_id=intervention.student_id,
                classroom_id=intervention.classroom_id,
                comic_release_id=intervention.comic_release_id,
                assignment_id=intervention.assignment_id,
                accessible_resource_version_id=(
                    intervention.accessible_resource_version_id
                ),
                adaptive_path_id=intervention.adaptive_path_id,
                window_code=code,
                window_days=days,
                scheduled_for=scheduled_for(completed_at, days),
                status="pending",
                target_value=(
                    float(intervention.target_snapshot.get("target_mastery"))
                    if intervention.target_snapshot.get("target_mastery")
                    is not None
                    else None
                ),
                evidence_snapshot={
                    "scheduled_from": completed_at.isoformat(),
                    "source": "learning_intervention",
                },
            )
            session.add(item)
            await session.flush()
        elif outcome_id and item.outcome_id is None:
            item.outcome_id = outcome_id
        rows.append(item)
    return rows


async def _individual_observation(
    session: AsyncSession,
    *,
    intervention: LearningIntervention,
    metric_name: str,
    until: datetime,
) -> tuple[float | None, int, dict[str, Any]]:
    if intervention.student_id is None:
        return None, 0, {}

    if metric_name == "assessment_score_percent" and intervention.assignment_id:
        attempts = list(
            (
                await session.scalars(
                    select(StudentAttempt)
                    .where(
                        StudentAttempt.organization_id
                        == intervention.organization_id,
                        StudentAttempt.student_id == intervention.student_id,
                        StudentAttempt.assignment_id == intervention.assignment_id,
                        StudentAttempt.grading_complete.is_(True),
                        StudentAttempt.graded_at.is_not(None),
                        StudentAttempt.graded_at <= until,
                        StudentAttempt.graded_at >= intervention.completed_at,
                    )
                    .order_by(StudentAttempt.graded_at.desc())
                )
            ).all()
        )
        if attempts:
            best = max(item.percentage for item in attempts)
            return (
                round(best / 100, 4),
                len(attempts),
                {
                    "attempt_ids": [str(item.id) for item in attempts[:20]],
                    "best_percentage": best,
                },
            )

    if metric_name == "progress_percent" and intervention.comic_release_id:
        checkpoint = await session.scalar(
            select(ComicReadingCheckpoint).where(
                ComicReadingCheckpoint.organization_id
                == intervention.organization_id,
                ComicReadingCheckpoint.user_id == intervention.student_id,
                ComicReadingCheckpoint.release_id
                == intervention.comic_release_id,
            )
        )
        sessions = list(
            (
                await session.scalars(
                    select(ComicReaderSessionMetric).where(
                        ComicReaderSessionMetric.organization_id
                        == intervention.organization_id,
                        ComicReaderSessionMetric.user_id
                        == intervention.student_id,
                        ComicReaderSessionMetric.release_id
                        == intervention.comic_release_id,
                        ComicReaderSessionMetric.started_at
                        >= intervention.completed_at,
                        ComicReaderSessionMetric.started_at <= until,
                    )
                )
            ).all()
        )
        values = [item.progress_percent for item in sessions]
        if checkpoint:
            values.append(checkpoint.progress_percent)
        if values:
            maximum = max(values)
            return (
                round(maximum / 100, 4),
                len(sessions) + int(checkpoint is not None),
                {
                    "session_count": len(sessions),
                    "checkpoint_id": str(checkpoint.id) if checkpoint else None,
                    "maximum_progress_percent": maximum,
                },
            )
    return None, 0, {}


async def _classroom_observation(
    session: AsyncSession,
    *,
    intervention: LearningIntervention,
    metric_name: str,
    until: datetime,
) -> tuple[float | None, int, dict[str, Any], bool]:
    if intervention.classroom_id is None:
        return None, 0, {}, False

    student_ids = list(
        (
            await session.scalars(
                select(ClassroomEnrollment.user_id).where(
                    ClassroomEnrollment.classroom_id
                    == intervention.classroom_id,
                    ClassroomEnrollment.role == "student",
                )
            )
        ).all()
    )
    minimum = get_settings().intervention_effectiveness_min_group_size
    suppressed = privacy_guard(len(student_ids), minimum)
    if suppressed:
        return (
            None,
            len(student_ids),
            {
                "sample_size": len(student_ids),
                "minimum_group_size": minimum,
            },
            True,
        )

    values: list[float] = []
    evidence_count = 0
    if metric_name == "assessment_score_percent" and intervention.assignment_id:
        for student_id in student_ids:
            attempts = list(
                (
                    await session.scalars(
                        select(StudentAttempt).where(
                            StudentAttempt.organization_id
                            == intervention.organization_id,
                            StudentAttempt.student_id == student_id,
                            StudentAttempt.assignment_id
                            == intervention.assignment_id,
                            StudentAttempt.grading_complete.is_(True),
                            StudentAttempt.graded_at.is_not(None),
                            StudentAttempt.graded_at <= until,
                            StudentAttempt.graded_at
                            >= intervention.completed_at,
                        )
                    )
                ).all()
            )
            if attempts:
                values.append(max(item.percentage for item in attempts) / 100)
                evidence_count += len(attempts)

    if metric_name == "progress_percent" and intervention.comic_release_id:
        checkpoints = list(
            (
                await session.scalars(
                    select(ComicReadingCheckpoint).where(
                        ComicReadingCheckpoint.organization_id
                        == intervention.organization_id,
                        ComicReadingCheckpoint.user_id.in_(student_ids),
                        ComicReadingCheckpoint.release_id
                        == intervention.comic_release_id,
                    )
                )
            ).all()
        )
        values.extend(item.progress_percent / 100 for item in checkpoints)
        evidence_count = len(checkpoints)

    return (
        average(values),
        evidence_count,
        {
            "sample_size": len(student_ids),
            "observed_students": len(values),
            "minimum_group_size": minimum,
        },
        False,
    )


async def _alert_recurred(
    session: AsyncSession,
    *,
    intervention: LearningIntervention,
    until: datetime,
) -> bool:
    if intervention.alert_id is None or intervention.completed_at is None:
        return False
    source = await session.get(LearningAlert, intervention.alert_id)
    if source is None:
        return False

    query = select(LearningAlert.id).where(
        LearningAlert.organization_id == intervention.organization_id,
        LearningAlert.id != source.id,
        LearningAlert.rule_code == source.rule_code,
        LearningAlert.created_at > intervention.completed_at,
        LearningAlert.created_at <= until,
    )
    if intervention.student_id:
        query = query.where(
            LearningAlert.student_id == intervention.student_id
        )
    elif intervention.classroom_id:
        query = query.where(
            LearningAlert.classroom_id == intervention.classroom_id
        )
    return await session.scalar(query.limit(1)) is not None


async def evaluate_checkpoint(
    session: AsyncSession,
    *,
    checkpoint: InterventionEvaluationCheckpoint,
    force: bool = False,
    observed_progress_percent: float | None = None,
    observed_score_percent: float | None = None,
) -> InterventionEvaluationCheckpoint:
    now = utc_now()
    if checkpoint.status == "completed" and not force:
        return checkpoint
    if checkpoint.scheduled_for > now and not force:
        return checkpoint

    checkpoint = await session.scalar(
        select(InterventionEvaluationCheckpoint)
        .where(
            InterventionEvaluationCheckpoint.id == checkpoint.id,
            InterventionEvaluationCheckpoint.organization_id
            == checkpoint.organization_id,
        )
        .with_for_update()
    )
    if checkpoint is None:
        raise ValueError("Checkpoint longitudinal não encontrado")

    intervention = await session.get(
        LearningIntervention,
        checkpoint.intervention_id,
    )
    if intervention is None or intervention.completed_at is None:
        checkpoint.status = "invalid"
        checkpoint.evaluated_at = now
        return checkpoint

    metric_name, baseline_value, target_value = metric_from_intervention(
        intervention.target_snapshot,
        intervention.baseline_snapshot,
    )
    observed_value: float | None = None
    evidence_count = 0
    evidence: dict[str, Any] = {}
    suppressed = False

    manual_value = (
        observed_score_percent
        if metric_name == "assessment_score_percent"
        else observed_progress_percent
        if metric_name == "progress_percent"
        else None
    )
    if manual_value is not None:
        observed_value = round(manual_value / 100, 4)
        evidence_count = 1
        evidence = {"source": "manual_observation"}
    elif checkpoint.window_code == "immediate":
        observed = intervention.target_snapshot.get("after")
        observed_value = float(observed) if observed is not None else None
        evidence_count = int(observed_value is not None)
        evidence = {
            "source": "intervention_completion",
            "comparison": {
                key: intervention.target_snapshot.get(key)
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
            },
        }
    elif intervention.student_id:
        observed_value, evidence_count, evidence = (
            await _individual_observation(
                session,
                intervention=intervention,
                metric_name=metric_name,
                until=now,
            )
        )
    else:
        (
            observed_value,
            evidence_count,
            evidence,
            suppressed,
        ) = await _classroom_observation(
            session,
            intervention=intervention,
            metric_name=metric_name,
            until=now,
        )

    immediate = await session.scalar(
        select(InterventionEvaluationCheckpoint).where(
            InterventionEvaluationCheckpoint.organization_id
            == checkpoint.organization_id,
            InterventionEvaluationCheckpoint.intervention_id
            == checkpoint.intervention_id,
            InterventionEvaluationCheckpoint.window_code == "immediate",
            InterventionEvaluationCheckpoint.status == "completed",
        )
    )
    immediate_value = (
        immediate.observed_value
        if immediate and immediate.id != checkpoint.id
        else observed_value
        if checkpoint.window_code == "immediate"
        else None
    )
    classification = classify_followup(
        baseline_value=baseline_value,
        observed_value=observed_value,
        immediate_value=immediate_value,
        target_value=target_value,
        minimum_improvement=get_settings().intervention_minimum_improvement,
        retention_tolerance=get_settings().intervention_retention_tolerance,
    )
    recurrence = await _alert_recurred(
        session,
        intervention=intervention,
        until=now,
    )

    checkpoint.metric_name = metric_name
    checkpoint.baseline_value = baseline_value
    checkpoint.observed_value = observed_value
    checkpoint.delta_value = classification["delta"]
    checkpoint.target_value = target_value
    checkpoint.target_met = classification["target_met"]
    checkpoint.improved = classification["improved"]
    checkpoint.retained = (
        False
        if checkpoint.window_code == "immediate"
        else classification["retained"]
    )
    checkpoint.alert_recurred = recurrence
    checkpoint.comparable = classification["comparable"]
    checkpoint.evidence_count = evidence_count
    checkpoint.privacy_suppressed = suppressed
    checkpoint.evidence_snapshot = {
        **checkpoint.evidence_snapshot,
        **evidence,
        "outcome": classification["outcome"],
        "evaluated_until": now.isoformat(),
    }
    checkpoint.status = (
        "privacy_suppressed"
        if suppressed
        else "completed"
        if classification["comparable"]
        else "insufficient_evidence"
    )
    checkpoint.evaluated_at = now
    return checkpoint


async def register_intervention_completion(
    session: AsyncSession,
    *,
    intervention: LearningIntervention,
    outcome_id: uuid.UUID | None,
) -> list[InterventionEvaluationCheckpoint]:
    rows = await schedule_checkpoints(
        session,
        intervention=intervention,
        outcome_id=outcome_id,
    )
    immediate = next(
        item for item in rows if item.window_code == "immediate"
    )
    await evaluate_checkpoint(
        session,
        checkpoint=immediate,
        force=True,
    )
    return rows


async def backfill_completed_interventions(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> int:
    start, end = date_bounds(period_start, period_end)
    interventions = list(
        (
            await session.scalars(
                select(LearningIntervention).where(
                    LearningIntervention.organization_id
                    == organization_id,
                    LearningIntervention.status == InterventionStatus.COMPLETED,
                    LearningIntervention.completed_at.is_not(None),
                    LearningIntervention.completed_at >= start,
                    LearningIntervention.completed_at <= end,
                )
            )
        ).all()
    )
    created = 0
    for intervention in interventions:
        exists = await session.scalar(
            select(InterventionEvaluationCheckpoint.id).where(
                InterventionEvaluationCheckpoint.organization_id
                == organization_id,
                InterventionEvaluationCheckpoint.intervention_id
                == intervention.id,
                InterventionEvaluationCheckpoint.window_code == "immediate",
            )
        )
        if exists:
            continue
        outcome_id = await session.scalar(
            select(InterventionOutcomeRecord.id)
            .where(
                InterventionOutcomeRecord.organization_id
                == organization_id,
                InterventionOutcomeRecord.learning_intervention_id
                == intervention.id,
            )
            .order_by(InterventionOutcomeRecord.occurred_at.desc())
            .limit(1)
        )
        await register_intervention_completion(
            session,
            intervention=intervention,
            outcome_id=outcome_id,
        )
        created += 1
    return created


async def evaluate_due_checkpoints(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    limit: int,
) -> dict[str, int]:
    rows = list(
        (
            await session.scalars(
                select(InterventionEvaluationCheckpoint)
                .where(
                    InterventionEvaluationCheckpoint.organization_id
                    == organization_id,
                    InterventionEvaluationCheckpoint.status.in_(
                        ["pending", "insufficient_evidence"]
                    ),
                    InterventionEvaluationCheckpoint.scheduled_for <= utc_now(),
                )
                .order_by(
                    InterventionEvaluationCheckpoint.scheduled_for,
                    InterventionEvaluationCheckpoint.created_at,
                )
                .limit(limit)
            )
        ).all()
    )
    result = defaultdict(int)
    for item in rows:
        evaluated = await evaluate_checkpoint(
            session,
            checkpoint=item,
            force=item.status == "insufficient_evidence",
        )
        result[evaluated.status] += 1
    await session.flush()
    return dict(result)


def _checkpoint_dimensions(
    checkpoint: InterventionEvaluationCheckpoint,
    intervention: LearningIntervention,
) -> list[tuple[str, str, dict[str, Any]]]:
    dimensions: list[tuple[str, str, dict[str, Any]]] = [
        ("overall", dimension_key("overall", "all"), {}),
        (
            "intervention_type",
            dimension_key(
                "intervention_type",
                intervention.intervention_type.value,
            ),
            {"intervention_type": intervention.intervention_type.value},
        ),
        (
            "adaptive_path",
            dimension_key(
                "adaptive_path",
                intervention.adaptive_path_id is not None,
            ),
            {"adaptive_path_used": intervention.adaptive_path_id is not None},
        ),
    ]
    if checkpoint.comic_release_id:
        dimensions.append(
            (
                "comic_release",
                dimension_key("comic_release", checkpoint.comic_release_id),
                {"comic_release_id": checkpoint.comic_release_id},
            )
        )
    if checkpoint.assignment_id:
        dimensions.append(
            (
                "assignment",
                dimension_key("assignment", checkpoint.assignment_id),
                {"assignment_id": checkpoint.assignment_id},
            )
        )
    if checkpoint.accessible_resource_version_id:
        dimensions.append(
            (
                "accessible_resource",
                dimension_key(
                    "accessible_resource",
                    checkpoint.accessible_resource_version_id,
                ),
                {
                    "accessible_resource_version_id":
                    checkpoint.accessible_resource_version_id
                },
            )
        )
    if checkpoint.classroom_id:
        dimensions.append(
            (
                "classroom",
                dimension_key("classroom", checkpoint.classroom_id),
                {},
            )
        )
    target_code = intervention.target_snapshot.get(
        "target_dimension_code"
    )
    if target_code:
        dimensions.append(
            (
                "learning_dimension",
                dimension_key("learning_dimension", str(target_code)),
                {},
            )
        )
    return dimensions


async def refresh_effectiveness_metrics(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
    classroom_id: uuid.UUID | None,
    window_code: str | None,
) -> int:
    start, end = date_bounds(period_start, period_end)
    query = (
        select(InterventionEvaluationCheckpoint, LearningIntervention)
        .join(
            LearningIntervention,
            LearningIntervention.id
            == InterventionEvaluationCheckpoint.intervention_id,
        )
        .where(
            InterventionEvaluationCheckpoint.organization_id
            == organization_id,
            InterventionEvaluationCheckpoint.evaluated_at.is_not(None),
            InterventionEvaluationCheckpoint.evaluated_at >= start,
            InterventionEvaluationCheckpoint.evaluated_at <= end,
        )
    )
    if classroom_id:
        query = query.where(
            InterventionEvaluationCheckpoint.classroom_id == classroom_id
        )
    if window_code:
        query = query.where(
            InterventionEvaluationCheckpoint.window_code == window_code
        )
    rows = list((await session.execute(query)).all())

    groups: dict[
        tuple[str, str, uuid.UUID | None, str, str, str],
        list[tuple[InterventionEvaluationCheckpoint, LearningIntervention, dict[str, Any]]],
    ] = defaultdict(list)
    for checkpoint, intervention in rows:
        if checkpoint.privacy_suppressed:
            continue
        scopes = [("ORGANIZATION", "ORGANIZATION", None)]
        if checkpoint.classroom_id:
            scopes.append(
                (
                    "CLASSROOM",
                    f"CLASSROOM:{checkpoint.classroom_id}",
                    checkpoint.classroom_id,
                )
            )
        for scope_type, scope_key, scope_id in scopes:
            for dimension_type, key, metadata in _checkpoint_dimensions(
                checkpoint,
                intervention,
            ):
                groups[
                    (
                        scope_type,
                        scope_key,
                        scope_id,
                        checkpoint.window_code,
                        dimension_type,
                        key,
                    )
                ].append((checkpoint, intervention, metadata))

    minimum = get_settings().intervention_effectiveness_min_group_size
    count = 0
    for (
        scope_type,
        scope_key,
        scope_id,
        group_window,
        dimension_type,
        key,
    ), items in groups.items():
        existing = await session.scalar(
            select(InterventionEffectivenessMetric).where(
                InterventionEffectivenessMetric.organization_id
                == organization_id,
                InterventionEffectivenessMetric.scope_key == scope_key,
                InterventionEffectivenessMetric.period_start == period_start,
                InterventionEffectivenessMetric.period_end == period_end,
                InterventionEffectivenessMetric.window_code == group_window,
                InterventionEffectivenessMetric.dimension_key == key,
            )
        )
        metric = existing or InterventionEffectivenessMetric(
            organization_id=organization_id,
            scope_type=scope_type,
            scope_key=scope_key,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            window_code=group_window,
            dimension_type=dimension_type,
            dimension_key=key,
        )
        checkpoints = [item[0] for item in items]
        interventions = [item[1] for item in items]
        metadata = items[0][2]
        sample_size = len(checkpoints)
        suppressed = privacy_guard(sample_size, minimum)
        completed = sum(
            item.status in {"completed", "insufficient_evidence"}
            for item in checkpoints
        )
        improved = sum(item.improved for item in checkpoints)
        target_met = sum(item.target_met for item in checkpoints)
        retained = sum(item.retained for item in checkpoints)
        recurrence = sum(item.alert_recurred for item in checkpoints)
        insufficient = sum(
            not item.comparable for item in checkpoints
        )
        gains = [
            item.delta_value
            for item in checkpoints
            if item.delta_value is not None
        ]
        days_to_improvement = [
            float(item.window_days)
            for item in checkpoints
            if item.improved or item.target_met
        ]

        metric.intervention_type = metadata.get("intervention_type")
        metric.comic_release_id = metadata.get("comic_release_id")
        metric.assignment_id = metadata.get("assignment_id")
        metric.accessible_resource_version_id = metadata.get(
            "accessible_resource_version_id"
        )
        metric.adaptive_path_used = metadata.get("adaptive_path_used")
        metric.sample_size = sample_size
        metric.completed_count = completed
        metric.improved_count = improved
        metric.target_met_count = target_met
        metric.retained_count = retained
        metric.recurrence_count = recurrence
        metric.insufficient_count = insufficient
        metric.privacy_suppressed = suppressed
        metric.completion_rate = (
            None if suppressed else safe_rate(completed, sample_size)
        )
        metric.improved_rate = (
            None if suppressed else safe_rate(improved, sample_size)
        )
        metric.target_met_rate = (
            None if suppressed else safe_rate(target_met, sample_size)
        )
        metric.retention_rate = (
            None if suppressed else safe_rate(retained, sample_size)
        )
        metric.recurrence_rate = (
            None if suppressed else safe_rate(recurrence, sample_size)
        )
        metric.average_gain = (
            None if suppressed else average(gains)
        )
        metric.median_days_to_improvement = (
            None if suppressed else median_value(days_to_improvement)
        )
        metric.evidence = {
            "minimum_group_size": minimum,
            "intervention_ids": [
                str(item.id) for item in interventions[:100]
            ],
            "comparable_count": sample_size - insufficient,
        }
        metric.calculated_at = utc_now()
        if existing is None:
            session.add(metric)
        count += 1
    await session.flush()
    return count


async def refresh_effectiveness(
    session: AsyncSession,
    *,
    actor: ActorContext,
    period_start: date,
    period_end: date,
    classroom_id: uuid.UUID | None,
    window_code: str | None,
    evaluate_due: bool,
) -> dict[str, Any]:
    latest = await session.execute(
        select(
            func.count(InterventionEvaluationCheckpoint.id),
            func.max(InterventionEvaluationCheckpoint.updated_at),
        ).where(
            InterventionEvaluationCheckpoint.organization_id
            == actor.organization_id
        )
    )
    checkpoint_count, latest_update = latest.one()
    fingerprint = stable_hash(
        {
            "organization_id": actor.organization_id,
            "period_start": period_start,
            "period_end": period_end,
            "classroom_id": classroom_id,
            "window_code": window_code,
            "evaluate_due": evaluate_due,
            "checkpoint_count": int(checkpoint_count or 0),
            "latest_update": latest_update,
        }
    )
    key = f"intervention-effectiveness:{fingerprint[:48]}"
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
            job_type="intervention_effectiveness_refresh",
            queue_name="default",
            module_name="intervention_effectiveness",
            entity_type="organization",
            entity_id=actor.organization_id,
            status="processing",
            priority=45,
            progress_percent=5,
            current_step="Avaliando janelas longitudinais",
            total_steps=2,
            idempotency_key=key,
            input_snapshot={
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "classroom_id": (
                    str(classroom_id) if classroom_id else None
                ),
                "window_code": window_code,
                "evaluate_due": evaluate_due,
            },
            queued_at=utc_now(),
            started_at=utc_now(),
        )
        session.add(job)
        await session.flush()
    else:
        job.status = "processing"
        job.progress_percent = 5

    scheduled = await backfill_completed_interventions(
        session,
        organization_id=actor.organization_id,
        period_start=period_start,
        period_end=period_end,
    )
    due_result: dict[str, int] = {}
    if evaluate_due:
        due_result = await evaluate_due_checkpoints(
            session,
            organization_id=actor.organization_id,
            limit=get_settings().intervention_effectiveness_refresh_limit,
        )
    job.progress_percent = 55
    job.current_step = "Agregando eficácia"
    metric_count = await refresh_effectiveness_metrics(
        session,
        organization_id=actor.organization_id,
        period_start=period_start,
        period_end=period_end,
        classroom_id=classroom_id,
        window_code=window_code,
    )
    result = {
        "interventions_scheduled": scheduled,
        "checkpoints_evaluated": due_result,
        "metrics_calculated": metric_count,
    }
    job.status = "completed"
    job.progress_percent = 100
    job.current_step = "Eficácia atualizada"
    job.result_reference = result
    job.completed_at = utc_now()
    await session.flush()
    return {"job_id": str(job.id), "reused": False, **result}


def metrics_csv(rows: list[InterventionEffectivenessMetric]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "scope_type",
            "scope_key",
            "period_start",
            "period_end",
            "window_code",
            "dimension_type",
            "dimension_key",
            "sample_size",
            "completion_rate",
            "improved_rate",
            "target_met_rate",
            "retention_rate",
            "recurrence_rate",
            "average_gain",
            "median_days_to_improvement",
            "privacy_suppressed",
        ]
    )
    for item in rows:
        writer.writerow(
            [
                item.scope_type,
                item.scope_key,
                item.period_start,
                item.period_end,
                item.window_code,
                item.dimension_type,
                item.dimension_key,
                item.sample_size,
                item.completion_rate,
                item.improved_rate,
                item.target_met_rate,
                item.retention_rate,
                item.recurrence_rate,
                item.average_gain,
                item.median_days_to_improvement,
                item.privacy_suppressed,
            ]
        )
    return output.getvalue()
