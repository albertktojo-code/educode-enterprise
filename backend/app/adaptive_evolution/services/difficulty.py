from __future__ import annotations

from ..enums import DifficultyClassification, DifficultyLevel
from ..schemas import (
    IndividualDifficultyInput,
    IndividualDifficultyResult,
    ObservedDifficultyInput,
    ObservedDifficultyResult,
)


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def difficulty_level(score: float) -> DifficultyLevel:
    if score < 0.20:
        return DifficultyLevel.VERY_EASY
    if score < 0.40:
        return DifficultyLevel.EASY
    if score < 0.65:
        return DifficultyLevel.INTERMEDIATE
    if score < 0.85:
        return DifficultyLevel.HARD
    return DifficultyLevel.VERY_HARD


def calculate_individual_difficulty(payload: IndividualDifficultyInput) -> IndividualDifficultyResult:
    hint_reliance = payload.average_hint_level / 5
    raw = (
        0.12
        + (payload.mastery_score * 0.48)
        + (payload.recent_performance * 0.24)
        + (payload.prerequisite_mastery * 0.14)
        + (payload.confidence_score * 0.08)
        - (hint_reliance * 0.12)
    )
    target = clamp(raw)
    previous = payload.previous_difficulty_score
    change = 0.0 if previous is None else target - previous

    # Evita saltos superiores a um nível sem revisão docente.
    requires_review = previous is not None and abs(change) > payload.max_change_per_cycle
    if previous is not None:
        bounded_change = max(-payload.max_change_per_cycle, min(payload.max_change_per_cycle, change))
        target = clamp(previous + bounded_change)
        change = target - previous

    if change > 0.03:
        action = "INCREASE_ONE_LEVEL"
    elif change < -0.03:
        action = "DECREASE_ONE_LEVEL"
    else:
        action = "MAINTAIN"

    confidence = clamp(
        (payload.confidence_score * 0.55)
        + (payload.prerequisite_mastery * 0.20)
        + (0.25 if previous is not None else 0.10)
    )
    reason = (
        f"Dificuldade calculada por domínio {payload.mastery_score:.2f}, desempenho recente "
        f"{payload.recent_performance:.2f}, pré-requisitos {payload.prerequisite_mastery:.2f} "
        f"e uso médio de pistas {payload.average_hint_level:.2f}."
    )
    return IndividualDifficultyResult(
        difficulty_score=round(target, 4),
        difficulty_level=difficulty_level(target),
        confidence_score=round(confidence, 4),
        change=round(change, 4),
        action=action,
        reason=reason,
        requires_teacher_review=requires_review,
    )


def classify_difference(
    difference: float, sample_size: int, minimum_sample_size: int = 10
) -> DifficultyClassification:
    if sample_size < minimum_sample_size:
        return DifficultyClassification.INSUFFICIENT_EVIDENCE
    if difference <= -0.20:
        return DifficultyClassification.MUCH_EASIER
    if difference <= -0.08:
        return DifficultyClassification.SLIGHTLY_EASIER
    if difference < 0.08:
        return DifficultyClassification.COHERENT
    if difference < 0.20:
        return DifficultyClassification.SLIGHTLY_HARDER
    return DifficultyClassification.MUCH_HARDER


def calculate_observed_difficulty(payload: ObservedDifficultyInput) -> ObservedDifficultyResult:
    if payload.attempts_count == 0:
        return ObservedDifficultyResult(
            predicted_difficulty=payload.predicted_difficulty,
            observed_difficulty=None,
            difference=None,
            classification=DifficultyClassification.INSUFFICIENT_EVIDENCE,
            sample_size=0,
            confidence_score=0.0,
            metrics={},
            requires_review=False,
        )

    accuracy = payload.correct_count / payload.attempts_count
    attempts_factor = clamp((payload.average_attempts - 1) / 4)
    hint_factor = clamp(payload.average_hint_level / 5)
    if payload.expected_time_seconds > 0:
        time_factor = clamp(payload.average_time_seconds / payload.expected_time_seconds - 1)
    else:
        time_factor = 0.0

    observed = clamp(
        ((1 - accuracy) * 0.50)
        + (attempts_factor * 0.20)
        + (hint_factor * 0.15)
        + (payload.abandonment_rate * 0.10)
        + (time_factor * 0.05)
    )
    difference = observed - payload.predicted_difficulty
    classification = classify_difference(difference, payload.attempts_count, payload.minimum_sample_size)
    confidence = clamp(payload.attempts_count / 100)
    requires_review = (
        abs(difference) >= payload.review_difference_threshold
        and payload.attempts_count >= payload.minimum_sample_size
        and confidence >= 0.30
    )

    return ObservedDifficultyResult(
        predicted_difficulty=payload.predicted_difficulty,
        observed_difficulty=round(observed, 4),
        difference=round(difference, 4),
        classification=classification,
        sample_size=payload.attempts_count,
        confidence_score=round(confidence, 4),
        metrics={
            "accuracy": round(accuracy, 4),
            "average_attempts_factor": round(attempts_factor, 4),
            "average_hint_factor": round(hint_factor, 4),
            "abandonment_rate": round(payload.abandonment_rate, 4),
            "time_factor": round(time_factor, 4),
        },
        requires_review=requires_review,
    )
