from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_evolution.models import AccessibleResourceVersion
from app.adaptive_insights.models import InterventionOutcomeRecord
from app.comic_reader_access.models import (
    ComicEmbeddedAssessmentLink,
    ComicReadingCheckpoint,
)
from app.comic_reader_analytics.models import (
    ComicReaderEvent,
    ComicReaderLearningMetric,
    ComicReaderSessionMetric,
)
from app.comic_review_publish.models import ComicEditorialRelease
from app.core.config import get_settings
from app.models.adaptive import (
    AdaptiveLearningPath,
    AdaptiveModelVersion,
    AdaptiveRecommendation,
    AdaptiveRecommendationEvidence,
)
from app.models.ai_runtime import AIGenerationRequest
from app.models.analytics import (
    AlertStatus,
    InterventionStatus,
    InterventionType,
    LearningAlert,
    LearningIntervention,
    LearningInterventionEvent,
)
from app.models.auth import Membership, Organization
from app.models.delivery import MaterialAssignment, StudentAttempt
from app.models.education import Classroom, ClassroomEnrollment
from app.schemas.ai_runtime import AIGenerationCreate
from app.services.adaptive import (
    approve_recommendation_as_path,
    calculate_path_outcome,
)
from app.services.ai.orchestrator import (
    AIOrchestrationError,
    create_generation_request,
)

from .compat import ActorContext
from .policies import (
    build_plan,
    canonical_intervention_type,
    choose_recommendation_type,
    comparable_outcome,
    confidence_from_evidence,
    due_dates,
    intervention_priority,
)

ACTIVE_INTERVENTION_STATUSES = {
    InterventionStatus.PLANNED,
    InterventionStatus.ACTIVE,
}


def _uuid(value: Any) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


async def orchestration_model(
    session: AsyncSession,
    *,
    actor: ActorContext,
) -> AdaptiveModelVersion:
    # Serializes first-use creation per organization and prevents duplicate
    # system models under concurrent proposal requests.
    await session.execute(
        select(Organization.id)
        .where(Organization.id == actor.organization_id)
        .with_for_update()
    )
    item = await session.scalar(
        select(AdaptiveModelVersion).where(
            AdaptiveModelVersion.organization_id == actor.organization_id,
            AdaptiveModelVersion.code == "comic-intervention-orchestrator",
            AdaptiveModelVersion.version == 1,
        )
    )
    if item is None:
        item = AdaptiveModelVersion(
            organization_id=actor.organization_id,
            code="comic-intervention-orchestrator",
            name="Orquestrador de intervenções com HQs",
            version=1,
            status="active",
            description=(
                "Regras explicáveis que combinam alertas, leitura, avaliações, "
                "acessibilidade e histórico de intervenções."
            ),
            rules_json={
                "human_approval_required": True,
                "automatic_application": False,
                "sources": [
                    "learning_alerts",
                    "hq_learning_analytics_snapshots",
                    "assessment_hub_responses",
                    "comic_reader_session_metrics",
                    "student_attempts",
                    "intervention_outcomes",
                ],
            },
            thresholds_json={
                "low_progress_percent": 40,
                "low_score_percent": 50,
            },
            minimum_evidence_count=2,
            is_default=False,
            created_by_user_id=actor.user_id,
            approved_by_user_id=actor.user_id,
            approved_at=datetime.now(UTC),
        )
        session.add(item)
        await session.flush()
    from app.institutional_governance.services import (
        GovernanceExecutionError,
        assert_adaptive_model_allowed,
    )

    try:
        await assert_adaptive_model_allowed(
            session,
            organization_id=actor.organization_id,
            enforcement_mode=get_settings().governance_enforcement_mode,
            model_version_id=item.id,
        )
    except GovernanceExecutionError as error:
        raise HTTPException(409, str(error)) from error
    return item


async def resolve_release_id(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    alert: LearningAlert,
) -> uuid.UUID | None:
    release_id = _uuid((alert.evidence or {}).get("release_id"))
    if release_id:
        exists = await session.scalar(
            select(ComicEditorialRelease.id).where(
                ComicEditorialRelease.organization_id == organization_id,
                ComicEditorialRelease.id == release_id,
            )
        )
        if exists:
            return exists

    if alert.assignment_id:
        return await session.scalar(
            select(ComicEmbeddedAssessmentLink.release_id)
            .where(
                ComicEmbeddedAssessmentLink.organization_id == organization_id,
                ComicEmbeddedAssessmentLink.assignment_id == alert.assignment_id,
            )
            .order_by(
                ComicEmbeddedAssessmentLink.page_number,
                ComicEmbeddedAssessmentLink.display_order,
            )
            .limit(1)
        )
    return None


async def alert_is_hq_linked(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    alert: LearningAlert,
) -> bool:
    return bool(
        await resolve_release_id(
            session,
            organization_id=organization_id,
            alert=alert,
        )
    )


async def evidence_snapshot(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    alert: LearningAlert,
) -> dict[str, Any]:
    settings = get_settings()
    window_start = alert.created_at - timedelta(
        days=settings.intervention_evidence_window_days
    )
    student_id = alert.student_id
    release_id = await resolve_release_id(
        session,
        organization_id=organization_id,
        alert=alert,
    )
    progress_percent = float((alert.evidence or {}).get("progress_percent", 0.0))
    active_seconds = int((alert.evidence or {}).get("active_seconds", 0))
    session_count = int((alert.evidence or {}).get("sessions", 0))
    completed = False
    page_number: int | None = None
    panel_number: int | None = None
    glossary_opens = 0
    narration_seconds = 0
    accessibility_actions = 0

    if student_id and release_id:
        checkpoint = await session.scalar(
            select(ComicReadingCheckpoint).where(
                ComicReadingCheckpoint.organization_id == organization_id,
                ComicReadingCheckpoint.release_id == release_id,
                ComicReadingCheckpoint.user_id == student_id,
            )
        )
        if checkpoint:
            progress_percent = max(progress_percent, checkpoint.progress_percent)
            completed = checkpoint.completed_at is not None

        sessions = list(
            (
                await session.scalars(
                    select(ComicReaderSessionMetric).where(
                        ComicReaderSessionMetric.organization_id == organization_id,
                        ComicReaderSessionMetric.release_id == release_id,
                        ComicReaderSessionMetric.user_id == student_id,
                        ComicReaderSessionMetric.started_at >= window_start,
                    )
                )
            ).all()
        )
        if sessions:
            active_seconds = sum(item.active_seconds for item in sessions)
            session_count = len(sessions)
            progress_percent = max(
                [progress_percent, *[item.progress_percent for item in sessions]]
            )
            completed = completed or any(item.completed for item in sessions)
            glossary_opens = sum(item.glossary_opens for item in sessions)
            narration_seconds = sum(item.narration_seconds for item in sessions)
            accessibility_actions = sum(
                item.accessibility_actions for item in sessions
            )

        events = list(
            (
                await session.scalars(
                    select(ComicReaderEvent).where(
                        ComicReaderEvent.organization_id == organization_id,
                        ComicReaderEvent.release_id == release_id,
                        ComicReaderEvent.user_id == student_id,
                        ComicReaderEvent.occurred_at >= window_start,
                        ComicReaderEvent.event_type.in_(
                            ["PAGE_VIEWED", "PANEL_VIEWED", "POSITION_DWELL"]
                        ),
                    )
                )
            ).all()
        )
        positions: dict[tuple[int | None, int | None], dict[str, int]] = defaultdict(
            lambda: {"views": 0, "duration_ms": 0}
        )
        for event in events:
            key = (event.page_number, event.panel_number)
            if event.event_type in {"PAGE_VIEWED", "PANEL_VIEWED"}:
                positions[key]["views"] += 1
            if event.event_type == "POSITION_DWELL":
                positions[key]["duration_ms"] += event.duration_ms
        if positions:
            (page_number, panel_number), _ = max(
                positions.items(),
                key=lambda item: (
                    item[1]["duration_ms"],
                    item[1]["views"],
                ),
            )

    assessment_score_percent = (alert.evidence or {}).get(
        "assessment_score_percent"
    )
    if assessment_score_percent is not None:
        assessment_score_percent = float(assessment_score_percent)
    if student_id and alert.assignment_id:
        attempts = list(
            (
                await session.scalars(
                    select(StudentAttempt).where(
                        StudentAttempt.organization_id == organization_id,
                        StudentAttempt.assignment_id == alert.assignment_id,
                        StudentAttempt.student_id == student_id,
                        StudentAttempt.started_at >= window_start,
                    )
                )
            ).all()
        )
        if attempts:
            assessment_score_percent = max(item.percentage for item in attempts)

    accessible_version_id: uuid.UUID | None = None
    if release_id:
        accessible_version_id = await session.scalar(
            select(AccessibleResourceVersion.id)
            .where(
                AccessibleResourceVersion.organization_id == organization_id,
                AccessibleResourceVersion.source_resource_id == release_id,
                AccessibleResourceVersion.status == "PUBLISHED",
            )
            .order_by(AccessibleResourceVersion.version.desc())
            .limit(1)
        )

    history: list[InterventionOutcomeRecord] = []
    if student_id:
        history = list(
            (
                await session.scalars(
                    select(InterventionOutcomeRecord)
                    .where(
                        InterventionOutcomeRecord.organization_id == organization_id,
                        InterventionOutcomeRecord.student_id == student_id,
                    )
                    .order_by(InterventionOutcomeRecord.occurred_at.desc())
                    .limit(20)
                )
            ).all()
        )

    learning_metrics: list[ComicReaderLearningMetric] = []
    if release_id:
        learning_metrics = list(
            (
                await session.scalars(
                    select(ComicReaderLearningMetric)
                    .where(
                        ComicReaderLearningMetric.organization_id == organization_id,
                        ComicReaderLearningMetric.release_id == release_id,
                        ComicReaderLearningMetric.privacy_suppressed.is_(False),
                    )
                    .order_by(ComicReaderLearningMetric.updated_at.desc())
                    .limit(5)
                )
            ).all()
        )

    return {
        "alert_id": str(alert.id),
        "alert_type": alert.alert_type,
        "rule_code": alert.rule_code,
        "severity": alert.severity.value,
        "student_id": str(student_id) if student_id else None,
        "classroom_id": str(alert.classroom_id) if alert.classroom_id else None,
        "assignment_id": str(alert.assignment_id) if alert.assignment_id else None,
        "release_id": str(release_id) if release_id else None,
        "evidence_window_start": window_start.isoformat(),
        "progress_percent": round(progress_percent, 2),
        "active_seconds": active_seconds,
        "session_count": session_count,
        "completed": completed,
        "bottleneck_page": page_number,
        "bottleneck_panel": panel_number,
        "glossary_opens": glossary_opens,
        "narration_seconds": narration_seconds,
        "accessibility_actions": accessibility_actions,
        "assessment_score_percent": assessment_score_percent,
        "accessible_resource_version_id": (
            str(accessible_version_id) if accessible_version_id else None
        ),
        "historical_interventions": [
            {
                "intervention_type": item.intervention_type,
                "mastery_gain": item.mastery_gain,
                "outcome": item.outcome,
                "occurred_at": item.occurred_at,
            }
            for item in history
        ],
        "learning_metrics": [
            {
                "assignment_id": str(item.assignment_id),
                "sample_size": item.sample_size,
                "average_score_percent": item.average_score_percent,
                "reading_score_correlation": item.reading_score_correlation,
                "interpretation": item.interpretation,
            }
            for item in learning_metrics
        ],
    }


async def create_ai_draft(
    session: AsyncSession,
    *,
    actor: ActorContext,
    alert: LearningAlert,
    snapshot: dict[str, Any],
) -> AIGenerationRequest | None:
    try:
        return await create_generation_request(
            session,
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            data=AIGenerationCreate(
                module_name="interventions",
                action_name="create_intervention",
                request_type="structured_text",
                target_type="learning_alert",
                target_id=alert.id,
                input_data={
                    "purpose": "intervention",
                    "evidence": snapshot,
                    "constraints": {
                        "human_approval_required": True,
                        "automatic_assignment": False,
                        "avoid_causal_claims": True,
                    },
                },
                parameters={"temperature": 0.2},
                queue_immediately=True,
            ),
        )
    except AIOrchestrationError:
        return None


async def active_intervention_for_alert(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    alert_id: uuid.UUID,
) -> LearningIntervention | None:
    return await session.scalar(
        select(LearningIntervention).where(
            LearningIntervention.organization_id == organization_id,
            LearningIntervention.alert_id == alert_id,
            LearningIntervention.status.in_(ACTIVE_INTERVENTION_STATUSES),
        )
    )


async def create_proposal(
    session: AsyncSession,
    *,
    actor: ActorContext,
    alert: LearningAlert,
    use_ai: bool,
    teacher_note: str,
    target_mastery: float,
) -> AdaptiveRecommendation:
    # Locking the alert serializes proposal creation for the same pedagogical
    # occurrence without requiring a new database constraint.
    alert = await session.scalar(
        select(LearningAlert)
        .where(
            LearningAlert.organization_id == actor.organization_id,
            LearningAlert.id == alert.id,
        )
        .with_for_update()
    )
    if alert is None:
        raise HTTPException(404, "Alerta pedagógico não encontrado.")

    pending = await session.scalar(
        select(AdaptiveRecommendation).where(
            AdaptiveRecommendation.organization_id == actor.organization_id,
            AdaptiveRecommendation.source_alert_id == alert.id,
            AdaptiveRecommendation.status == "pending_review",
        )
    )
    if pending:
        raise HTTPException(
            409,
            {
                "code": "INTERVENTION_PROPOSAL_ALREADY_EXISTS",
                "recommendation_id": str(pending.id),
            },
        )
    active = await active_intervention_for_alert(
        session,
        organization_id=actor.organization_id,
        alert_id=alert.id,
    )
    if active:
        raise HTTPException(
            409,
            {
                "code": "INTERVENTION_ALREADY_ACTIVE",
                "intervention_id": str(active.id),
            },
        )

    snapshot = await evidence_snapshot(
        session,
        organization_id=actor.organization_id,
        alert=alert,
    )
    if not snapshot["release_id"]:
        raise HTTPException(
            409,
            "O alerta não está vinculado a uma HQ publicada ou atividade incorporada.",
        )

    alert_evidence = alert.evidence or {}
    recommendation_type = choose_recommendation_type(
        alert_type=alert.alert_type,
        rule_code=alert.rule_code,
        progress_percent=float(snapshot["progress_percent"]),
        score_percent=snapshot["assessment_score_percent"],
        accessibility_used=int(snapshot["accessibility_actions"]) > 0,
        observed_accuracy=(
            float(alert_evidence["accuracy"])
            if alert_evidence.get("accuracy") is not None
            else None
        ),
    )
    evidence_count = 1
    evidence_count += int(snapshot["session_count"] > 0)
    evidence_count += int(snapshot["assessment_score_percent"] is not None)
    evidence_count += int(bool(snapshot["historical_interventions"]))
    confidence = confidence_from_evidence(
        evidence_count,
        snapshot["assessment_score_percent"] is not None,
    )
    plan = build_plan(
        release_id=snapshot["release_id"],
        page_number=snapshot["bottleneck_page"],
        panel_number=snapshot["bottleneck_panel"],
        assignment_id=snapshot["assignment_id"],
        accessible_version_id=snapshot["accessible_resource_version_id"],
        teacher_note=teacher_note,
        recommendation_type=recommendation_type,
        activity_id=(
            str(alert_evidence["activity_id"])
            if alert_evidence.get("activity_id")
            else None
        ),
        question_version_id=(
            str(alert_evidence["question_version_id"])
            if alert_evidence.get("question_version_id")
            else None
        ),
    )
    model = await orchestration_model(session, actor=actor)
    ai_request = (
        await create_ai_draft(
            session,
            actor=actor,
            alert=alert,
            snapshot=snapshot,
        )
        if use_ai
        else None
    )

    item = AdaptiveRecommendation(
        organization_id=actor.organization_id,
        student_id=alert.student_id,
        classroom_id=alert.classroom_id,
        group_id=None,
        skill_state_id=None,
        model_version_id=model.id,
        source_alert_id=alert.id,
        source_comic_release_id=_uuid(snapshot["release_id"]),
        source_ai_request_id=ai_request.id if ai_request else None,
        source_kind=(
            "hq_learning_analytics"
            if alert_evidence.get("source") == "hq_learning_analytics"
            else "comic_reader_alert"
        ),
        recommendation_type=recommendation_type,
        status="pending_review",
        priority=intervention_priority(alert.severity.value, confidence),
        title=f"Intervenção: {alert.title}",
        rationale=(
            f"{alert.description} Evidências atuais: progresso de "
            f"{snapshot['progress_percent']:.1f}%, "
            f"{snapshot['session_count']} sessão(ões) e "
            f"{snapshot['active_seconds']} segundo(s) ativos. "
            "A proposta exige revisão docente antes da aplicação."
        ),
        target_dimension_type=str(
            alert_evidence.get("skill_type")
            or ("activity" if alert_evidence.get("activity_id") else "comic_learning")
        ),
        target_dimension_code=str(
            alert_evidence.get("skill_code")
            or alert_evidence.get("activity_id")
            or alert.rule_code
        ),
        target_mastery=target_mastery,
        confidence_score=confidence,
        evidence_summary={
            **snapshot,
            "ai_request_status": "queued" if ai_request else "not_requested",
        },
        proposed_materials=plan,
        # A queued request is not an AI-authored proposal yet.
        created_by_ai=False,
        created_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.flush()

    evidence_rows = [
        (
            "learning_alert",
            alert.id,
            None,
            alert.description,
            {"rule_code": alert.rule_code, "evidence": alert.evidence},
        ),
        (
            "comic_reader_analytics",
            item.source_comic_release_id,
            float(snapshot["progress_percent"]) / 100,
            "Progresso, tempo ativo e ponto de maior permanência na HQ.",
            snapshot,
        ),
    ]
    source_snapshot_id = _uuid(alert_evidence.get("source_snapshot_id"))
    if source_snapshot_id:
        evidence_rows.append(
            (
                "hq_learning_analytics_snapshot",
                source_snapshot_id,
                (
                    float(alert_evidence["accuracy"]) / 100
                    if alert_evidence.get("accuracy") is not None
                    else None
                ),
                "Snapshot canônico da experiência e avaliação pós-HQ.",
                {
                    "snapshot_id": str(source_snapshot_id),
                    "publication_id": alert_evidence.get("publication_id"),
                    "scope_type": alert_evidence.get("scope_type"),
                    "scope_id": alert_evidence.get("scope_id"),
                    "signal_key": alert_evidence.get("signal_key"),
                },
            )
        )
    if alert.assignment_id:
        evidence_rows.append(
            (
                "assessment",
                alert.assignment_id,
                (
                    float(snapshot["assessment_score_percent"]) / 100
                    if snapshot["assessment_score_percent"] is not None
                    else None
                ),
                "Melhor resultado observado na atividade vinculada.",
                {"score_percent": snapshot["assessment_score_percent"]},
            )
        )
    for source_type, source_id, observed, summary, data in evidence_rows:
        if source_id is None:
            continue
        session.add(
            AdaptiveRecommendationEvidence(
                organization_id=actor.organization_id,
                recommendation_id=item.id,
                source_type=source_type,
                source_id=source_id,
                dimension_type="comic_learning",
                dimension_code=alert.rule_code,
                observed_score=observed,
                evidence_weight=1.0,
                summary=summary,
                evidence_snapshot=data,
            )
        )
    return item


def intervention_type(value: str) -> InterventionType:
    try:
        return InterventionType(value)
    except ValueError:
        return canonical_intervention_type(value)


async def add_event(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    intervention: LearningIntervention,
    event_type: str,
    from_status: str = "",
    to_status: str = "",
    data: dict[str, Any] | None = None,
) -> LearningInterventionEvent:
    event = LearningInterventionEvent(
        organization_id=intervention.organization_id,
        intervention_id=intervention.id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        event_data=data or {},
    )
    session.add(event)
    await session.flush()
    return event


async def validate_recommendation_references(
    session: AsyncSession,
    *,
    actor: ActorContext,
    recommendation: AdaptiveRecommendation,
    alert: LearningAlert | None,
) -> uuid.UUID | None:
    if recommendation.student_id:
        member = await session.scalar(
            select(Membership.id).where(
                Membership.organization_id == actor.organization_id,
                Membership.user_id == recommendation.student_id,
                Membership.is_active.is_(True),
            )
        )
        if member is None:
            raise HTTPException(409, "O estudante não pertence à organização ativa.")

    if recommendation.classroom_id:
        classroom = await session.scalar(
            select(Classroom.id).where(
                Classroom.organization_id == actor.organization_id,
                Classroom.id == recommendation.classroom_id,
                Classroom.is_active.is_(True),
            )
        )
        if classroom is None:
            raise HTTPException(409, "A turma não pertence à organização ativa.")
        if recommendation.student_id:
            enrollment = await session.scalar(
                select(ClassroomEnrollment.id).where(
                    ClassroomEnrollment.classroom_id == recommendation.classroom_id,
                    ClassroomEnrollment.user_id == recommendation.student_id,
                    ClassroomEnrollment.role == "student",
                )
            )
            if enrollment is None:
                raise HTTPException(409, "O estudante não está matriculado na turma.")

    if recommendation.source_comic_release_id:
        release = await session.scalar(
            select(ComicEditorialRelease.id).where(
                ComicEditorialRelease.organization_id == actor.organization_id,
                ComicEditorialRelease.id == recommendation.source_comic_release_id,
                ComicEditorialRelease.status == "PUBLISHED",
            )
        )
        if release is None:
            raise HTTPException(409, "O release da HQ não está disponível.")

    if alert and alert.assignment_id:
        assignment = await session.scalar(
            select(MaterialAssignment.id).where(
                MaterialAssignment.organization_id == actor.organization_id,
                MaterialAssignment.id == alert.assignment_id,
            )
        )
        if assignment is None:
            raise HTTPException(409, "A atividade não pertence à organização ativa.")

    accessible_ids = {
        value
        for item in recommendation.proposed_materials
        if (value := _uuid(item.get("accessible_resource_version_id")))
    }
    if len(accessible_ids) > 1:
        raise HTTPException(422, "A proposta contém versões acessíveis conflitantes.")
    accessible_id = next(iter(accessible_ids), None)
    if accessible_id:
        accessible = await session.scalar(
            select(AccessibleResourceVersion.id).where(
                AccessibleResourceVersion.organization_id == actor.organization_id,
                AccessibleResourceVersion.id == accessible_id,
                AccessibleResourceVersion.status == "PUBLISHED",
                AccessibleResourceVersion.source_resource_id
                == recommendation.source_comic_release_id,
            )
        )
        if accessible is None:
            raise HTTPException(409, "A versão acessível não é válida para esta HQ.")

    for action in recommendation.proposed_materials:
        action_release = _uuid(action.get("release_id"))
        action_assignment = _uuid(action.get("assignment_id"))
        if (
            action_release
            and action_release != recommendation.source_comic_release_id
        ):
            raise HTTPException(422, "A proposta referencia outro release de HQ.")
        if action_assignment and (
            alert is None or action_assignment != alert.assignment_id
        ):
            raise HTTPException(422, "A proposta referencia outra atividade.")
    return accessible_id


async def approve_proposal(
    session: AsyncSession,
    *,
    actor: ActorContext,
    recommendation: AdaptiveRecommendation,
    due_days: int,
    evaluation_days: int,
    create_adaptive_path: bool,
) -> LearningIntervention:
    model = await session.get(AdaptiveModelVersion, recommendation.model_version_id)
    if model is None:
        raise HTTPException(409, "Modelo adaptativo da recomendação não encontrado.")

    alert = (
        await session.get(LearningAlert, recommendation.source_alert_id)
        if recommendation.source_alert_id
        else None
    )
    existing = await session.scalar(
        select(LearningIntervention).where(
            LearningIntervention.organization_id == actor.organization_id,
            LearningIntervention.source_recommendation_id == recommendation.id,
        )
    )
    if existing:
        raise HTTPException(
            409,
            {
                "code": "PROPOSAL_ALREADY_CONVERTED",
                "intervention_id": str(existing.id),
            },
        )
    if alert:
        active = await active_intervention_for_alert(
            session,
            organization_id=actor.organization_id,
            alert_id=alert.id,
        )
        if active:
            raise HTTPException(
                409,
                {
                    "code": "INTERVENTION_ALREADY_ACTIVE",
                    "intervention_id": str(active.id),
                },
            )

    accessible_id = await validate_recommendation_references(
        session,
        actor=actor,
        recommendation=recommendation,
        alert=alert,
    )
    due_at, evaluation_due_at = due_dates(due_days, evaluation_days)
    item = LearningIntervention(
        organization_id=actor.organization_id,
        teacher_id=actor.user_id,
        classroom_id=recommendation.classroom_id,
        student_id=recommendation.student_id,
        alert_id=recommendation.source_alert_id,
        assignment_id=alert.assignment_id if alert else None,
        source_recommendation_id=recommendation.id,
        comic_release_id=recommendation.source_comic_release_id,
        accessible_resource_version_id=accessible_id,
        ai_request_id=recommendation.source_ai_request_id,
        approved_by_user_id=actor.user_id,
        intervention_type=intervention_type(recommendation.recommendation_type),
        status=InterventionStatus.PLANNED,
        reason=recommendation.rationale,
        notes=recommendation.review_notes,
        expected_outcome=(
            f"Alcançar domínio mínimo de {recommendation.target_mastery:.0%} "
            f"em {recommendation.target_dimension_code}."
        ),
        result_summary="",
        plan_snapshot={"actions": recommendation.proposed_materials},
        baseline_snapshot=recommendation.evidence_summary,
        target_snapshot={
            "target_mastery": recommendation.target_mastery,
            "target_dimension_type": recommendation.target_dimension_type,
            "target_dimension_code": recommendation.target_dimension_code,
        },
        human_review_required=True,
        approved_at=datetime.now(UTC),
        due_at=due_at,
        evaluation_due_at=evaluation_due_at,
    )
    session.add(item)
    await session.flush()

    if create_adaptive_path and recommendation.student_id:
        path = await approve_recommendation_as_path(
            session,
            organization_id=actor.organization_id,
            recommendation=recommendation,
            teacher_id=actor.user_id,
            model=model,
        )
        item.adaptive_path_id = path.id
    else:
        recommendation.status = "approved"
        recommendation.reviewed_by_user_id = actor.user_id
        recommendation.reviewed_at = datetime.now(UTC)

    if alert and alert.status == AlertStatus.OPEN:
        alert.status = AlertStatus.ACKNOWLEDGED

    await add_event(
        session,
        actor_user_id=actor.user_id,
        intervention=item,
        event_type="intervention.approved",
        from_status="proposal",
        to_status=InterventionStatus.PLANNED.value,
        data={
            "recommendation_id": str(recommendation.id),
            "adaptive_path_id": (
                str(item.adaptive_path_id) if item.adaptive_path_id else None
            ),
        },
    )
    return item


async def current_outcome_snapshot(
    session: AsyncSession,
    intervention: LearningIntervention,
) -> dict[str, Any]:
    alert = (
        await session.get(LearningAlert, intervention.alert_id)
        if intervention.alert_id
        else None
    )
    if alert:
        return await evidence_snapshot(
            session,
            organization_id=intervention.organization_id,
            alert=alert,
        )
    return {
        "progress_percent": None,
        "assessment_score_percent": None,
        "release_id": (
            str(intervention.comic_release_id)
            if intervention.comic_release_id
            else None
        ),
    }


async def complete_intervention(
    session: AsyncSession,
    *,
    actor: ActorContext,
    intervention: LearningIntervention,
    result_summary: str,
    teacher_notes: str,
    observed_progress_percent: float | None,
    observed_score_percent: float | None,
) -> InterventionOutcomeRecord | None:
    snapshot = await current_outcome_snapshot(session, intervention)
    if observed_progress_percent is not None:
        snapshot["progress_percent"] = observed_progress_percent
    if observed_score_percent is not None:
        snapshot["assessment_score_percent"] = observed_score_percent

    comparison = comparable_outcome(
        intervention.baseline_snapshot,
        snapshot,
        target_mastery=float(
            intervention.target_snapshot.get("target_mastery", 0.75)
        ),
        minimum_improvement=get_settings().intervention_minimum_improvement,
    )
    learning_node_id = (
        intervention.comic_release_id
        or intervention.assignment_id
        or intervention.id
    )
    record: InterventionOutcomeRecord | None = None
    if intervention.student_id is not None:
        record = InterventionOutcomeRecord(
            organization_id=intervention.organization_id,
            student_id=intervention.student_id,
            learning_node_id=learning_node_id,
            intervention_type=intervention.intervention_type.value,
            material_id=intervention.assignment_id,
            learning_intervention_id=intervention.id,
            comic_release_id=intervention.comic_release_id,
            mastery_before=comparison["before"],
            mastery_after=comparison["after"],
            mastery_gain=comparison["gain"],
            completion_rate=1.0,
            hints_average=0.0,
            attempts_average=1.0,
            outcome=comparison["outcome"],
            occurred_at=datetime.now(UTC),
            source_snapshot={
                "baseline": intervention.baseline_snapshot,
                "observed": snapshot,
                "comparison": comparison,
                "teacher_notes": teacher_notes,
            },
            created_by_user_id=actor.user_id,
        )
        session.add(record)
        await session.flush()

    previous = intervention.status.value
    intervention.status = InterventionStatus.COMPLETED
    intervention.completed_at = datetime.now(UTC)
    intervention.result_summary = result_summary
    intervention.notes = (
        f"{intervention.notes}\n{teacher_notes}".strip()
        if teacher_notes
        else intervention.notes
    )
    intervention.target_snapshot = {
        **intervention.target_snapshot,
        "observed": snapshot,
        **comparison,
    }

    if intervention.adaptive_path_id:
        path = await session.scalar(
            select(AdaptiveLearningPath).where(
                AdaptiveLearningPath.organization_id == intervention.organization_id,
                AdaptiveLearningPath.id == intervention.adaptive_path_id,
            )
        )
        if path:
            await calculate_path_outcome(
                session,
                organization_id=intervention.organization_id,
                path=path,
                student_id=intervention.student_id,
            )

    recommendation = (
        await session.get(
            AdaptiveRecommendation,
            intervention.source_recommendation_id,
        )
        if intervention.source_recommendation_id
        else None
    )
    alert = (
        await session.get(LearningAlert, intervention.alert_id)
        if intervention.alert_id
        else None
    )
    resolved = bool(comparison["target_met"] or comparison["improved"])
    if alert:
        if resolved:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(UTC)
        else:
            alert.status = AlertStatus.OPEN
            alert.resolved_at = None
    if recommendation:
        recommendation.status = "completed" if resolved else "needs_revision"

    await add_event(
        session,
        actor_user_id=actor.user_id,
        intervention=intervention,
        event_type="intervention.completed",
        from_status=previous,
        to_status=InterventionStatus.COMPLETED.value,
        data={
            "outcome_record_id": str(record.id) if record else None,
            "metric": comparison["metric"],
            "mastery_gain": comparison["gain"],
            "outcome": comparison["outcome"],
            "target_met": comparison["target_met"],
            "alert_resolved": resolved,
            "scope": "student" if intervention.student_id else "classroom",
        },
    )
    from app.intervention_effectiveness.services import (
        register_intervention_completion,
    )

    await register_intervention_completion(
        session,
        intervention=intervention,
        outcome_id=record.id if record else None,
    )
    return record


async def user_can_access_intervention(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    intervention: LearningIntervention,
) -> bool:
    if intervention.student_id == user_id:
        return True
    if intervention.student_id is not None or intervention.classroom_id is None:
        return False
    enrollment = await session.scalar(
        select(ClassroomEnrollment.id).where(
            ClassroomEnrollment.classroom_id == intervention.classroom_id,
            ClassroomEnrollment.user_id == user_id,
            ClassroomEnrollment.role == "student",
        )
    )
    return enrollment is not None
