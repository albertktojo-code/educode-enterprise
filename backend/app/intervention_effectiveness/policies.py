from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from statistics import median
from typing import Any, Iterable

WINDOWS: tuple[tuple[str, int], ...] = (
    ("immediate", 0),
    ("d7", 7),
    ("d15", 15),
    ("d30", 30),
    ("d60", 60),
)


def window_definitions() -> list[dict[str, int | str]]:
    return [
        {"code": code, "days": days}
        for code, days in WINDOWS
    ]


def scheduled_for(completed_at: datetime, window_days: int) -> datetime:
    value = completed_at
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value + timedelta(days=window_days)


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def privacy_guard(sample_size: int, minimum_group_size: int) -> bool:
    return sample_size < minimum_group_size


def average(values: Iterable[float]) -> float | None:
    rows = list(values)
    return round(sum(rows) / len(rows), 4) if rows else None


def median_value(values: Iterable[float]) -> float | None:
    rows = list(values)
    return round(float(median(rows)), 2) if rows else None


def metric_from_intervention(
    target_snapshot: dict[str, Any],
    baseline_snapshot: dict[str, Any],
) -> tuple[str, float | None, float | None]:
    metric = str(
        target_snapshot.get("metric")
        or (
            "assessment_score_percent"
            if baseline_snapshot.get("assessment_score_percent") is not None
            else "progress_percent"
            if baseline_snapshot.get("progress_percent") is not None
            else "insufficient_evidence"
        )
    )
    before = target_snapshot.get("before")
    if before is None:
        source = baseline_snapshot.get(metric)
        before = float(source) / 100 if source is not None else None
    target = target_snapshot.get("target_mastery")
    return (
        metric,
        float(before) if before is not None else None,
        float(target) if target is not None else None,
    )


def classify_followup(
    *,
    baseline_value: float | None,
    observed_value: float | None,
    immediate_value: float | None,
    target_value: float | None,
    minimum_improvement: float,
    retention_tolerance: float,
) -> dict[str, Any]:
    if baseline_value is None or observed_value is None:
        return {
            "comparable": False,
            "delta": None,
            "improved": False,
            "target_met": False,
            "retained": False,
            "outcome": "insufficient_evidence",
        }

    delta = observed_value - baseline_value
    improved = delta >= minimum_improvement
    target_met = (
        target_value is not None
        and observed_value >= target_value
    )
    retained = (
        immediate_value is not None
        and observed_value >= immediate_value - retention_tolerance
    )
    outcome = (
        "retained"
        if retained and (improved or target_met)
        else "improved"
        if improved
        else "target_met"
        if target_met
        else "regressed"
        if delta <= -minimum_improvement
        else "stable"
    )
    return {
        "comparable": True,
        "delta": round(delta, 4),
        "improved": improved,
        "target_met": target_met,
        "retained": retained,
        "outcome": outcome,
    }


def period_bounds(
    period_start: date | None,
    period_end: date | None,
) -> tuple[date, date]:
    end = period_end or date.today()
    start = period_start or (end - timedelta(days=90))
    if end < start:
        raise ValueError("period_end deve ser igual ou posterior a period_start")
    if (end - start).days > 730:
        raise ValueError("O período não pode exceder 730 dias")
    return start, end


def dimension_key(
    dimension_type: str,
    value: str | bool | None,
) -> str:
    normalized = "none" if value is None else str(value).lower()
    return f"{dimension_type}:{normalized}"
