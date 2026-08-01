from __future__ import annotations

from collections import Counter
from typing import Any

from ..enums import RecommendationAction
from ..schemas import (
    RecommendationSimulationResult,
    SimulatedDecision,
    SimulationProfile,
)


def _decision(profile: SimulationProfile, config: dict[str, Any]) -> SimulatedDecision:
    advance_score = float(config.get("advance_mastery", 0.75))
    minimum_confidence = float(config.get("minimum_confidence", 0.55))
    minimum_evidences = int(config.get("minimum_evidences", 3))
    max_failures = int(config.get("max_intervention_failures", 2))

    if profile.evidences_count < minimum_evidences or profile.confidence_score < minimum_confidence:
        action = RecommendationAction.COLLECT_MORE_EVIDENCE
        reason = "Evidências ou confiança abaixo dos limites do modelo."
        score = min(profile.confidence_score, profile.evidences_count / max(minimum_evidences, 1))
    elif profile.intervention_failures > max_failures:
        action = RecommendationAction.TEACHER_REVIEW
        reason = "Falhas de intervenção acima do limite configurado."
        score = 1 - min(1.0, profile.intervention_failures / 10)
    elif profile.overdue_reviews > 0:
        action = RecommendationAction.REVIEW_PREREQUISITE
        reason = "Existem revisões atrasadas que devem ser consideradas antes do avanço."
        score = max(0.0, 1 - profile.overdue_reviews * 0.1)
    elif profile.mastery_score >= advance_score:
        action = RecommendationAction.ADVANCE
        reason = "Domínio atingiu o limiar de avanço."
        score = profile.mastery_score
    elif profile.mastery_score < float(config.get("reinforce_below", 0.40)):
        action = RecommendationAction.REPEAT_INTERVENTION
        reason = "Domínio abaixo do limiar de reforço."
        score = 1 - profile.mastery_score
    else:
        action = RecommendationAction.TRY_ALTERNATIVE
        reason = "Domínio intermediário; simulação sugere estratégia alternativa."
        score = 0.5

    return SimulatedDecision(
        student_id=profile.student_id,
        learning_node_id=profile.learning_node_id,
        action=action,
        reason=reason,
        score=round(score, 4),
    )


def simulate_recommendations(
    profiles: list[SimulationProfile],
    configuration: dict[str, Any],
) -> RecommendationSimulationResult:
    decisions = [_decision(profile, configuration) for profile in profiles]
    distribution = Counter(item.action.value for item in decisions)
    return RecommendationSimulationResult(
        profiles_count=len(profiles),
        decisions=decisions,
        action_distribution=dict(distribution),
        warnings=[
            "Simulação isolada: não altera trilhas, notas, domínio ou agenda de revisão.",
            "Resultados devem ser revisados antes da publicação de um modelo.",
        ],
    )
