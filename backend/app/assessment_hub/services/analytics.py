from __future__ import annotations

from statistics import fmean

from ..schemas import ItemAnalyticsInput, ItemAnalyticsResult


def calculate_item_analytics(payload: ItemAnalyticsInput) -> ItemAnalyticsResult:
    observations = payload.observations
    sample_size = len(observations)
    accuracy = sum(1 for item in observations if item.correct) / sample_size
    average_score = fmean(item.score_ratio for item in observations)
    observed_difficulty = 1 - accuracy
    difference = observed_difficulty - payload.predicted_difficulty

    if sample_size < 10:
        classification = "EVIDENCIA_INSUFICIENTE"
    elif difference >= 0.20:
        classification = "MAIS_DIFICIL_QUE_PREVISTO"
    elif difference >= 0.08:
        classification = "LIGEIRAMENTE_MAIS_DIFICIL"
    elif difference <= -0.20:
        classification = "MAIS_FACIL_QUE_PREVISTO"
    elif difference <= -0.08:
        classification = "LIGEIRAMENTE_MAIS_FACIL"
    else:
        classification = "DIFICULDADE_COERENTE"

    confidence = min(1.0, sample_size / 50)
    return ItemAnalyticsResult(
        sample_size=sample_size,
        accuracy_rate=round(accuracy, 4),
        average_score_ratio=round(average_score, 4),
        observed_difficulty=round(observed_difficulty, 4),
        predicted_difficulty=payload.predicted_difficulty,
        difficulty_difference=round(difference, 4),
        classification=classification,
        average_attempts=round(fmean(item.attempts for item in observations), 4),
        average_hints=round(fmean(item.hints for item in observations), 4),
        average_duration_seconds=round(fmean(item.duration_seconds for item in observations), 4),
        confidence=round(confidence, 4),
    )
