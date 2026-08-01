from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.models.analytics import InterventionStatus, InterventionType

ALLOWED_TRANSITIONS = {
    InterventionStatus.PLANNED: {
        InterventionStatus.ACTIVE,
        InterventionStatus.CANCELED,
    },
    InterventionStatus.ACTIVE: {
        InterventionStatus.COMPLETED,
        InterventionStatus.CANCELED,
    },
    InterventionStatus.COMPLETED: set(),
    InterventionStatus.CANCELED: set(),
}


def choose_recommendation_type(
    *,
    alert_type: str,
    rule_code: str = "",
    progress_percent: float,
    score_percent: float | None,
    accessibility_used: bool,
    observed_accuracy: float | None = None,
) -> str:
    normalized = f"{alert_type} {rule_code}".casefold()
    if "mastery_opportunity" in normalized:
        return (
            "advanced_challenge"
            if observed_accuracy is not None and observed_accuracy >= 92
            else "deepening"
        )
    if "hard_activity" in normalized:
        return (
            "simplified_activity"
            if observed_accuracy is not None and observed_accuracy < 25
            else "equivalent_activity"
        )
    if "skill_difficulty" in normalized:
        return (
            "reinforcement"
            if observed_accuracy is None or observed_accuracy < 30
            else "consolidation"
        )
    if "abandonment" in normalized or "low_completion" in normalized:
        return "guided_reread"
    if score_percent is not None and score_percent < 50:
        return "simplified_activity"
    if "reading" in normalized or "comic" in normalized or progress_percent < 40:
        return "guided_reread"
    if accessibility_used:
        return "individual_feedback"
    return "consolidation"


def canonical_intervention_type(recommendation_type: str) -> InterventionType:
    mapping = {
        "guided_reread": InterventionType.REINFORCEMENT,
        "simplified_activity": InterventionType.ADAPTED_ACTIVITY,
        "equivalent_activity": InterventionType.ADAPTED_ACTIVITY,
        "reinforcement": InterventionType.REINFORCEMENT,
        "consolidation": InterventionType.FOLLOW_UP,
        "deepening": InterventionType.ADVANCED_CHALLENGE,
        "advanced_challenge": InterventionType.ADVANCED_CHALLENGE,
        "individual_feedback": InterventionType.INDIVIDUAL_FEEDBACK,
    }
    return mapping.get(recommendation_type, InterventionType.REINFORCEMENT)


def choose_intervention_type(
    *,
    alert_type: str,
    progress_percent: float,
    score_percent: float | None,
    accessibility_used: bool,
) -> InterventionType:
    recommendation_type = choose_recommendation_type(
        alert_type=alert_type,
        progress_percent=progress_percent,
        score_percent=score_percent,
        accessibility_used=accessibility_used,
    )
    return canonical_intervention_type(recommendation_type)


def intervention_priority(severity: str, confidence: float) -> str:
    if severity == "priority" or confidence >= 0.8:
        return "high"
    if severity == "attention" or confidence >= 0.55:
        return "normal"
    return "low"


def confidence_from_evidence(evidence_count: int, has_assessment: bool) -> float:
    base = min(0.82, 0.3 + evidence_count * 0.08)
    if has_assessment:
        base += 0.08
    return round(min(0.9, base), 4)


def due_dates(days: int, evaluation_days: int) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    due = now + timedelta(days=max(1, days))
    evaluation = due + timedelta(days=max(1, evaluation_days))
    return due, evaluation


def can_transition(current: InterventionStatus, target: InterventionStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def score_proxy(snapshot: dict[str, Any]) -> float:
    """Mantém o proxy legado para consumidores anteriores à análise comparável."""
    score = snapshot.get("assessment_score_percent")
    if score is not None:
        return min(1.0, max(0.0, float(score) / 100))
    progress = snapshot.get("progress_percent", 0.0)
    return min(1.0, max(0.0, float(progress) / 100))


def build_plan(
    *,
    release_id: str | None,
    page_number: int | None,
    panel_number: int | None,
    assignment_id: str | None,
    accessible_version_id: str | None,
    teacher_note: str,
    recommendation_type: str = "reinforcement",
    activity_id: str | None = None,
    question_version_id: str | None = None,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if release_id:
        actions.append(
            {
                "type": "comic_reread",
                "title": "Releitura orientada da HQ",
                "release_id": release_id,
                "page_number": page_number,
                "panel_number": panel_number,
                "completion_required": True,
            }
        )
    if accessible_version_id:
        actions.append(
            {
                "type": "accessible_resource",
                "title": "Utilizar versão acessível",
                "accessible_resource_version_id": accessible_version_id,
                "completion_required": True,
            }
        )
    if assignment_id:
        actions.append(
            {
                "type": "assignment",
                "title": "Realizar atividade complementar",
                "assignment_id": assignment_id,
                "completion_required": True,
            }
        )
    if recommendation_type in {"simplified_activity", "equivalent_activity"}:
        actions.append(
            {
                "type": "activity_variant",
                "title": (
                    "Propor atividade simplificada"
                    if recommendation_type == "simplified_activity"
                    else "Propor atividade equivalente"
                ),
                "variant_kind": recommendation_type,
                "activity_id": activity_id,
                "question_version_id": question_version_id,
                "requires_teacher_selection": True,
                "completion_required": True,
            }
        )
    elif recommendation_type in {"deepening", "advanced_challenge"}:
        actions.append(
            {
                "type": "extension_activity",
                "title": (
                    "Propor desafio avançado"
                    if recommendation_type == "advanced_challenge"
                    else "Propor atividade de aprofundamento"
                ),
                "variant_kind": recommendation_type,
                "activity_id": activity_id,
                "question_version_id": question_version_id,
                "requires_teacher_selection": True,
                "completion_required": True,
            }
        )
    elif recommendation_type == "consolidation":
        actions.append(
            {
                "type": "skill_practice",
                "title": "Consolidar a habilidade observada",
                "variant_kind": recommendation_type,
                "activity_id": activity_id,
                "question_version_id": question_version_id,
                "requires_teacher_selection": True,
                "completion_required": True,
            }
        )
    actions.append(
        {
            "type": "teacher_feedback",
            "title": "Feedback individual do professor",
            "note": teacher_note,
            "completion_required": False,
        }
    )
    return actions


def _percent(snapshot: dict[str, Any], key: str) -> float | None:
    value = snapshot.get(key)
    if value is None:
        return None
    return min(100.0, max(0.0, float(value)))


def comparable_outcome(
    baseline: dict[str, Any],
    observed: dict[str, Any],
    *,
    target_mastery: float,
    minimum_improvement: float,
) -> dict[str, Any]:
    baseline_assessment = _percent(baseline, "assessment_score_percent")
    observed_assessment = _percent(observed, "assessment_score_percent")
    baseline_progress = _percent(baseline, "progress_percent")
    observed_progress = _percent(observed, "progress_percent")

    metric = "insufficient_evidence"
    before_percent: float | None = None
    after_percent: float | None = None

    if baseline_assessment is not None and observed_assessment is not None:
        metric = "assessment_score_percent"
        before_percent = baseline_assessment
        after_percent = observed_assessment
    elif baseline_progress is not None and observed_progress is not None:
        metric = "progress_percent"
        before_percent = baseline_progress
        after_percent = observed_progress

    if before_percent is None or after_percent is None:
        fallback = (
            baseline_assessment
            if baseline_assessment is not None
            else baseline_progress
            if baseline_progress is not None
            else 0.0
        )
        before = fallback / 100
        return {
            "metric": metric,
            "before": round(before, 4),
            "after": round(before, 4),
            "gain": 0.0,
            "outcome": "insufficient_evidence",
            "improved": False,
            "target_met": False,
            "comparable": False,
        }

    before = before_percent / 100
    after = after_percent / 100
    gain = after - before
    improved = gain >= minimum_improvement
    target_met = after >= target_mastery
    outcome = (
        "improved"
        if improved
        else "regressed"
        if gain <= -minimum_improvement
        else "stable"
    )
    return {
        "metric": metric,
        "before": round(before, 4),
        "after": round(after, 4),
        "gain": round(gain, 4),
        "outcome": outcome,
        "improved": improved,
        "target_met": target_met,
        "comparable": True,
    }


def safe_student_actions(
    plan_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    allowed = {
        "type",
        "title",
        "release_id",
        "page_number",
        "panel_number",
        "assignment_id",
        "accessible_resource_version_id",
        "variant_kind",
        "activity_id",
        "question_version_id",
        "requires_teacher_selection",
        "completion_required",
    }
    actions = plan_snapshot.get("actions", [])
    return [
        {key: value for key, value in action.items() if key in allowed}
        for action in actions
        if isinstance(action, dict)
    ]
