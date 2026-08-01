from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import pstdev
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptive import (
    AdaptiveAuditEvent,
    AdaptiveGroupMember,
    AdaptiveLearningPath,
    AdaptiveLearningProfile,
    AdaptiveModelVersion,
    AdaptivePathOutcome,
    AdaptivePathStep,
    AdaptiveRecommendation,
    AdaptiveRecommendationEvidence,
    AdaptiveReviewSchedule,
    AdaptiveSkillState,
    AdaptiveStudentGroup,
    SkillPrerequisite,
)
from app.models.assessment import AssessmentOutcomeEvidence
from app.models.auth import Membership, User
from app.models.education import ClassroomEnrollment
from app.schemas.adaptive import LearningPathCreate, StudentGroupCreate

DEFAULT_THRESHOLDS = {"initial": 0.40, "developing": 0.65, "adequate": 0.85}
DEFAULT_REVIEW_INTERVALS = (1, 7, 30)


@dataclass(slots=True, frozen=True)
class EvidencePoint:
    source_id: UUID | None
    score_obtained: float
    score_possible: float
    evidence_weight: float = 1.0
    calculated_at: datetime | None = None
    difficulty: str = "medium"
    source_type: str = "assessment"

    @property
    def normalized_score(self) -> float:
        if self.score_possible <= 0:
            return 0.0
        return max(0.0, min(1.0, self.score_obtained / self.score_possible))


@dataclass(slots=True, frozen=True)
class MasteryResult:
    mastery_score: float
    mastery_level: str
    confidence_score: float
    confidence_level: str
    evidence_count: int
    weighted_score: float
    weighted_possible: float
    trend: str
    explanation: str


def _difficulty_multiplier(difficulty: str) -> float:
    return {
        "very_easy": 0.75,
        "easy": 0.85,
        "medium": 1.0,
        "hard": 1.15,
        "very_hard": 1.25,
    }.get(difficulty.lower(), 1.0)


def _recency_multiplier(at: datetime | None, now: datetime) -> float:
    if at is None:
        return 0.85
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    age_days = max(0.0, (now - at).total_seconds() / 86400)
    return max(0.65, 1.0 - min(age_days, 365.0) / 365.0 * 0.35)


def _mastery_level(score: float, evidence_count: int, minimum: int, thresholds: dict[str, float]) -> str:
    if evidence_count == 0:
        return "not_assessed"
    if evidence_count < minimum:
        return "insufficient_evidence"
    if score < thresholds["initial"]:
        return "initial"
    if score < thresholds["developing"]:
        return "developing"
    if score < thresholds["adequate"]:
        return "adequate"
    return "advanced"


def _confidence_level(score: float) -> str:
    if score < 0.35:
        return "insufficient"
    if score < 0.60:
        return "low"
    if score < 0.80:
        return "moderate"
    return "high"


def calculate_mastery(
    evidence: Iterable[EvidencePoint],
    *,
    minimum_evidence_count: int = 3,
    thresholds: dict[str, float] | None = None,
    now: datetime | None = None,
) -> MasteryResult:
    points = list(evidence)
    current_time = now or datetime.now(UTC)
    active_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if not points:
        return MasteryResult(
            mastery_score=0.0,
            mastery_level="not_assessed",
            confidence_score=0.0,
            confidence_level="insufficient",
            evidence_count=0,
            weighted_score=0.0,
            weighted_possible=0.0,
            trend="stable",
            explanation="Nenhuma evidência válida foi encontrada para esta dimensão.",
        )

    weighted_total = 0.0
    total_weight = 0.0
    normalized_scores: list[float] = []
    ordered = sorted(points, key=lambda item: item.calculated_at or datetime.min.replace(tzinfo=UTC))
    for point in ordered:
        score = point.normalized_score
        weight = (
            max(point.evidence_weight, 0.05)
            * _difficulty_multiplier(point.difficulty)
            * _recency_multiplier(point.calculated_at, current_time)
        )
        weighted_total += score * weight
        total_weight += weight
        normalized_scores.append(score)

    mastery = weighted_total / total_weight if total_weight else 0.0
    consistency = 1.0 if len(normalized_scores) == 1 else max(0.0, 1.0 - pstdev(normalized_scores))
    evidence_factor = min(1.0, len(points) / max(minimum_evidence_count * 2, 1))
    confidence = min(1.0, evidence_factor * 0.70 + consistency * 0.30)

    trend = "stable"
    if len(ordered) >= 4:
        midpoint = len(ordered) // 2
        early = sum(item.normalized_score for item in ordered[:midpoint]) / midpoint
        recent_items = ordered[midpoint:]
        recent = sum(item.normalized_score for item in recent_items) / len(recent_items)
        delta = recent - early
        if delta >= 0.10:
            trend = "improving"
        elif delta <= -0.10:
            trend = "declining"

    level = _mastery_level(mastery, len(points), minimum_evidence_count, active_thresholds)
    explanation = (
        f"Domínio calculado com {len(points)} evidências válidas, ponderadas por peso, "
        f"dificuldade e recência. Confiança {_confidence_level(confidence)}; tendência {trend}."
    )
    return MasteryResult(
        mastery_score=round(mastery, 4),
        mastery_level=level,
        confidence_score=round(confidence, 4),
        confidence_level=_confidence_level(confidence),
        evidence_count=len(points),
        weighted_score=round(weighted_total, 4),
        weighted_possible=round(total_weight, 4),
        trend=trend,
        explanation=explanation,
    )


def recommendation_type_for(state: MasteryResult) -> str:
    if state.evidence_count == 0 or state.mastery_level == "insufficient_evidence":
        return "diagnostic"
    if state.mastery_score < 0.40:
        return "recovery"
    if state.mastery_score < 0.65:
        return "reinforcement"
    if state.mastery_score < 0.85:
        return "consolidation"
    return "advanced_challenge"


def recommendation_priority(state: MasteryResult) -> str:
    if state.trend == "declining" and state.mastery_score < 0.65:
        return "high"
    if state.mastery_score < 0.40 and state.confidence_score >= 0.60:
        return "high"
    if state.mastery_level == "insufficient_evidence":
        return "attention"
    return "normal"


def default_materials_for(recommendation_type: str, dimension_code: str) -> list[dict[str, Any]]:
    common = {"dimension_code": dimension_code, "requires_teacher_review": True}
    if recommendation_type == "diagnostic":
        return [
            {**common, "type": "diagnostic_quiz", "title": "Diagnóstico curto", "estimated_minutes": 10},
        ]
    if recommendation_type in {"recovery", "prerequisite_recovery"}:
        return [
            {**common, "type": "comic", "title": "HQ explicativa de recuperação", "estimated_minutes": 12},
            {**common, "type": "guided_activity", "title": "Atividade guiada", "estimated_minutes": 15},
            {**common, "type": "quiz", "title": "Verificação de aprendizagem", "estimated_minutes": 10},
        ]
    if recommendation_type == "reinforcement":
        return [
            {**common, "type": "worked_example", "title": "Exemplo resolvido", "estimated_minutes": 8},
            {**common, "type": "practice", "title": "Prática de reforço", "estimated_minutes": 15},
            {**common, "type": "quiz", "title": "Quiz de consolidação", "estimated_minutes": 8},
        ]
    if recommendation_type == "consolidation":
        return [
            {**common, "type": "practice", "title": "Atividade de consolidação", "estimated_minutes": 15},
            {**common, "type": "application", "title": "Aplicação em novo contexto", "estimated_minutes": 15},
        ]
    return [
        {**common, "type": "challenge", "title": "Desafio avançado", "estimated_minutes": 20},
        {**common, "type": "project", "title": "Projeto de aprofundamento", "estimated_minutes": 30},
    ]


def recommendation_rationale(state: AdaptiveSkillState) -> str:
    if state.evidence_count < 3:
        return (
            f"Há somente {state.evidence_count} evidência(s) para {state.dimension_code}. "
            "Recomenda-se uma atividade diagnóstica antes de tomar decisões de progressão."
        )
    percent = state.mastery_score * 100
    trend_label = {
        "improving": "em evolução",
        "declining": "em queda",
        "stable": "estável",
    }.get(state.trend, state.trend)
    return (
        f"O domínio estimado em {state.dimension_code} é {percent:.1f}%, com "
        f"confiança {state.confidence_level}, {state.evidence_count} evidências e tendência {trend_label}. "
        "A recomendação utiliza apenas evidências rastreáveis de exercícios e avaliações realizados."
    )


def build_review_dates(
    *,
    mastery_score: float,
    start: datetime | None = None,
    intervals: tuple[int, ...] = DEFAULT_REVIEW_INTERVALS,
) -> list[datetime]:
    base = start or datetime.now(UTC)
    multiplier = 0.75 if mastery_score < 0.50 else 1.0 if mastery_score < 0.80 else 1.5
    return [base + timedelta(days=max(1, round(days * multiplier))) for days in intervals]


def evaluate_advancement(
    *,
    mastery_score: float,
    evidence_count: int,
    target_mastery: float,
    minimum_evidence_count: int,
    required_steps_complete: bool,
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if mastery_score < target_mastery:
        blockers.append(f"domínio {mastery_score:.0%} abaixo da meta {target_mastery:.0%}")
    if evidence_count < minimum_evidence_count:
        blockers.append(
            f"somente {evidence_count} evidências; mínimo necessário {minimum_evidence_count}"
        )
    if not required_steps_complete:
        blockers.append("existem etapas obrigatórias pendentes")
    return not blockers, blockers


async def ensure_default_model(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> AdaptiveModelVersion:
    model = await session.scalar(
        select(AdaptiveModelVersion).where(
            AdaptiveModelVersion.organization_id == organization_id,
            AdaptiveModelVersion.is_default.is_(True),
            AdaptiveModelVersion.status == "active",
        ).order_by(AdaptiveModelVersion.version.desc())
    )
    if model is not None:
        return model
    model = AdaptiveModelVersion(
        organization_id=organization_id,
        code="mastery-v1",
        name="Modelo determinístico de domínio",
        version=1,
        status="active",
        description="Modelo explicável baseado em evidências, recência, dificuldade e consistência.",
        rules_json={
            "recency_floor": 0.65,
            "difficulty_weights": {"easy": 0.85, "medium": 1.0, "hard": 1.15},
            "confidence": "70% quantidade de evidências + 30% consistência",
        },
        thresholds_json=DEFAULT_THRESHOLDS,
        minimum_evidence_count=3,
        is_default=True,
        created_by_user_id=user_id,
        approved_by_user_id=user_id,
        approved_at=datetime.now(UTC),
    )
    session.add(model)
    await session.flush()
    return model


async def ensure_profile(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
) -> AdaptiveLearningProfile:
    profile = await session.scalar(
        select(AdaptiveLearningProfile).where(
            AdaptiveLearningProfile.organization_id == organization_id,
            AdaptiveLearningProfile.student_id == student_id,
        )
    )
    if profile is None:
        profile = AdaptiveLearningProfile(
            organization_id=organization_id,
            student_id=student_id,
        )
        session.add(profile)
        await session.flush()
    return profile


async def validate_student_membership(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
) -> bool:
    return (
        await session.scalar(
            select(func.count(Membership.id)).where(
                Membership.organization_id == organization_id,
                Membership.user_id == student_id,
                Membership.is_active.is_(True),
            )
        )
        or 0
    ) > 0


async def classroom_student_ids(
    session: AsyncSession,
    *,
    organization_id: UUID,
    classroom_id: UUID,
) -> list[UUID]:
    statement = (
        select(ClassroomEnrollment.user_id)
        .join(User, User.id == ClassroomEnrollment.user_id)
        .join(Membership, Membership.user_id == User.id)
        .where(
            ClassroomEnrollment.classroom_id == classroom_id,
            ClassroomEnrollment.role == "student",
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )
        .distinct()
    )
    return list((await session.scalars(statement)).all())


def _point_from_model(item: AssessmentOutcomeEvidence) -> EvidencePoint:
    snapshot = item.source_snapshot or {}
    return EvidencePoint(
        source_id=item.id,
        score_obtained=item.score_obtained,
        score_possible=item.score_possible,
        evidence_weight=item.evidence_weight,
        calculated_at=item.calculated_at,
        difficulty=str(snapshot.get("difficulty", "medium")),
        source_type="assessment_outcome",
    )


async def refresh_student_states(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
    model: AdaptiveModelVersion,
) -> tuple[list[AdaptiveSkillState], int]:
    profile = await ensure_profile(session, organization_id=organization_id, student_id=student_id)
    evidence_rows = list(
        (
            await session.scalars(
                select(AssessmentOutcomeEvidence)
                .where(
                    AssessmentOutcomeEvidence.organization_id == organization_id,
                    AssessmentOutcomeEvidence.student_id == student_id,
                    AssessmentOutcomeEvidence.score_possible > 0,
                )
                .order_by(AssessmentOutcomeEvidence.calculated_at.asc())
            )
        ).all()
    )
    grouped: dict[tuple[str, str], list[AssessmentOutcomeEvidence]] = defaultdict(list)
    for row in evidence_rows:
        grouped[(row.dimension_type, row.dimension_code)].append(row)

    updated: list[AdaptiveSkillState] = []
    for (dimension_type, dimension_code), rows in grouped.items():
        result = calculate_mastery(
            (_point_from_model(item) for item in rows),
            minimum_evidence_count=model.minimum_evidence_count,
            thresholds={key: float(value) for key, value in model.thresholds_json.items()},
        )
        state = await session.scalar(
            select(AdaptiveSkillState).where(
                AdaptiveSkillState.organization_id == organization_id,
                AdaptiveSkillState.student_id == student_id,
                AdaptiveSkillState.dimension_type == dimension_type,
                AdaptiveSkillState.dimension_code == dimension_code,
            )
        )
        snapshot = [
            {
                "evidence_id": str(item.id),
                "assignment_id": str(item.assignment_id),
                "attempt_id": str(item.attempt_id),
                "question_id": str(item.question_id),
                "score": item.score_obtained,
                "possible": item.score_possible,
                "weight": item.evidence_weight,
                "calculated_at": item.calculated_at.isoformat(),
            }
            for item in rows[-30:]
        ]
        values = {
            "profile_id": profile.id,
            "model_version_id": model.id,
            "mastery_score": result.mastery_score,
            "mastery_level": result.mastery_level,
            "confidence_score": result.confidence_score,
            "confidence_level": result.confidence_level,
            "evidence_count": result.evidence_count,
            "weighted_score": result.weighted_score,
            "weighted_possible": result.weighted_possible,
            "trend": result.trend,
            "evidence_snapshot": snapshot,
            "calculation_explanation": result.explanation,
            "first_evidence_at": rows[0].calculated_at,
            "last_evidence_at": rows[-1].calculated_at,
            "calculated_at": datetime.now(UTC),
        }
        if state is None:
            state = AdaptiveSkillState(
                organization_id=organization_id,
                profile_id=profile.id,
                student_id=student_id,
                model_version_id=model.id,
                dimension_type=dimension_type,
                dimension_code=dimension_code,
                **values,
            )
            session.add(state)
        else:
            for field, value in values.items():
                setattr(state, field, value)
        updated.append(state)

    profile.last_calculated_at = datetime.now(UTC)
    await session.flush()
    return updated, len(evidence_rows)


async def create_recommendations_for_states(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
    model: AdaptiveModelVersion,
    states: list[AdaptiveSkillState],
    created_by_user_id: UUID,
    maximum: int = 5,
    only_dimension: tuple[str, str] | None = None,
) -> list[AdaptiveRecommendation]:
    candidates = sorted(states, key=lambda item: (item.mastery_score, -item.evidence_count))
    created: list[AdaptiveRecommendation] = []
    for state in candidates:
        if only_dimension and (state.dimension_type, state.dimension_code) != only_dimension:
            continue
        if state.mastery_score >= 0.85 and state.confidence_score < 0.6:
            continue
        existing = await session.scalar(
            select(AdaptiveRecommendation).where(
                AdaptiveRecommendation.organization_id == organization_id,
                AdaptiveRecommendation.student_id == student_id,
                AdaptiveRecommendation.target_dimension_type == state.dimension_type,
                AdaptiveRecommendation.target_dimension_code == state.dimension_code,
                AdaptiveRecommendation.status.in_(["pending_review", "approved"]),
            )
        )
        if existing is not None:
            continue
        prerequisites = list(
            (
                await session.scalars(
                    select(SkillPrerequisite).where(
                        SkillPrerequisite.organization_id == organization_id,
                        SkillPrerequisite.dimension_type == state.dimension_type,
                        SkillPrerequisite.dimension_code == state.dimension_code,
                    )
                )
            ).all()
        )
        prerequisite_gaps: list[dict[str, Any]] = []
        for prerequisite in prerequisites:
            prerequisite_state = await session.scalar(
                select(AdaptiveSkillState).where(
                    AdaptiveSkillState.organization_id == organization_id,
                    AdaptiveSkillState.student_id == student_id,
                    AdaptiveSkillState.dimension_type == prerequisite.prerequisite_type,
                    AdaptiveSkillState.dimension_code == prerequisite.prerequisite_code,
                )
            )
            observed = prerequisite_state.mastery_score if prerequisite_state is not None else 0.0
            if observed < prerequisite.minimum_mastery:
                prerequisite_gaps.append(
                    {
                        "dimension_type": prerequisite.prerequisite_type,
                        "dimension_code": prerequisite.prerequisite_code,
                        "observed_mastery": observed,
                        "required_mastery": prerequisite.minimum_mastery,
                        "rationale": prerequisite.rationale,
                    }
                )
        rec_type = recommendation_type_for(
            MasteryResult(
                mastery_score=state.mastery_score,
                mastery_level=state.mastery_level,
                confidence_score=state.confidence_score,
                confidence_level=state.confidence_level,
                evidence_count=state.evidence_count,
                weighted_score=state.weighted_score,
                weighted_possible=state.weighted_possible,
                trend=state.trend,
                explanation=state.calculation_explanation,
            )
        )
        target_type = state.dimension_type
        target_code = state.dimension_code
        rationale = recommendation_rationale(state)
        if prerequisite_gaps:
            first_gap = prerequisite_gaps[0]
            target_type = str(first_gap["dimension_type"])
            target_code = str(first_gap["dimension_code"])
            rec_type = "prerequisite_recovery"
            rationale = (
                f"Antes de avançar em {state.dimension_code}, o pré-requisito {target_code} "
                f"apresenta domínio de {float(first_gap['observed_mastery']):.1%}, abaixo da meta "
                f"de {float(first_gap['required_mastery']):.1%}. " + rationale
            )
        target = 0.65 if rec_type in {"diagnostic", "recovery", "prerequisite_recovery"} else 0.75 if rec_type != "advanced_challenge" else 0.90
        recommendation = AdaptiveRecommendation(
            organization_id=organization_id,
            student_id=student_id,
            skill_state_id=state.id,
            model_version_id=model.id,
            recommendation_type=rec_type,
            status="pending_review",
            priority=recommendation_priority(
                MasteryResult(
                    state.mastery_score, state.mastery_level, state.confidence_score,
                    state.confidence_level, state.evidence_count, state.weighted_score,
                    state.weighted_possible, state.trend, state.calculation_explanation,
                )
            ),
            title=f"{rec_type.replace('_', ' ').title()} — {target_code}",
            rationale=rationale,
            target_dimension_type=target_type,
            target_dimension_code=target_code,
            target_mastery=target,
            confidence_score=state.confidence_score,
            evidence_summary={
                "mastery_score": state.mastery_score,
                "mastery_level": state.mastery_level,
                "confidence_level": state.confidence_level,
                "evidence_count": state.evidence_count,
                "trend": state.trend,
                "model_version": model.version,
                "source_dimension": state.dimension_code,
                "prerequisite_gaps": prerequisite_gaps,
            },
            proposed_materials=default_materials_for(rec_type, target_code),
            created_by_ai=False,
            created_by_user_id=created_by_user_id,
        )
        session.add(recommendation)
        await session.flush()
        session.add(
            AdaptiveRecommendationEvidence(
                organization_id=organization_id,
                recommendation_id=recommendation.id,
                source_type="skill_state",
                source_id=state.id,
                dimension_type=state.dimension_type,
                dimension_code=state.dimension_code,
                observed_score=state.mastery_score,
                evidence_weight=1.0,
                summary=state.calculation_explanation,
                evidence_snapshot=state.evidence_snapshot,
            )
        )
        created.append(recommendation)
        if len(created) >= maximum:
            break
    return created


async def audit(
    session: AsyncSession,
    *,
    organization_id: UUID,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    student_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AdaptiveAuditEvent(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            student_id=student_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )


async def create_path(
    session: AsyncSession,
    *,
    organization_id: UUID,
    teacher_id: UUID,
    model: AdaptiveModelVersion,
    data: LearningPathCreate,
    auto_approve: bool = False,
) -> AdaptiveLearningPath:
    now = datetime.now(UTC)
    path = AdaptiveLearningPath(
        organization_id=organization_id,
        student_id=data.student_id,
        classroom_id=data.classroom_id,
        group_id=data.group_id,
        recommendation_id=data.recommendation_id,
        model_version_id=model.id,
        created_by_user_id=teacher_id,
        approved_by_user_id=teacher_id if auto_approve else None,
        title=data.title,
        description=data.description,
        path_type=data.path_type,
        status="approved" if auto_approve else "draft",
        goal=data.goal,
        target_dimension_type=data.target_dimension_type,
        target_dimension_code=data.target_dimension_code,
        target_mastery=data.target_mastery,
        minimum_evidence_count=data.minimum_evidence_count,
        settings_json=data.settings_json,
        approved_at=now if auto_approve else None,
    )
    session.add(path)
    await session.flush()
    for position, step_data in enumerate(data.steps, start=1):
        session.add(
            AdaptivePathStep(
                organization_id=organization_id,
                path_id=path.id,
                assignment_id=step_data.assignment_id,
                position=position,
                step_type=step_data.step_type,
                title=step_data.title,
                description=step_data.description,
                content_reference=step_data.content_reference,
                is_required=step_data.is_required,
                status="available" if position == 1 and auto_approve else "locked",
                advancement_rule=step_data.advancement_rule,
                due_at=step_data.due_at,
                available_at=now if position == 1 and auto_approve else None,
            )
        )
    await audit(
        session,
        organization_id=organization_id,
        actor_user_id=teacher_id,
        student_id=data.student_id,
        action="path.created",
        entity_type="learning_path",
        entity_id=path.id,
        details={"status": path.status, "target": data.target_dimension_code},
    )
    await session.flush()
    return path


async def approve_recommendation_as_path(
    session: AsyncSession,
    *,
    organization_id: UUID,
    recommendation: AdaptiveRecommendation,
    teacher_id: UUID,
    model: AdaptiveModelVersion,
) -> AdaptiveLearningPath:
    steps = []
    for item in recommendation.proposed_materials:
        steps.append(
            {
                "title": item.get("title", "Atividade recomendada"),
                "description": item.get("description", ""),
                "step_type": item.get("type", "activity"),
                "content_reference": item,
                "advancement_rule": {"completion_required": True},
            }
        )
    data = LearningPathCreate.model_validate(
        {
            "student_id": recommendation.student_id,
            "classroom_id": recommendation.classroom_id,
            "group_id": recommendation.group_id,
            "recommendation_id": recommendation.id,
            "title": recommendation.title,
            "description": recommendation.rationale,
            "path_type": recommendation.recommendation_type,
            "goal": f"Alcançar domínio mínimo de {recommendation.target_mastery:.0%} em {recommendation.target_dimension_code}.",
            "target_dimension_type": recommendation.target_dimension_type,
            "target_dimension_code": recommendation.target_dimension_code,
            "target_mastery": recommendation.target_mastery,
            "minimum_evidence_count": 5,
            "settings_json": {"teacher_approval_required": True, "public_ranking": False},
            "steps": steps,
        }
    )
    path = await create_path(
        session,
        organization_id=organization_id,
        teacher_id=teacher_id,
        model=model,
        data=data,
        auto_approve=True,
    )
    recommendation.status = "approved"
    recommendation.reviewed_by_user_id = teacher_id
    recommendation.reviewed_at = datetime.now(UTC)
    return path


async def load_path_with_steps(
    session: AsyncSession,
    *,
    organization_id: UUID,
    path: AdaptiveLearningPath,
) -> tuple[AdaptiveLearningPath, list[AdaptivePathStep]]:
    steps = list(
        (
            await session.scalars(
                select(AdaptivePathStep)
                .where(
                    AdaptivePathStep.organization_id == organization_id,
                    AdaptivePathStep.path_id == path.id,
                )
                .order_by(AdaptivePathStep.position.asc())
            )
        ).all()
    )
    return path, steps


async def activate_path(
    session: AsyncSession,
    *,
    path: AdaptiveLearningPath,
    actor_user_id: UUID,
) -> None:
    now = datetime.now(UTC)
    path.status = "active"
    path.approved_by_user_id = path.approved_by_user_id or actor_user_id
    path.approved_at = path.approved_at or now
    path.started_at = path.started_at or now
    first = await session.scalar(
        select(AdaptivePathStep)
        .where(AdaptivePathStep.path_id == path.id)
        .order_by(AdaptivePathStep.position.asc())
    )
    if first is not None and first.status == "locked":
        first.status = "available"
        first.available_at = now


async def complete_step(
    session: AsyncSession,
    *,
    organization_id: UUID,
    step: AdaptivePathStep,
    score: float | None,
    evidence_count: int,
    notes: str,
) -> AdaptivePathStep | None:
    now = datetime.now(UTC)
    step.status = "completed"
    step.completed_at = now
    step.completion_snapshot = {
        "score": score,
        "evidence_count": evidence_count,
        "notes": notes,
        "completed_at": now.isoformat(),
    }
    next_step = await session.scalar(
        select(AdaptivePathStep).where(
            AdaptivePathStep.organization_id == organization_id,
            AdaptivePathStep.path_id == step.path_id,
            AdaptivePathStep.position == step.position + 1,
        )
    )
    if next_step is not None and next_step.status == "locked":
        next_step.status = "available"
        next_step.available_at = now
    return next_step


async def schedule_reviews_for_path(
    session: AsyncSession,
    *,
    organization_id: UUID,
    path: AdaptiveLearningPath,
    student_ids: list[UUID],
    mastery_score: float,
) -> int:
    dates = build_review_dates(mastery_score=mastery_score)
    count = 0
    for student_id in student_ids:
        for review_number, scheduled_for in enumerate(dates, start=1):
            session.add(
                AdaptiveReviewSchedule(
                    organization_id=organization_id,
                    student_id=student_id,
                    path_id=path.id,
                    dimension_type=path.target_dimension_type,
                    dimension_code=path.target_dimension_code,
                    review_number=review_number,
                    scheduled_for=scheduled_for,
                )
            )
            count += 1
    return count


async def path_student_ids(session: AsyncSession, path: AdaptiveLearningPath) -> list[UUID]:
    if path.student_id is not None:
        return [path.student_id]
    if path.group_id is not None:
        return list(
            (
                await session.scalars(
                    select(AdaptiveGroupMember.student_id).where(
                        AdaptiveGroupMember.group_id == path.group_id,
                        AdaptiveGroupMember.removed_at.is_(None),
                    )
                )
            ).all()
        )
    if path.classroom_id is not None:
        return list(
            (
                await session.scalars(
                    select(ClassroomEnrollment.user_id).where(
                        ClassroomEnrollment.classroom_id == path.classroom_id,
                        ClassroomEnrollment.role == "student",
                    )
                )
            ).all()
        )
    return []


async def calculate_path_outcome(
    session: AsyncSession,
    *,
    organization_id: UUID,
    path: AdaptiveLearningPath,
    student_id: UUID | None,
) -> AdaptivePathOutcome:
    state = None
    if student_id is not None:
        state = await session.scalar(
            select(AdaptiveSkillState).where(
                AdaptiveSkillState.organization_id == organization_id,
                AdaptiveSkillState.student_id == student_id,
                AdaptiveSkillState.dimension_type == path.target_dimension_type,
                AdaptiveSkillState.dimension_code == path.target_dimension_code,
            )
        )
    steps = list(
        (
            await session.scalars(
                select(AdaptivePathStep).where(AdaptivePathStep.path_id == path.id)
            )
        ).all()
    )
    completed = sum(1 for item in steps if item.status == "completed")
    completion_rate = completed / len(steps) if steps else 0.0
    before = None
    evidence_before = 0
    if path.recommendation_id is not None:
        recommendation = await session.get(AdaptiveRecommendation, path.recommendation_id)
        if recommendation:
            before = recommendation.evidence_summary.get("mastery_score")
            evidence_before = int(recommendation.evidence_summary.get("evidence_count", 0))
    after = state.mastery_score if state else None
    delta = after - float(before) if after is not None and before is not None else None
    interpretation = "A evolução é descritiva e não estabelece causalidade."
    if delta is not None:
        interpretation = (
            f"Variação observada de {delta * 100:+.1f} pontos percentuais após a trilha. "
            "O resultado é descritivo e deve ser interpretado junto às demais evidências."
        )
    outcome = AdaptivePathOutcome(
        organization_id=organization_id,
        path_id=path.id,
        student_id=student_id,
        dimension_type=path.target_dimension_type,
        dimension_code=path.target_dimension_code,
        mastery_before=float(before) if before is not None else None,
        mastery_after=after,
        mastery_delta=delta,
        evidence_before=evidence_before,
        evidence_after=state.evidence_count if state else 0,
        completion_rate=completion_rate,
        interpretation=interpretation,
    )
    session.add(outcome)
    return outcome


async def create_group(
    session: AsyncSession,
    *,
    organization_id: UUID,
    teacher_id: UUID,
    data: StudentGroupCreate,
) -> AdaptiveStudentGroup:
    group = AdaptiveStudentGroup(
        organization_id=organization_id,
        classroom_id=data.classroom_id,
        created_by_user_id=teacher_id,
        name=data.name,
        purpose=data.purpose,
        target_dimension_type=data.target_dimension_type,
        target_dimension_code=data.target_dimension_code,
        expires_at=data.expires_at,
        is_visible_to_students=False,
    )
    session.add(group)
    await session.flush()
    for student_id in dict.fromkeys(data.student_ids):
        session.add(
            AdaptiveGroupMember(
                organization_id=organization_id,
                group_id=group.id,
                student_id=student_id,
                reason_snapshot={"reason": data.purpose, "target": data.target_dimension_code},
                added_by_user_id=teacher_id,
            )
        )
    await audit(
        session,
        organization_id=organization_id,
        actor_user_id=teacher_id,
        action="group.created",
        entity_type="adaptive_group",
        entity_id=group.id,
        details={"member_count": len(set(data.student_ids))},
    )
    return group


async def delete_pending_recommendations(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
) -> int:
    result = await session.execute(
        delete(AdaptiveRecommendation).where(
            AdaptiveRecommendation.organization_id == organization_id,
            AdaptiveRecommendation.student_id == student_id,
            AdaptiveRecommendation.status == "pending_review",
        )
    )
    return int(result.rowcount or 0)
