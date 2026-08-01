from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import mean
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comic_reader_analytics.policies import MINIMUM_GROUP_SIZE, privacy_guard

if TYPE_CHECKING:
    from .compat import ActorContext


COMPLETED_SESSION_STATUSES = {"SUBMITTED", "UNDER_REVIEW", "COMPLETED"}
ABANDONED_SESSION_STATUSES = {"PAUSED", "EXPIRED", "CANCELLED"}


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def scored_summary(observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(observations)
    scored = [
        row
        for row in rows
        if row.get("score") is not None
        and float(row.get("maximum_score") or 0) > 0
    ]
    awarded = sum(float(row["score"]) for row in scored)
    possible = sum(float(row["maximum_score"]) for row in scored)
    correct = sum(
        1
        for row in scored
        if row.get("is_correct") is True
        or float(row["score"]) >= float(row["maximum_score"])
    )
    return {
        "response_count": len(rows),
        "scored_response_count": len(scored),
        "pending_review_count": sum(
            1
            for row in rows
            if row.get("requires_human_review") and row.get("score") is None
        ),
        "correct_count": correct,
        "awarded_score": round(awarded, 4),
        "possible_score": round(possible, 4),
        "accuracy": safe_rate(awarded, possible) if possible else None,
    }


def build_alerts(
    metrics: dict[str, Any],
    skill_metrics: list[dict[str, Any]],
    activity_metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if metrics.get("privacy_suppressed"):
        return []

    alerts: list[dict[str, Any]] = []
    students = int(metrics.get("students") or 0)
    if students and float(metrics.get("completion_rate") or 0) < 60:
        alerts.append(
            {
                "code": "LOW_COMPLETION",
                "signal_key": "LOW_COMPLETION",
                "severity": "priority",
                "title": "Baixa conclusão da experiência pós-HQ",
                "message": "Menos de 60% dos estudantes concluíram a experiência.",
                "explanation": (
                    "A conclusão combina leitura obrigatória e envio das atividades "
                    "canônicas vinculadas à publicação."
                ),
            }
        )
    if (
        int(metrics.get("abandonment_count") or 0) > 0
        and float(metrics.get("abandonment_rate") or 0) >= 30
    ):
        alerts.append(
            {
                "code": "ABANDONMENT",
                "signal_key": "ABANDONMENT",
                "severity": "priority",
                "title": "Possível abandono da experiência pós-HQ",
                "message": "Há estudantes com experiência interrompida ou expirada.",
                "explanation": (
                    "O sinal considera sessões pausadas, expiradas ou canceladas sem "
                    "conclusão registrada."
                ),
            }
        )

    for item in skill_metrics:
        accuracy = item.get("accuracy")
        evidence_count = int(item.get("evidence_count") or 0)
        if accuracy is None or evidence_count == 0:
            continue
        dimension = f"{item.get('skill_type')}:{item.get('skill_code')}"
        if float(accuracy) < 50:
            alerts.append(
                {
                    "code": "SKILL_DIFFICULTY",
                    "signal_key": f"SKILL_DIFFICULTY:{dimension}",
                    "severity": "attention",
                    "title": "Dificuldade em habilidade",
                    "skill_type": item.get("skill_type"),
                    "skill_code": item.get("skill_code"),
                    "accuracy": accuracy,
                    "evidence_count": evidence_count,
                    "message": "Habilidade com acerto inferior a 50%.",
                    "explanation": (
                        "O indicador foi calculado com respostas corrigidas e vínculos "
                        "pedagógicos do Assessment Hub."
                    ),
                }
            )
        elif float(accuracy) >= 85 and evidence_count >= 2:
            alerts.append(
                {
                    "code": "MASTERY_OPPORTUNITY",
                    "signal_key": f"MASTERY_OPPORTUNITY:{dimension}",
                    "severity": "info",
                    "title": "Oportunidade de aprofundamento",
                    "skill_type": item.get("skill_type"),
                    "skill_code": item.get("skill_code"),
                    "accuracy": accuracy,
                    "evidence_count": evidence_count,
                    "message": "Desempenho consistente permite aprofundamento ou desafio.",
                    "explanation": (
                        "A recomendação permanece pendente de revisão docente e não "
                        "altera automaticamente a trilha do estudante."
                    ),
                }
            )

    for item in activity_metrics:
        accuracy = item.get("accuracy")
        response_count = int(item.get("scored_response_count") or 0)
        if accuracy is None or response_count == 0 or float(accuracy) >= 40:
            continue
        activity_id = item.get("activity_id")
        alerts.append(
            {
                "code": "HARD_ACTIVITY",
                "signal_key": f"HARD_ACTIVITY:{activity_id}",
                "severity": "attention",
                "title": "Atividade com dificuldade observada alta",
                "activity_id": activity_id,
                "question_version_id": item.get("question_version_id"),
                "accuracy": accuracy,
                "evidence_count": response_count,
                "message": "Atividade com acerto inferior a 40%.",
                "explanation": (
                    "O cálculo usa somente respostas corrigidas do Assessment Hub; "
                    "respostas pendentes de revisão não são tratadas como erro."
                ),
            }
        )
    return alerts


def reading_answer_correlation(
    *,
    reviewed_correct: int,
    reviewed_total: int,
    not_reviewed_correct: int,
    not_reviewed_total: int,
) -> dict[str, Any]:
    reviewed = safe_rate(reviewed_correct, reviewed_total)
    not_reviewed = safe_rate(not_reviewed_correct, not_reviewed_total)
    sufficient = reviewed_total > 0 and not_reviewed_total > 0
    difference = round(reviewed - not_reviewed, 2) if sufficient else None
    if not sufficient:
        interpretation = "Dados insuficientes para comparar releitura e desempenho."
    elif reviewed > not_reviewed:
        interpretation = "A releitura esteve associada a melhor desempenho."
    else:
        interpretation = "Não foi observada vantagem de desempenho para a releitura."
    return {
        "code": "REVIEW_BEFORE_ANSWER",
        "reviewed_accuracy": reviewed,
        "reviewed_sample_size": reviewed_total,
        "not_reviewed_accuracy": not_reviewed,
        "not_reviewed_sample_size": not_reviewed_total,
        "sample_size": reviewed_total + not_reviewed_total,
        "difference_points": difference,
        "sufficient_data": sufficient,
        "interpretation": interpretation,
    }


def _period_filter(statement: Any, column: Any, period_start: Any, period_end: Any) -> Any:
    if period_start is not None:
        statement = statement.where(column >= period_start)
    if period_end is not None:
        statement = statement.where(column <= period_end)
    return statement


def _scope_id_filter(column: Any, value: uuid.UUID | None) -> Any:
    return column.is_(None) if value is None else column == value


def _response_payload(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "attempt_id": row.attempt_id,
        "question_version_id": row.question_version_id,
        "score": row.score,
        "maximum_score": row.maximum_score,
        "is_correct": row.is_correct,
        "requires_human_review": row.requires_human_review,
        "answered_at": row.answered_at,
    }


async def _sync_learning_alerts(
    session: AsyncSession,
    *,
    actor: ActorContext,
    snapshot: Any,
    alerts: list[dict[str, Any]],
    release_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    from app.models.analytics import (
        AlertSeverity,
        AlertStatus,
        LearningAlert,
    )

    existing = list(
        (
            await session.scalars(
                select(LearningAlert).where(
                    LearningAlert.organization_id == actor.organization_id,
                    LearningAlert.alert_type == "hq_post_learning",
                )
            )
        ).all()
    )
    existing_by_signal = {
        str((item.evidence or {}).get("signal_key")): item
        for item in existing
        if (item.evidence or {}).get("source_snapshot_id") == str(snapshot.id)
    }
    student_id = snapshot.scope_id if snapshot.scope_type == "STUDENT" else None
    classroom_id = snapshot.scope_id if snapshot.scope_type == "CLASS" else None
    synced: list[dict[str, Any]] = []
    active_signals: set[str] = set()

    for alert_data in alerts:
        signal_key = str(alert_data["signal_key"])
        active_signals.add(signal_key)
        evidence = {
            **alert_data,
            "source": "hq_learning_analytics",
            "source_snapshot_id": str(snapshot.id),
            "publication_id": str(snapshot.publication_id),
            "comic_project_id": str(snapshot.comic_project_id),
            "release_id": str(release_id) if release_id else None,
            "scope_type": snapshot.scope_type,
            "scope_id": str(snapshot.scope_id) if snapshot.scope_id else None,
            "period_start": (
                snapshot.period_start.isoformat() if snapshot.period_start else None
            ),
            "period_end": snapshot.period_end.isoformat() if snapshot.period_end else None,
            "progress_percent": float(
                (snapshot.metrics or {}).get("average_reading_progress") or 0.0
            ),
            "assessment_score_percent": alert_data.get("accuracy"),
            "snapshot_metrics": snapshot.metrics,
        }
        item = existing_by_signal.get(signal_key)
        if item is None:
            rule_code = f"HQ_POST:{signal_key}"
            item = LearningAlert(
                organization_id=actor.organization_id,
                classroom_id=classroom_id,
                student_id=student_id,
                assignment_id=None,
                alert_type="hq_post_learning",
                severity=AlertSeverity(alert_data["severity"]),
                status=AlertStatus.OPEN,
                title=str(alert_data["title"]),
                description=str(alert_data["message"]),
                explanation=str(alert_data["explanation"]),
                evidence=evidence,
                rule_code=rule_code[:100],
            )
            session.add(item)
            await session.flush()
        elif item.status in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED}:
            item.severity = AlertSeverity(alert_data["severity"])
            item.title = str(alert_data["title"])
            item.description = str(alert_data["message"])
            item.explanation = str(alert_data["explanation"])
            item.evidence = evidence

        synced.append(
            {
                **alert_data,
                "learning_alert_id": str(item.id),
                "actionable": release_id is not None,
                "human_approval_required": True,
            }
        )

    for signal_key, item in existing_by_signal.items():
        if signal_key in active_signals or item.status != AlertStatus.OPEN:
            continue
        item.status = AlertStatus.RESOLVED
        item.resolved_at = datetime.now(UTC)
        item.evidence = {
            **(item.evidence or {}),
            "auto_resolution_reason": "SIGNAL_NOT_PRESENT_ON_REGENERATION",
        }
    return synced


async def generate_snapshot(
    session: AsyncSession,
    *,
    actor: ActorContext,
    publication_id: uuid.UUID,
    scope_type: str,
    scope_id: uuid.UUID | None,
    period_start: Any,
    period_end: Any,
):
    from app.assessment_delivery.models import (
        AssessmentPublication,
        AssessmentSession,
        AssessmentTarget,
    )
    from app.assessment_hub.models import AssessmentResponse, QuestionSkillLink
    from app.comic_reader_analytics.models import ComicReaderEvent
    from app.comic_review_publish.models import ComicEditorialRelease

    from . import models

    normalized_scope = scope_type.upper()
    if normalized_scope in {"STUDENT", "CLASS", "ACTIVITY"} and scope_id is None:
        raise HTTPException(422, "scope_id é obrigatório para o escopo informado.")
    if period_start and period_end and period_end < period_start:
        raise HTTPException(422, "period_end deve ser igual ou posterior a period_start.")

    publication = await session.scalar(
        select(AssessmentPublication)
        .where(
            AssessmentPublication.organization_id == actor.organization_id,
            AssessmentPublication.id == publication_id,
        )
        .with_for_update()
    )
    if publication is None:
        raise HTTPException(404, "Publicação não encontrada.")
    delivery = await session.scalar(
        select(models.HQActivityDeliveryLink).where(
            models.HQActivityDeliveryLink.organization_id == actor.organization_id,
            models.HQActivityDeliveryLink.publication_id == publication_id,
        )
    )
    if delivery is None:
        raise HTTPException(404, "Aplicação pós-HQ não encontrada.")

    session_statement = select(AssessmentSession).where(
        AssessmentSession.organization_id == actor.organization_id,
        AssessmentSession.publication_id == publication_id,
    )
    session_statement = _period_filter(
        session_statement,
        AssessmentSession.created_at,
        period_start,
        period_end,
    )
    if normalized_scope == "STUDENT":
        session_statement = session_statement.where(
            AssessmentSession.student_id == scope_id
        )
    elif normalized_scope == "CLASS":
        target_ids = select(AssessmentTarget.id).where(
            AssessmentTarget.organization_id == actor.organization_id,
            AssessmentTarget.publication_id == publication_id,
            AssessmentTarget.target_type == "CLASSROOM",
            AssessmentTarget.target_id == scope_id,
        )
        session_statement = session_statement.where(
            AssessmentSession.target_id.in_(target_ids)
        )
    sessions = list((await session.scalars(session_statement)).all())
    session_student_ids = {item.student_id for item in sessions}

    state_statement = select(models.HQStudentExperienceState).where(
        models.HQStudentExperienceState.organization_id == actor.organization_id,
        models.HQStudentExperienceState.publication_id == publication_id,
    )
    if normalized_scope == "STUDENT":
        state_statement = state_statement.where(
            models.HQStudentExperienceState.student_id == scope_id
        )
    elif normalized_scope == "CLASS":
        state_statement = state_statement.where(
            models.HQStudentExperienceState.student_id.in_(session_student_ids)
        )
    states = list((await session.scalars(state_statement)).all())
    student_ids = session_student_ids | {item.student_id for item in states}

    activity_statement = (
        select(models.HQActivityBinding)
        .where(
            models.HQActivityBinding.organization_id == actor.organization_id,
            models.HQActivityBinding.comic_project_id == delivery.comic_project_id,
            models.HQActivityBinding.publication_id == publication_id,
        )
        .order_by(models.HQActivityBinding.display_order)
    )
    if normalized_scope == "ACTIVITY":
        activity_statement = activity_statement.where(
            models.HQActivityBinding.id == scope_id
        )
    activities = list((await session.scalars(activity_statement)).all())
    if normalized_scope == "ACTIVITY" and not activities:
        raise HTTPException(404, "Atividade não encontrada nesta publicação.")

    attempt_ids = {item.assessment_hub_attempt_id for item in sessions}
    responses: list[Any] = []
    if attempt_ids:
        response_statement = select(AssessmentResponse).where(
            AssessmentResponse.organization_id == actor.organization_id,
            AssessmentResponse.attempt_id.in_(attempt_ids),
        )
        response_statement = _period_filter(
            response_statement,
            AssessmentResponse.answered_at,
            period_start,
            period_end,
        )
        responses = list((await session.scalars(response_statement)).all())

    responses_by_question: dict[uuid.UUID, list[dict[str, Any]]] = defaultdict(list)
    for response in responses:
        responses_by_question[response.question_version_id].append(
            _response_payload(response)
        )

    activity_metrics: list[dict[str, Any]] = []
    activities_by_question: dict[uuid.UUID, Any] = {}
    for item in activities:
        if item.question_version_id:
            activities_by_question[item.question_version_id] = item
        observations = responses_by_question.get(item.question_version_id, [])
        summary = scored_summary(observations)
        activity_metrics.append(
            {
                "activity_id": str(item.id),
                "question_version_id": (
                    str(item.question_version_id) if item.question_version_id else None
                ),
                "title": item.title,
                "activity_type": item.activity_type,
                "difficulty": item.difficulty,
                "max_score": item.max_score,
                "attempt_count": len(
                    {row["attempt_id"] for row in observations}
                ),
                "source_page_id": (
                    str(item.source_page_id) if item.source_page_id else None
                ),
                **summary,
            }
        )

    question_version_ids = set(activities_by_question)
    skill_links: list[Any] = []
    if question_version_ids:
        skill_links = list(
            (
                await session.scalars(
                    select(QuestionSkillLink).where(
                        QuestionSkillLink.organization_id == actor.organization_id,
                        QuestionSkillLink.question_version_id.in_(question_version_ids),
                    )
                )
            ).all()
        )
    links_by_question: dict[uuid.UUID, list[Any]] = defaultdict(list)
    for link in skill_links:
        links_by_question[link.question_version_id].append(link)

    skill_buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for question_version_id, observations in responses_by_question.items():
        activity = activities_by_question.get(question_version_id)
        if activity is None:
            continue
        for observation in observations:
            score = observation.get("score")
            maximum = float(observation.get("maximum_score") or 0)
            if score is None or maximum <= 0:
                continue
            ratio = min(1.0, max(0.0, float(score) / maximum))
            for link in links_by_question.get(question_version_id, []):
                key = (link.skill_type, link.skill_code)
                bucket = skill_buckets.setdefault(
                    key,
                    {
                        "weighted_score": 0.0,
                        "weight": 0.0,
                        "evidence_count": 0,
                        "activity_ids": set(),
                    },
                )
                weight = max(0.0, float(link.weight))
                bucket["weighted_score"] += ratio * weight
                bucket["weight"] += weight
                bucket["evidence_count"] += 1
                bucket["activity_ids"].add(str(activity.id))

    skill_metrics = [
        {
            "skill_type": skill_type,
            "skill_code": skill_code,
            "accuracy": (
                safe_rate(bucket["weighted_score"], bucket["weight"])
                if bucket["weight"]
                else None
            ),
            "evidence_count": bucket["evidence_count"],
            "activity_count": len(bucket["activity_ids"]),
            "activity_ids": sorted(bucket["activity_ids"]),
        }
        for (skill_type, skill_code), bucket in sorted(skill_buckets.items())
    ]

    latest_session_by_student: dict[uuid.UUID, Any] = {}
    for item in sorted(sessions, key=lambda row: row.created_at):
        latest_session_by_student[item.student_id] = item
    completed_students = {
        item.student_id
        for item in states
        if item.current_stage == "COMPLETED" or item.completed_at is not None
    }
    abandoned_students = {
        student_id
        for student_id, item in latest_session_by_student.items()
        if item.status in ABANDONED_SESSION_STATUSES
        and student_id not in completed_students
    }
    group_scope = normalized_scope != "STUDENT"
    guard = (
        privacy_guard(len(student_ids))
        if group_scope
        else {
            "sample_size": len(student_ids),
            "minimum_group_size": MINIMUM_GROUP_SIZE,
            "suppressed": False,
            "reason": None,
        }
    )
    metrics = {
        "students": len(student_ids),
        "sessions": len(sessions),
        "submitted_sessions": sum(
            item.status in COMPLETED_SESSION_STATUSES for item in sessions
        ),
        "reading_completion_rate": safe_rate(
            sum(1 for item in states if item.reading_progress >= 100),
            len(states),
        ),
        "activity_completion_rate": safe_rate(
            sum(1 for item in states if item.activity_progress >= 100),
            len(states),
        ),
        "completion_rate": safe_rate(len(completed_students), len(student_ids)),
        "abandonment_count": len(abandoned_students),
        "abandonment_rate": safe_rate(len(abandoned_students), len(student_ids)),
        "average_reading_progress": (
            round(mean([item.reading_progress for item in states]), 2)
            if states
            else 0.0
        ),
        "average_activity_progress": (
            round(mean([item.activity_progress for item in states]), 2)
            if states
            else 0.0
        ),
        "average_answered_count": (
            round(mean([item.answered_count for item in states]), 2)
            if states
            else 0.0
        ),
        "resume_usage_rate": safe_rate(
            sum(1 for item in states if item.last_sequence > 1),
            len(states),
        ),
        "response_count": len(responses),
        "scored_response_count": sum(
            item["scored_response_count"] for item in activity_metrics
        ),
        "pending_review_count": sum(
            item["pending_review_count"] for item in activity_metrics
        ),
        "unmapped_activity_count": sum(
            1
            for item in activities
            if item.question_version_id not in links_by_question
        ),
        "privacy_suppressed": guard["suppressed"],
        "privacy_reason": guard["reason"],
        "minimum_group_size": guard["minimum_group_size"],
    }

    release_ids = {item.release_id for item in states if item.release_id}
    release_id = next(iter(release_ids), None) if len(release_ids) == 1 else None
    if release_id is None:
        release_id = await session.scalar(
            select(ComicEditorialRelease.id)
            .where(
                ComicEditorialRelease.organization_id == actor.organization_id,
                ComicEditorialRelease.comic_project_id == delivery.comic_project_id,
                ComicEditorialRelease.status == "PUBLISHED",
            )
            .order_by(ComicEditorialRelease.release_number.desc())
            .limit(1)
        )
    metrics["release_id"] = str(release_id) if release_id else None

    pages = list(
        (
            await session.scalars(
                select(models.HQEditorPage)
                .where(
                    models.HQEditorPage.organization_id == actor.organization_id,
                    models.HQEditorPage.comic_project_id == delivery.comic_project_id,
                    models.HQEditorPage.page_type.in_(
                        ["COVER", "STORY", "BACK_COVER"]
                    ),
                )
                .order_by(models.HQEditorPage.page_number)
            )
        ).all()
    )
    reader_events: list[Any] = []
    if release_id and student_ids:
        event_statement = select(ComicReaderEvent).where(
            ComicReaderEvent.organization_id == actor.organization_id,
            ComicReaderEvent.release_id == release_id,
            ComicReaderEvent.user_id.in_(student_ids),
            ComicReaderEvent.event_type.in_(
                ["PAGE_VIEWED", "POSITION_DWELL"]
            ),
        )
        event_statement = _period_filter(
            event_statement,
            ComicReaderEvent.occurred_at,
            period_start,
            period_end,
        )
        reader_events = list((await session.scalars(event_statement)).all())
        reader_events = [
            event
            for event in reader_events
            if not (event.properties or {}).get("publication_id")
            or (event.properties or {}).get("publication_id") == str(publication_id)
        ]

    views_by_page_user: dict[tuple[int, uuid.UUID], int] = defaultdict(int)
    duration_by_page: dict[int, int] = defaultdict(int)
    for event in reader_events:
        if event.page_number is None:
            continue
        if event.event_type == "PAGE_VIEWED":
            views_by_page_user[(event.page_number, event.user_id)] += 1
        elif event.event_type == "POSITION_DWELL":
            duration_by_page[event.page_number] += event.duration_ms

    page_metrics: list[dict[str, Any]] = []
    for page in pages:
        page_views = {
            user_id: count
            for (page_number, user_id), count in views_by_page_user.items()
            if page_number == page.page_number
        }
        viewer_count = len(page_views)
        page_metrics.append(
            {
                "page_id": str(page.id),
                "page_number": page.page_number,
                "title": page.title,
                "viewer_count": viewer_count,
                "view_count": sum(page_views.values()),
                "revisit_count": sum(max(0, count - 1) for count in page_views.values()),
                "average_active_seconds": (
                    round(duration_by_page[page.page_number] / 1000 / viewer_count, 2)
                    if viewer_count
                    else 0.0
                ),
            }
        )

    attempts_by_id = {
        item.assessment_hub_attempt_id: item for item in sessions
    }
    page_number_by_id = {item.id: item.page_number for item in pages}
    page_view_times: dict[tuple[uuid.UUID, int], list[datetime]] = defaultdict(list)
    for event in reader_events:
        if event.event_type == "PAGE_VIEWED" and event.page_number is not None:
            page_view_times[(event.user_id, event.page_number)].append(
                event.occurred_at
            )

    reviewed_correct = reviewed_total = 0
    not_reviewed_correct = not_reviewed_total = 0
    for response in responses:
        if response.score is None:
            continue
        assessment_session = attempts_by_id.get(response.attempt_id)
        activity = activities_by_question.get(response.question_version_id)
        if assessment_session is None or activity is None or not activity.source_page_id:
            continue
        page_number = page_number_by_id.get(activity.source_page_id)
        if page_number is None:
            continue
        prior_views = sum(
            occurred_at <= response.answered_at
            for occurred_at in page_view_times.get(
                (assessment_session.student_id, page_number),
                [],
            )
        )
        correct = response.is_correct is True or (
            response.maximum_score > 0
            and float(response.score) >= float(response.maximum_score)
        )
        if prior_views >= 2:
            reviewed_total += 1
            reviewed_correct += int(correct)
        else:
            not_reviewed_total += 1
            not_reviewed_correct += int(correct)

    correlations = [
        reading_answer_correlation(
            reviewed_correct=reviewed_correct,
            reviewed_total=reviewed_total,
            not_reviewed_correct=not_reviewed_correct,
            not_reviewed_total=not_reviewed_total,
        )
    ]
    alert_payloads = build_alerts(metrics, skill_metrics, activity_metrics)

    snapshot = await session.scalar(
        select(models.HQLearningAnalyticsSnapshot).where(
            models.HQLearningAnalyticsSnapshot.organization_id
            == actor.organization_id,
            models.HQLearningAnalyticsSnapshot.publication_id == publication_id,
            models.HQLearningAnalyticsSnapshot.scope_type == normalized_scope,
            _scope_id_filter(
                models.HQLearningAnalyticsSnapshot.scope_id,
                scope_id,
            ),
            models.HQLearningAnalyticsSnapshot.period_start == period_start,
            models.HQLearningAnalyticsSnapshot.period_end == period_end,
        )
    )
    if snapshot is None:
        snapshot = models.HQLearningAnalyticsSnapshot(
            organization_id=actor.organization_id,
            comic_project_id=delivery.comic_project_id,
            publication_id=publication_id,
            scope_type=normalized_scope,
            scope_id=scope_id,
            period_start=period_start,
            period_end=period_end,
            generated_by_user_id=actor.user_id,
        )
        session.add(snapshot)

    snapshot.metrics = metrics
    snapshot.skill_metrics = skill_metrics
    snapshot.page_metrics = page_metrics
    snapshot.activity_metrics = activity_metrics
    snapshot.correlations = correlations
    snapshot.generated_by_user_id = actor.user_id
    snapshot.generated_at = datetime.now(UTC)
    await session.flush()
    snapshot.alerts = await _sync_learning_alerts(
        session,
        actor=actor,
        snapshot=snapshot,
        alerts=alert_payloads,
        release_id=release_id,
    )
    await session.flush()
    return snapshot


async def latest_snapshot(
    session: AsyncSession,
    *,
    actor: ActorContext,
    publication_id: uuid.UUID,
    scope_type: str = "PUBLICATION",
    scope_id: uuid.UUID | None = None,
):
    from . import models

    normalized_scope = scope_type.upper()
    scope_filter = (
        models.HQLearningAnalyticsSnapshot.scope_id.is_(None)
        if scope_id is None
        else models.HQLearningAnalyticsSnapshot.scope_id == scope_id
    )
    return await session.scalar(
        select(models.HQLearningAnalyticsSnapshot)
        .where(
            models.HQLearningAnalyticsSnapshot.organization_id
            == actor.organization_id,
            models.HQLearningAnalyticsSnapshot.publication_id == publication_id,
            models.HQLearningAnalyticsSnapshot.scope_type == normalized_scope,
            scope_filter,
        )
        .order_by(models.HQLearningAnalyticsSnapshot.generated_at.desc())
    )
