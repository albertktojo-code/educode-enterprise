from __future__ import annotations

from datetime import date, timedelta

from ..enums import ReviewStatus
from ..schemas import SpacedReviewInput, SpacedReviewResult


def _base_interval(result_score: float, policy: dict[str, int]) -> int:
    if result_score < 0.40:
        return max(1, int(policy.get("very_low", 1)))
    if result_score < 0.60:
        return max(1, int(policy.get("low", 3)))
    if result_score < 0.80:
        return max(1, int(policy.get("adequate", 7)))
    if result_score < 0.90:
        return max(1, int(policy.get("advanced", 15)))
    return max(1, int(policy.get("mastered", 30)))


def calculate_next_review(payload: SpacedReviewInput) -> SpacedReviewResult:
    reference = payload.reference_date or date.today()
    interval = _base_interval(payload.result_score, payload.interval_policy)

    # O domínio e a confiança estabilizam o intervalo; pistas elevadas o reduzem.
    stability = (payload.mastery_score * 0.65) + (payload.confidence_score * 0.35)
    if stability >= 0.85 and payload.result_score >= 0.80:
        interval = max(interval, 15)
    elif stability < 0.35:
        interval = min(interval, 3)

    if payload.hint_level_used >= 4:
        interval = max(1, round(interval * 0.50))
    elif payload.hint_level_used >= 2:
        interval = max(1, round(interval * 0.75))

    if payload.previous_interval_days and payload.result_score >= 0.80:
        interval = max(interval, min(60, round(payload.previous_interval_days * 1.60)))

    if payload.overdue_days > 0:
        interval = max(1, interval - min(interval - 1, payload.overdue_days // 3))

    scheduled_for = reference + timedelta(days=interval)
    priority = 100 - min(80, round(payload.mastery_score * 45 + payload.confidence_score * 25))
    if payload.result_score < 0.40:
        priority = min(100, priority + 20)
    if payload.overdue_days:
        priority = min(100, priority + min(20, payload.overdue_days))

    reason = (
        f"Intervalo de {interval} dia(s) calculado com resultado {payload.result_score:.2f}, "
        f"domínio {payload.mastery_score:.2f}, confiança {payload.confidence_score:.2f} "
        f"e pista máxima {payload.hint_level_used}."
    )
    return SpacedReviewResult(
        interval_days=interval,
        scheduled_for=scheduled_for,
        status=ReviewStatus.FUTURE,
        priority=max(1, min(100, priority)),
        reason=reason,
    )
