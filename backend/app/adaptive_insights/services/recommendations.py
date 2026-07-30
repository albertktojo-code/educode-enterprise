from __future__ import annotations

from collections import defaultdict

from ..enums import RecommendationAction
from ..schemas import (
    InterventionRecommendationInput,
    InterventionRecommendationResult,
    RecommendationCandidate,
)


def recommend_from_intervention_history(
    payload: InterventionRecommendationInput,
) -> InterventionRecommendationResult:
    grouped: dict[str, list] = defaultdict(list)
    for item in payload.history:
        grouped[item.intervention_type].append(item)

    candidates: list[RecommendationCandidate] = []
    for intervention in payload.candidate_interventions:
        records = grouped.get(intervention, [])
        if not records:
            candidates.append(
                RecommendationCandidate(
                    intervention_type=intervention,
                    score=0.35,
                    historical_uses=0,
                    average_gain=0.0,
                    rationale=["Sem histórico suficiente; prioridade exploratória controlada."],
                )
            )
            continue

        weighted_gains: list[float] = []
        total_weight = 0.0
        for record in records:
            gain = record.mastery_after - record.mastery_before
            recency = max(0.25, 1 - min(record.days_ago, 180) / 240)
            quality = 0.55 + 0.45 * record.completion_rate
            support_penalty = max(0.55, 1 - record.hint_level_average * 0.06)
            attempts_penalty = max(0.65, 1 - max(0, record.attempts_average - 1) * 0.05)
            weight = recency * quality * support_penalty * attempts_penalty
            weighted_gains.append(gain * weight)
            total_weight += weight
        average_gain = sum(weighted_gains) / total_weight if total_weight else 0.0
        evidence_factor = min(1.0, len(records) / 5)
        score = min(1.0, max(0.0, 0.50 + average_gain * 1.8 + evidence_factor * 0.20))
        candidates.append(
            RecommendationCandidate(
                intervention_type=intervention,
                score=round(score, 4),
                historical_uses=len(records),
                average_gain=round(average_gain, 4),
                rationale=[
                    f"{len(records)} uso(s) histórico(s) considerado(s).",
                    f"Ganho médio ponderado de domínio: {average_gain:.3f}.",
                    "Resultados recentes e concluídos receberam maior peso.",
                ],
            )
        )

    candidates.sort(key=lambda item: (item.score, item.historical_uses), reverse=True)
    best = candidates[0] if candidates else None
    warnings = ["Recomendação descritiva; exige validação docente antes da aplicação."]

    if payload.current_confidence < 0.35 or len(payload.history) < 2:
        action = RecommendationAction.COLLECT_MORE_EVIDENCE
        recommendation = best.intervention_type if best else None
        confidence = min(0.45, payload.current_confidence + len(payload.history) * 0.08)
        warnings.append("Histórico ou confiança insuficiente para uma decisão forte.")
    elif payload.current_mastery >= 0.85 and payload.current_confidence >= 0.65:
        action = RecommendationAction.ADVANCE
        recommendation = None
        confidence = min(0.95, 0.65 + payload.current_confidence * 0.25)
    elif best and best.average_gain > 0.03:
        action = RecommendationAction.REPEAT_INTERVENTION
        recommendation = best.intervention_type
        confidence = min(0.90, 0.45 + best.score * 0.35 + min(best.historical_uses, 5) * 0.03)
    elif best and best.historical_uses > 0:
        action = RecommendationAction.TRY_ALTERNATIVE
        alternative = next((item for item in candidates if item.historical_uses == 0), None)
        recommendation = alternative.intervention_type if alternative else best.intervention_type
        confidence = 0.55
    else:
        action = RecommendationAction.TEACHER_REVIEW
        recommendation = best.intervention_type if best else None
        confidence = 0.40

    return InterventionRecommendationResult(
        action=action,
        recommended_intervention=recommendation,
        confidence=round(confidence, 4),
        candidates=candidates,
        requires_teacher_review=True,
        warnings=warnings,
    )
