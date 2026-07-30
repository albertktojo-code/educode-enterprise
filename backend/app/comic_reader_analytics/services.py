from __future__ import annotations

import csv
import io
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time
from statistics import mean
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comic_reader_access.models import (
    ComicEmbeddedAssessmentLink,
    ComicPresentationSession,
    ComicReadingCheckpoint,
)
from app.comic_review_publish.models import ComicEditorialRelease
from app.models.analytics import AlertSeverity, AlertStatus, LearningAlert
from app.models.delivery import StudentAttempt
from app.models.education import Classroom, ClassroomEnrollment
from app.models.operations import BackgroundJob

from . import models
from .compat import ActorContext
from .policies import (
    MINIMUM_GROUP_SIZE,
    clamp_duration,
    correlation_label,
    median,
    pearson,
    privacy_guard,
    safe_rate,
    stable_hash,
)


def bounds(start: date, end: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end, time.max, tzinfo=UTC),
    )


def dimension_key(page: int | None, panel: int | None) -> str:
    return f"page:{page or 0}:panel:{panel or 0}"


async def ingest_events(
    session: AsyncSession,
    *,
    actor: ActorContext,
    events: list[Any],
) -> dict[str, int]:
    release_ids = {event.release_id for event in events}
    allowed_release_ids = set(
        (
            await session.scalars(
                select(ComicEditorialRelease.id).where(
                    ComicEditorialRelease.organization_id == actor.organization_id,
                    ComicEditorialRelease.id.in_(release_ids),
                )
            )
        ).all()
    )
    unknown = release_ids.difference(allowed_release_ids)
    if unknown:
        raise ValueError("One or more releases do not belong to the current organization")

    presentation_pairs = {
        (event.presentation_session_id, event.release_id)
        for event in events
        if event.presentation_session_id is not None
    }
    if presentation_pairs:
        presentation_ids = {item[0] for item in presentation_pairs}
        presentations = list(
            (
                await session.scalars(
                    select(ComicPresentationSession).where(
                        ComicPresentationSession.organization_id == actor.organization_id,
                        ComicPresentationSession.id.in_(presentation_ids),
                    )
                )
            ).all()
        )
        valid_pairs = {(item.id, item.release_id) for item in presentations}
        if presentation_pairs.difference(valid_pairs):
            raise ValueError("Invalid presentation session reference")

    accepted = 0
    duplicates = 0
    for event in events:
        exists = await session.scalar(
            select(models.ComicReaderEvent.id).where(
                models.ComicReaderEvent.organization_id == actor.organization_id,
                models.ComicReaderEvent.user_id == actor.user_id,
                models.ComicReaderEvent.client_event_id == event.client_event_id,
            )
        )
        if exists:
            duplicates += 1
            continue
        session.add(
            models.ComicReaderEvent(
                organization_id=actor.organization_id,
                release_id=event.release_id,
                user_id=actor.user_id,
                presentation_session_id=event.presentation_session_id,
                client_event_id=event.client_event_id,
                session_key=event.session_key,
                event_type=event.event_type,
                page_number=event.page_number,
                panel_number=event.panel_number,
                duration_ms=clamp_duration(event.duration_ms),
                sequence=event.sequence,
                properties=event.properties,
                occurred_at=event.occurred_at,
            )
        )
        accepted += 1
    await session.commit()
    return {"accepted": accepted, "duplicates": duplicates}


async def refresh_session_metrics(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
    release_id: uuid.UUID | None,
) -> list[models.ComicReaderSessionMetric]:
    start, end = bounds(period_start, period_end)
    query = select(models.ComicReaderEvent).where(
        models.ComicReaderEvent.organization_id == organization_id,
        models.ComicReaderEvent.occurred_at >= start,
        models.ComicReaderEvent.occurred_at <= end,
    )
    if release_id:
        query = query.where(models.ComicReaderEvent.release_id == release_id)
    events = list((await session.scalars(query.order_by(models.ComicReaderEvent.occurred_at))).all())

    checkpoints_query = select(ComicReadingCheckpoint).where(
        ComicReadingCheckpoint.organization_id == organization_id
    )
    if release_id:
        checkpoints_query = checkpoints_query.where(
            ComicReadingCheckpoint.release_id == release_id
        )
    checkpoints = {
        (item.release_id, item.user_id): item
        for item in (await session.scalars(checkpoints_query)).all()
    }

    grouped: dict[tuple[uuid.UUID, uuid.UUID, str], list[models.ComicReaderEvent]] = defaultdict(list)
    for event in events:
        grouped[(event.release_id, event.user_id, event.session_key)].append(event)

    results: list[models.ComicReaderSessionMetric] = []
    for (group_release, user_id, session_key), rows in grouped.items():
        positions = [
            dimension_key(item.page_number, item.panel_number)
            for item in rows
            if item.event_type in {"PAGE_VIEWED", "PANEL_VIEWED"}
        ]
        checkpoint = checkpoints.get((group_release, user_id))
        existing = await session.scalar(
            select(models.ComicReaderSessionMetric).where(
                models.ComicReaderSessionMetric.organization_id == organization_id,
                models.ComicReaderSessionMetric.release_id == group_release,
                models.ComicReaderSessionMetric.user_id == user_id,
                models.ComicReaderSessionMetric.session_key == session_key,
            )
        )
        item = existing or models.ComicReaderSessionMetric(
            organization_id=organization_id,
            release_id=group_release,
            user_id=user_id,
            session_key=session_key,
            started_at=rows[0].occurred_at,
        )
        item.started_at = min(row.occurred_at for row in rows)
        item.ended_at = max(row.occurred_at for row in rows)
        item.total_seconds = max(0, int((item.ended_at - item.started_at).total_seconds()))
        item.active_seconds = int(
            sum(clamp_duration(row.duration_ms) for row in rows) / 1000
        )
        item.page_views = sum(row.event_type == "PAGE_VIEWED" for row in rows)
        item.panel_views = sum(row.event_type == "PANEL_VIEWED" for row in rows)
        item.revisits = max(0, len(positions) - len(set(positions)))
        item.glossary_opens = sum(row.event_type == "GLOSSARY_OPENED" for row in rows)
        item.narration_seconds = int(
            sum(
                clamp_duration(row.duration_ms)
                for row in rows
                if row.event_type == "NARRATION_COMPLETED"
            )
            / 1000
        )
        item.accessibility_actions = sum(
            row.event_type == "ACCESSIBILITY_CHANGED" for row in rows
        )
        item.assessment_opens = sum(row.event_type == "ASSESSMENT_OPENED" for row in rows)
        item.presentation_syncs = sum(
            row.event_type == "PRESENTATION_SYNCED" for row in rows
        )
        item.progress_percent = checkpoint.progress_percent if checkpoint else 0.0
        item.completed = bool(checkpoint and checkpoint.completed_at)
        item.summary = {"event_count": len(rows), "unique_positions": len(set(positions))}
        if existing is None:
            session.add(item)
        results.append(item)
    await session.flush()
    return results


async def refresh_content_metrics(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
    release_id: uuid.UUID | None,
) -> int:
    start, end = bounds(period_start, period_end)
    query = select(models.ComicReaderEvent).where(
        models.ComicReaderEvent.organization_id == organization_id,
        models.ComicReaderEvent.occurred_at >= start,
        models.ComicReaderEvent.occurred_at <= end,
    )
    if release_id:
        query = query.where(models.ComicReaderEvent.release_id == release_id)
    events = list((await session.scalars(query)).all())

    buckets: dict[tuple[uuid.UUID, date, str], list[models.ComicReaderEvent]] = defaultdict(list)
    for event in events:
        buckets[
            (
                event.release_id,
                event.occurred_at.date(),
                dimension_key(event.page_number, event.panel_number),
            )
        ].append(event)

    for (group_release, metric_date, key), rows in buckets.items():
        existing = await session.scalar(
            select(models.ComicReaderContentMetric).where(
                models.ComicReaderContentMetric.organization_id == organization_id,
                models.ComicReaderContentMetric.release_id == group_release,
                models.ComicReaderContentMetric.metric_date == metric_date,
                models.ComicReaderContentMetric.dimension_key == key,
            )
        )
        item = existing or models.ComicReaderContentMetric(
            organization_id=organization_id,
            release_id=group_release,
            metric_date=metric_date,
            dimension_key=key,
        )
        first = rows[0]
        item.page_number = first.page_number
        item.panel_number = first.panel_number
        item.viewer_count = len({row.user_id for row in rows})
        item.view_count = sum(
            row.event_type in {"PAGE_VIEWED", "PANEL_VIEWED"} for row in rows
        )
        item.completion_count = sum(
            row.event_type in {"PAGE_COMPLETED", "PANEL_COMPLETED"} for row in rows
        )
        views_per_user: dict[uuid.UUID, int] = defaultdict(int)
        for row in rows:
            if row.event_type in {"PAGE_VIEWED", "PANEL_VIEWED"}:
                views_per_user[row.user_id] += 1
        item.revisit_count = sum(max(0, value - 1) for value in views_per_user.values())
        item.total_active_seconds = int(
            sum(
                clamp_duration(row.duration_ms)
                for row in rows
                if row.event_type == "POSITION_DWELL"
            )
            / 1000
        )
        item.glossary_opens = sum(row.event_type == "GLOSSARY_OPENED" for row in rows)
        item.narration_starts = sum(row.event_type == "NARRATION_STARTED" for row in rows)
        item.assessment_opens = sum(row.event_type == "ASSESSMENT_OPENED" for row in rows)
        if existing is None:
            session.add(item)
    await session.flush()
    return len(buckets)


async def refresh_cohort_metrics(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
    release_id: uuid.UUID | None,
    classroom_id: uuid.UUID | None,
) -> int:
    start, end = bounds(period_start, period_end)
    query = select(models.ComicReaderSessionMetric).where(
        models.ComicReaderSessionMetric.organization_id == organization_id,
        models.ComicReaderSessionMetric.started_at >= start,
        models.ComicReaderSessionMetric.started_at <= end,
    )
    if release_id:
        query = query.where(models.ComicReaderSessionMetric.release_id == release_id)
    metrics = list((await session.scalars(query)).all())

    organization_classrooms = select(Classroom.id).where(
        Classroom.organization_id == organization_id
    )
    if classroom_id:
        organization_classrooms = organization_classrooms.where(
            Classroom.id == classroom_id
        )
    classroom_ids = set((await session.scalars(organization_classrooms)).all())
    if classroom_ids:
        enrollments = [
            item
            for item in (
                await session.scalars(
                    select(ClassroomEnrollment).where(
                        ClassroomEnrollment.classroom_id.in_(classroom_ids)
                    )
                )
            ).all()
            if item.role.lower() == "student"
        ]
    else:
        enrollments = []
    user_classrooms: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    classroom_users: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for item in enrollments:
        user_classrooms[item.user_id].add(item.classroom_id)
        classroom_users[item.classroom_id].add(item.user_id)

    groups: dict[tuple[uuid.UUID, uuid.UUID], dict[uuid.UUID, list[Any]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for metric in metrics:
        for classroom in user_classrooms.get(metric.user_id, set()):
            groups[(classroom, metric.release_id)][metric.user_id].append(metric)

    count = 0
    for (classroom, group_release), students in groups.items():
        summaries = []
        for student_id, rows in students.items():
            summaries.append(
                {
                    "student_id": student_id,
                    "active": sum(row.active_seconds for row in rows),
                    "progress": max(row.progress_percent for row in rows),
                    "completed": any(row.completed for row in rows),
                    "presentation": any(row.presentation_syncs > 0 for row in rows),
                    "narration": any(row.narration_seconds > 0 for row in rows),
                    "accessibility": any(row.accessibility_actions > 0 for row in rows),
                }
            )
        existing = await session.scalar(
            select(models.ComicReaderCohortMetric).where(
                models.ComicReaderCohortMetric.organization_id == organization_id,
                models.ComicReaderCohortMetric.classroom_id == classroom,
                models.ComicReaderCohortMetric.release_id == group_release,
                models.ComicReaderCohortMetric.period_start == period_start,
                models.ComicReaderCohortMetric.period_end == period_end,
            )
        )
        item = existing or models.ComicReaderCohortMetric(
            organization_id=organization_id,
            classroom_id=classroom,
            release_id=group_release,
            period_start=period_start,
            period_end=period_end,
        )
        item.enrolled_students = len(classroom_users[classroom])
        item.started_students = len(summaries)
        item.completed_students = sum(row["completed"] for row in summaries)
        item.completion_rate = safe_rate(
            item.completed_students, max(item.enrolled_students, 1)
        )
        item.average_active_seconds = (
            round(mean(row["active"] for row in summaries), 2) if summaries else 0.0
        )
        item.median_progress_percent = median(
            [float(row["progress"]) for row in summaries]
        )
        item.presentation_participants = sum(row["presentation"] for row in summaries)
        item.narration_users = sum(row["narration"] for row in summaries)
        item.accessibility_users = sum(row["accessibility"] for row in summaries)
        item.privacy_suppressed = privacy_guard(len(summaries))["suppressed"]
        if existing is None:
            session.add(item)
        count += 1
    await session.flush()
    return count


async def refresh_learning_metrics(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    period_start: date,
    period_end: date,
    release_id: uuid.UUID | None,
) -> int:
    links_query = select(ComicEmbeddedAssessmentLink).where(
        ComicEmbeddedAssessmentLink.organization_id == organization_id,
        ComicEmbeddedAssessmentLink.assignment_id.is_not(None),
    )
    if release_id:
        links_query = links_query.where(
            ComicEmbeddedAssessmentLink.release_id == release_id
        )
    links = list((await session.scalars(links_query)).all())
    pairs = {
        (link.release_id, link.assignment_id)
        for link in links
        if link.assignment_id is not None
    }
    start, end = bounds(period_start, period_end)
    count = 0

    for group_release, assignment_id in pairs:
        reading_rows = list(
            (
                await session.scalars(
                    select(models.ComicReaderSessionMetric).where(
                        models.ComicReaderSessionMetric.organization_id == organization_id,
                        models.ComicReaderSessionMetric.release_id == group_release,
                        models.ComicReaderSessionMetric.started_at >= start,
                        models.ComicReaderSessionMetric.started_at <= end,
                    )
                )
            ).all()
        )
        reading: dict[uuid.UUID, dict[str, Any]] = defaultdict(
            lambda: {"active": 0.0, "progress": 0.0, "completed": False}
        )
        for row in reading_rows:
            reading[row.user_id]["active"] += row.active_seconds
            reading[row.user_id]["progress"] = max(
                reading[row.user_id]["progress"], row.progress_percent
            )
            reading[row.user_id]["completed"] |= row.completed

        attempts = list(
            (
                await session.scalars(
                    select(StudentAttempt).where(
                        StudentAttempt.organization_id == organization_id,
                        StudentAttempt.assignment_id == assignment_id,
                        StudentAttempt.started_at >= start,
                        StudentAttempt.started_at <= end,
                    )
                )
            ).all()
        )
        best_scores: dict[uuid.UUID, float] = {}
        for attempt in attempts:
            best_scores[attempt.student_id] = max(
                best_scores.get(attempt.student_id, 0.0), attempt.percentage
            )

        matched = [
            (
                float(reading[student]["active"]),
                float(reading[student]["progress"]),
                bool(reading[student]["completed"]),
                float(best_scores[student]),
            )
            for student in set(reading).intersection(best_scores)
        ]
        guard = privacy_guard(len(matched))
        active_values = [row[0] for row in matched]
        progress_values = [row[1] for row in matched]
        score_values = [row[3] for row in matched]
        completed_scores = [row[3] for row in matched if row[2]]
        incomplete_scores = [row[3] for row in matched if not row[2]]
        correlation = pearson(active_values, score_values)
        delta = (
            round(mean(completed_scores) - mean(incomplete_scores), 4)
            if completed_scores and incomplete_scores
            else None
        )
        existing = await session.scalar(
            select(models.ComicReaderLearningMetric).where(
                models.ComicReaderLearningMetric.organization_id == organization_id,
                models.ComicReaderLearningMetric.scope_key == "ORGANIZATION",
                models.ComicReaderLearningMetric.release_id == group_release,
                models.ComicReaderLearningMetric.assignment_id == assignment_id,
                models.ComicReaderLearningMetric.period_start == period_start,
                models.ComicReaderLearningMetric.period_end == period_end,
            )
        )
        item = existing or models.ComicReaderLearningMetric(
            organization_id=organization_id,
            scope_type="ORGANIZATION",
            scope_key="ORGANIZATION",
            scope_id=None,
            release_id=group_release,
            assignment_id=assignment_id,
            period_start=period_start,
            period_end=period_end,
        )
        item.sample_size = len(matched)
        item.average_active_seconds = round(mean(active_values), 2) if active_values else 0.0
        item.average_progress_percent = (
            round(mean(progress_values), 2) if progress_values else 0.0
        )
        item.average_score_percent = round(mean(score_values), 2) if score_values else 0.0
        item.reading_score_correlation = None if guard["suppressed"] else correlation
        item.completion_score_delta = None if guard["suppressed"] else delta
        item.interpretation = (
            "PRIVACY_SUPPRESSED"
            if guard["suppressed"]
            else correlation_label(correlation)
        )
        item.privacy_suppressed = guard["suppressed"]
        item.evidence = {
            "minimum_group_size": MINIMUM_GROUP_SIZE,
            "completed_count": len(completed_scores),
            "incomplete_count": len(incomplete_scores),
        }
        if existing is None:
            session.add(item)
        count += 1
    await session.flush()
    return count


async def refresh_analytics(
    session: AsyncSession,
    *,
    actor: ActorContext,
    period_start: date,
    period_end: date,
    release_id: uuid.UUID | None,
    classroom_id: uuid.UUID | None,
) -> dict[str, Any]:
    start, end = bounds(period_start, period_end)
    version_query = select(
        func.count(models.ComicReaderEvent.id),
        func.max(models.ComicReaderEvent.received_at),
    ).where(
        models.ComicReaderEvent.organization_id == actor.organization_id,
        models.ComicReaderEvent.occurred_at >= start,
        models.ComicReaderEvent.occurred_at <= end,
    )
    if release_id:
        version_query = version_query.where(
            models.ComicReaderEvent.release_id == release_id
        )
    event_count, latest_received_at = (await session.execute(version_query)).one()
    fingerprint = stable_hash(
        {
            "organization": actor.organization_id,
            "period_start": period_start,
            "period_end": period_end,
            "release_id": release_id,
            "classroom_id": classroom_id,
            "event_count": int(event_count or 0),
            "latest_received_at": latest_received_at,
        }
    )
    key = f"comic-reader-analytics:{fingerprint[:48]}"
    job = await session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.organization_id == actor.organization_id,
            BackgroundJob.idempotency_key == key,
        )
    )
    if job and job.status == "completed":
        return {"job_id": str(job.id), "reused": True, **job.result_reference}
    if job is None:
        job = BackgroundJob(
            organization_id=actor.organization_id,
            requested_by_user_id=actor.user_id,
            job_type="comic_reader_analytics_refresh",
            queue_name="default",
            module_name="comic_reader_analytics",
            entity_type="organization",
            entity_id=actor.organization_id,
            status="processing",
            priority=50,
            progress_percent=5,
            current_step="Agregando eventos",
            total_steps=4,
            idempotency_key=key,
            input_snapshot={
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "release_id": str(release_id) if release_id else None,
                "classroom_id": str(classroom_id) if classroom_id else None,
            },
            queued_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.flush()
    else:
        job.status = "processing"
        job.progress_percent = 5
        job.current_step = "Reprocessando analytics"

    sessions = await refresh_session_metrics(
        session,
        organization_id=actor.organization_id,
        period_start=period_start,
        period_end=period_end,
        release_id=release_id,
    )
    job.progress_percent = 35
    content = await refresh_content_metrics(
        session,
        organization_id=actor.organization_id,
        period_start=period_start,
        period_end=period_end,
        release_id=release_id,
    )
    job.progress_percent = 60
    cohorts = await refresh_cohort_metrics(
        session,
        organization_id=actor.organization_id,
        period_start=period_start,
        period_end=period_end,
        release_id=release_id,
        classroom_id=classroom_id,
    )
    job.progress_percent = 80
    learning = await refresh_learning_metrics(
        session,
        organization_id=actor.organization_id,
        period_start=period_start,
        period_end=period_end,
        release_id=release_id,
    )
    result = {
        "session_metrics": len(sessions),
        "content_metrics": content,
        "cohort_metrics": cohorts,
        "learning_metrics": learning,
    }
    job.status = "completed"
    job.progress_percent = 100
    job.current_step = "Analytics atualizados"
    job.result_reference = result
    job.completed_at = datetime.now(UTC)
    await session.commit()
    return {"job_id": str(job.id), "reused": False, **result}


async def generate_alerts(
    session: AsyncSession,
    *,
    actor: ActorContext,
    period_start: date,
    period_end: date,
    release_id: uuid.UUID | None,
    minimum_active_seconds: int,
    maximum_progress_percent: float,
    minimum_sessions: int,
) -> int:
    start, end = bounds(period_start, period_end)
    query = select(models.ComicReaderSessionMetric).where(
        models.ComicReaderSessionMetric.organization_id == actor.organization_id,
        models.ComicReaderSessionMetric.started_at >= start,
        models.ComicReaderSessionMetric.started_at <= end,
    )
    if release_id:
        query = query.where(models.ComicReaderSessionMetric.release_id == release_id)
    rows = list((await session.scalars(query)).all())
    groups: dict[tuple[uuid.UUID, uuid.UUID], list[Any]] = defaultdict(list)
    for row in rows:
        groups[(row.release_id, row.user_id)].append(row)

    created = 0
    for (group_release, student_id), sessions in groups.items():
        active = sum(row.active_seconds for row in sessions)
        progress = max(row.progress_percent for row in sessions)
        if (
            len(sessions) < minimum_sessions
            or active < minimum_active_seconds
            or progress > maximum_progress_percent
        ):
            continue
        rule_code = f"COMIC_LOW_PROGRESS_{str(group_release)[:8]}"
        exists = await session.scalar(
            select(LearningAlert.id).where(
                LearningAlert.organization_id == actor.organization_id,
                LearningAlert.student_id == student_id,
                LearningAlert.rule_code == rule_code,
                LearningAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            )
        )
        if exists:
            continue
        session.add(
            LearningAlert(
                organization_id=actor.organization_id,
                classroom_id=None,
                student_id=student_id,
                assignment_id=None,
                alert_type="comic_reading_low_progress",
                severity=AlertSeverity.ATTENTION,
                status=AlertStatus.OPEN,
                title="Baixo progresso na leitura da HQ",
                description="Foram registradas várias sessões, mas o progresso permaneceu reduzido.",
                explanation=(
                    "O alerta combina sessões, tempo ativo e progresso. "
                    "Ele exige revisão humana e não representa diagnóstico."
                ),
                evidence={
                    "release_id": str(group_release),
                    "sessions": len(sessions),
                    "active_seconds": active,
                    "progress_percent": progress,
                },
                rule_code=rule_code,
            )
        )
        created += 1
    await session.commit()
    return created


def content_csv(rows: list[models.ComicReaderContentMetric]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "release_id", "metric_date", "page_number", "panel_number",
            "viewer_count", "view_count", "completion_count", "revisit_count",
            "total_active_seconds", "glossary_opens", "narration_starts",
            "assessment_opens",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.release_id, row.metric_date, row.page_number, row.panel_number,
                row.viewer_count, row.view_count, row.completion_count,
                row.revisit_count, row.total_active_seconds, row.glossary_opens,
                row.narration_starts, row.assessment_opens,
            ]
        )
    return output.getvalue()
