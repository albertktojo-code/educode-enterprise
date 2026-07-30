from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comic_reader_access.services import release_for_actor
from app.services.consolidated_audit import append_domain_audit

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import MINIMUM_GROUP_SIZE, privacy_guard, safe_rate
from .schemas import AlertGenerationRequest, AnalyticsRefreshRequest, ReaderEventBatch
from .services import (
    bounds,
    content_csv,
    generate_alerts,
    ingest_events,
    refresh_analytics,
)

router = APIRouter(prefix="/comic-reader-analytics", tags=["comic-reader-analytics"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]
ANALYTICS_ROLES = {
    "OWNER", "ADMIN", "ORG_ADMIN", "PLATFORM_ADMIN", "TEACHER",
    "COORDINATOR", "PEDAGOGICAL_COORDINATOR",
}


def require_analytics(actor: ActorContext) -> None:
    if not set(actor.roles).intersection(ANALYTICS_ROLES):
        raise HTTPException(403, "Permissao insuficiente para analytics de leitura.")


def resolve_period(
    period_start: date | None,
    period_end: date | None,
) -> tuple[date, date]:
    end = period_end or date.today()
    start = period_start or (end - timedelta(days=30))
    if end < start:
        raise HTTPException(422, "period_end precisa ser igual ou posterior a period_start.")
    if (end - start).days > 366:
        raise HTTPException(422, "O periodo de analytics nao pode exceder 366 dias.")
    return start, end


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "16.6", "module": "comic-reader-analytics"}


@router.post("/events/batch")
async def create_events(data: ReaderEventBatch, session: SessionDep, actor: ActorDep):
    release_ids = {event.release_id for event in data.events}
    if len(release_ids) > 10:
        raise HTTPException(422, "Um lote pode conter no maximo dez releases.")
    for release_id in release_ids:
        await release_for_actor(session, actor=actor, release_id=release_id)
    try:
        return await ingest_events(session, actor=actor, events=data.events)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get("/me/summary")
async def my_summary(
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    period_start, period_end = resolve_period(period_start, period_end)
    start, end = bounds(period_start, period_end)
    rows = list(
        (
            await session.scalars(
                select(models.ComicReaderSessionMetric).where(
                    models.ComicReaderSessionMetric.organization_id == actor.organization_id,
                    models.ComicReaderSessionMetric.user_id == actor.user_id,
                    models.ComicReaderSessionMetric.started_at >= start,
                    models.ComicReaderSessionMetric.started_at <= end,
                )
            )
        ).all()
    )
    return {
        "sessions": len(rows),
        "active_seconds": sum(row.active_seconds for row in rows),
        "completed_releases": len({row.release_id for row in rows if row.completed}),
        "average_progress_percent": (
            round(sum(row.progress_percent for row in rows) / len(rows), 2)
            if rows else 0.0
        ),
        "glossary_opens": sum(row.glossary_opens for row in rows),
        "narration_seconds": sum(row.narration_seconds for row in rows),
    }


@router.post("/refresh")
async def refresh(data: AnalyticsRefreshRequest, session: SessionDep, actor: ActorDep):
    require_analytics(actor)
    result = await refresh_analytics(
        session,
        actor=actor,
        period_start=data.period_start,
        period_end=data.period_end,
        release_id=data.release_id,
        classroom_id=data.classroom_id,
    )
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_analytics",
        action="comic.reader.analytics.refreshed",
        entity_type="background_job",
        entity_id=uuid.UUID(result["job_id"]),
        details=data.model_dump(mode="json"),
    )
    await session.commit()
    if data.generate_alerts:
        result["alerts_created"] = await generate_alerts(
            session,
            actor=actor,
            period_start=data.period_start,
            period_end=data.period_end,
            release_id=data.release_id,
            minimum_active_seconds=120,
            maximum_progress_percent=35.0,
            minimum_sessions=2,
        )
    return result


@router.get("/overview")
async def overview(
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    release_id: uuid.UUID | None = None,
):
    require_analytics(actor)
    period_start, period_end = resolve_period(period_start, period_end)
    start, end = bounds(period_start, period_end)
    query = select(models.ComicReaderSessionMetric).where(
        models.ComicReaderSessionMetric.organization_id == actor.organization_id,
        models.ComicReaderSessionMetric.started_at >= start,
        models.ComicReaderSessionMetric.started_at <= end,
    )
    if release_id:
        query = query.where(models.ComicReaderSessionMetric.release_id == release_id)
    rows = list((await session.scalars(query)).all())
    students = {row.user_id for row in rows}
    completed = {row.user_id for row in rows if row.completed}
    return {
        "period_start": period_start,
        "period_end": period_end,
        "students": len(students),
        "releases": len({row.release_id for row in rows}),
        "sessions": len(rows),
        "active_seconds": sum(row.active_seconds for row in rows),
        "completion_rate": safe_rate(len(completed), len(students)),
        "average_progress_percent": (
            round(sum(row.progress_percent for row in rows) / len(rows), 2)
            if rows else 0.0
        ),
        "revisits": sum(row.revisits for row in rows),
        "glossary_opens": sum(row.glossary_opens for row in rows),
        "narration_seconds": sum(row.narration_seconds for row in rows),
        "accessibility_actions": sum(row.accessibility_actions for row in rows),
        "presentation_syncs": sum(row.presentation_syncs for row in rows),
    }


@router.get("/releases/{release_id}/content")
async def content_metrics(
    release_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    require_analytics(actor)
    period_start, period_end = resolve_period(period_start, period_end)
    rows = list(
        (
            await session.scalars(
                select(models.ComicReaderContentMetric)
                .where(
                    models.ComicReaderContentMetric.organization_id == actor.organization_id,
                    models.ComicReaderContentMetric.release_id == release_id,
                    models.ComicReaderContentMetric.metric_date >= period_start,
                    models.ComicReaderContentMetric.metric_date <= period_end,
                )
                .order_by(
                    models.ComicReaderContentMetric.page_number,
                    models.ComicReaderContentMetric.panel_number,
                    models.ComicReaderContentMetric.metric_date,
                )
            )
        ).all()
    )
    return [
        {
            "metric_date": row.metric_date,
            "page_number": row.page_number,
            "panel_number": row.panel_number,
            "viewer_count": row.viewer_count,
            "view_count": row.view_count,
            "completion_count": row.completion_count,
            "revisit_count": row.revisit_count,
            "total_active_seconds": row.total_active_seconds,
            "glossary_opens": row.glossary_opens,
            "narration_starts": row.narration_starts,
            "assessment_opens": row.assessment_opens,
        }
        for row in rows
    ]


@router.get("/classrooms/{classroom_id}")
async def classroom_metrics(
    classroom_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    require_analytics(actor)
    period_start, period_end = resolve_period(period_start, period_end)
    rows = list(
        (
            await session.scalars(
                select(models.ComicReaderCohortMetric).where(
                    models.ComicReaderCohortMetric.organization_id == actor.organization_id,
                    models.ComicReaderCohortMetric.classroom_id == classroom_id,
                    models.ComicReaderCohortMetric.period_start == period_start,
                    models.ComicReaderCohortMetric.period_end == period_end,
                )
            )
        ).all()
    )
    return [
        {
            "release_id": str(row.release_id),
            "privacy": privacy_guard(row.started_students, MINIMUM_GROUP_SIZE),
            "enrolled_students": row.enrolled_students,
            "started_students": None if row.privacy_suppressed else row.started_students,
            "completed_students": None if row.privacy_suppressed else row.completed_students,
            "completion_rate": None if row.privacy_suppressed else row.completion_rate,
            "average_active_seconds": None if row.privacy_suppressed else row.average_active_seconds,
            "median_progress_percent": None if row.privacy_suppressed else row.median_progress_percent,
            "presentation_participants": None if row.privacy_suppressed else row.presentation_participants,
            "narration_users": None if row.privacy_suppressed else row.narration_users,
            "accessibility_users": None if row.privacy_suppressed else row.accessibility_users,
        }
        for row in rows
    ]


@router.get("/releases/{release_id}/learning")
async def learning_metrics(
    release_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    require_analytics(actor)
    period_start, period_end = resolve_period(period_start, period_end)
    rows = list(
        (
            await session.scalars(
                select(models.ComicReaderLearningMetric).where(
                    models.ComicReaderLearningMetric.organization_id == actor.organization_id,
                    models.ComicReaderLearningMetric.release_id == release_id,
                    models.ComicReaderLearningMetric.period_start == period_start,
                    models.ComicReaderLearningMetric.period_end == period_end,
                )
            )
        ).all()
    )
    return [
        {
            "scope_type": row.scope_type,
            "scope_id": str(row.scope_id) if row.scope_id else None,
            "assignment_id": str(row.assignment_id),
            "sample_size": row.sample_size,
            "average_active_seconds": row.average_active_seconds,
            "average_progress_percent": row.average_progress_percent,
            "average_score_percent": row.average_score_percent,
            "reading_score_correlation": row.reading_score_correlation,
            "completion_score_delta": row.completion_score_delta,
            "interpretation": row.interpretation,
            "privacy_suppressed": row.privacy_suppressed,
            "evidence": row.evidence,
        }
        for row in rows
    ]


@router.get("/accessibility")
async def accessibility_metrics(
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    release_id: uuid.UUID | None = None,
):
    require_analytics(actor)
    period_start, period_end = resolve_period(period_start, period_end)
    start, end = bounds(period_start, period_end)
    query = select(models.ComicReaderSessionMetric).where(
        models.ComicReaderSessionMetric.organization_id == actor.organization_id,
        models.ComicReaderSessionMetric.started_at >= start,
        models.ComicReaderSessionMetric.started_at <= end,
    )
    if release_id:
        query = query.where(models.ComicReaderSessionMetric.release_id == release_id)
    rows = list((await session.scalars(query)).all())
    users = {row.user_id for row in rows}
    narration_users = {row.user_id for row in rows if row.narration_seconds > 0}
    accessibility_users = {row.user_id for row in rows if row.accessibility_actions > 0}
    return {
        "users": len(users),
        "narration_users": len(narration_users),
        "accessibility_users": len(accessibility_users),
        "narration_adoption_rate": safe_rate(len(narration_users), len(users)),
        "accessibility_adoption_rate": safe_rate(len(accessibility_users), len(users)),
        "narration_seconds": sum(row.narration_seconds for row in rows),
        "accessibility_actions": sum(row.accessibility_actions for row in rows),
    }


@router.post("/alerts/generate")
async def generate_alerts_endpoint(
    data: AlertGenerationRequest,
    session: SessionDep,
    actor: ActorDep,
):
    require_analytics(actor)
    created = await generate_alerts(
        session,
        actor=actor,
        period_start=data.period_start,
        period_end=data.period_end,
        release_id=data.release_id,
        minimum_active_seconds=data.minimum_active_seconds,
        maximum_progress_percent=data.maximum_progress_percent,
        minimum_sessions=data.minimum_sessions,
    )
    return {"created": created, "alerts_path": "/analytics/alerts"}


@router.get("/releases/{release_id}/export.csv")
async def export_csv(
    release_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    require_analytics(actor)
    period_start, period_end = resolve_period(period_start, period_end)
    rows = list(
        (
            await session.scalars(
                select(models.ComicReaderContentMetric).where(
                    models.ComicReaderContentMetric.organization_id == actor.organization_id,
                    models.ComicReaderContentMetric.release_id == release_id,
                    models.ComicReaderContentMetric.metric_date >= period_start,
                    models.ComicReaderContentMetric.metric_date <= period_end,
                )
            )
        ).all()
    )
    content = content_csv(rows)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_analytics",
        action="comic.reader.analytics.exported",
        entity_type="comic_editorial_release",
        entity_id=release_id,
        details={
            "format": "CSV",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "rows": len(rows),
        },
    )
    await session.commit()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="comic-reader-{release_id}.csv"'
        },
    )
