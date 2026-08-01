from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter
from typing import Any, Iterable, Sequence


def stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def calculate_facility(correct: int, answered: int) -> float | None:
    if answered <= 0:
        return None
    return round(clamp(correct / answered), 4)


def observed_difficulty_from_facility(facility: float | None) -> float | None:
    if facility is None:
        return None
    return round(clamp(1.0 - facility), 4)


def calculate_discrimination(upper_correct: int, upper_total: int, lower_correct: int, lower_total: int) -> float | None:
    if upper_total <= 0 or lower_total <= 0:
        return None
    value = upper_correct / upper_total - lower_correct / lower_total
    return round(max(-1.0, min(1.0, value)), 4)


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denominator_x == 0 or denominator_y == 0:
        return None
    return round(max(-1.0, min(1.0, numerator / (denominator_x * denominator_y))), 4)


def point_biserial(item_scores: Sequence[int], total_scores: Sequence[float]) -> float | None:
    if any(score not in (0, 1) for score in item_scores):
        raise ValueError("item_scores devem conter apenas 0 ou 1")
    return pearson_correlation([float(item) for item in item_scores], list(total_scores))


def classify_item_flags(
    *,
    sample_size: int,
    facility_index: float | None,
    discrimination_index: float | None,
    omission_rate: float | None,
    predicted_difficulty: float | None,
    observed_difficulty: float | None,
    minimum_sample: int = 20,
) -> list[str]:
    flags: list[str] = []
    if sample_size < minimum_sample:
        flags.append("INSUFFICIENT_SAMPLE")
    if facility_index is not None and facility_index >= 0.9:
        flags.append("VERY_EASY")
    if facility_index is not None and facility_index <= 0.2:
        flags.append("VERY_DIFFICULT")
    if discrimination_index is not None and discrimination_index < 0:
        flags.append("NEGATIVE_DISCRIMINATION")
    elif discrimination_index is not None and discrimination_index < 0.2:
        flags.append("LOW_DISCRIMINATION")
    if omission_rate is not None and omission_rate >= 0.2:
        flags.append("HIGH_OMISSION")
    if predicted_difficulty is not None and observed_difficulty is not None:
        delta = observed_difficulty - predicted_difficulty
        if delta >= 0.2:
            flags.append("HARDER_THAN_PREDICTED")
        elif delta <= -0.2:
            flags.append("EASIER_THAN_PREDICTED")
    return flags


def analyze_distractors(
    selections: Iterable[str | None],
    correct_option: str,
    *,
    minimum_functioning_rate: float = 0.05,
) -> list[dict[str, Any]]:
    normalized = [value for value in selections if value is not None]
    total = len(normalized)
    counts = Counter(normalized)
    result: list[dict[str, Any]] = []
    for option, count in sorted(counts.items()):
        rate = count / total if total else 0.0
        is_correct = option == correct_option
        result.append({
            "option_code": option,
            "is_correct": is_correct,
            "selection_count": count,
            "selection_rate": round(rate, 4),
            "non_functioning": (not is_correct) and rate < minimum_functioning_rate,
        })
    return result


def descriptive_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "minimum": None, "maximum": None, "standard_deviation": None}
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 4),
        "median": round(statistics.median(values), 4),
        "minimum": round(min(values), 4),
        "maximum": round(max(values), 4),
        "standard_deviation": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
    }


def cronbach_alpha(rows: Sequence[Sequence[float]]) -> float | None:
    if len(rows) < 2 or not rows or len(rows[0]) < 2:
        return None
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("Todas as linhas devem possuir o mesmo numero de itens")
    item_variances = [statistics.pvariance([row[index] for row in rows]) for index in range(width)]
    totals = [sum(row) for row in rows]
    total_variance = statistics.pvariance(totals)
    if total_variance == 0:
        return None
    alpha = width / (width - 1) * (1 - sum(item_variances) / total_variance)
    return round(max(-1.0, min(1.0, alpha)), 4)


def privacy_guard(sample_size: int, minimum_group_size: int = 5) -> dict[str, Any]:
    if minimum_group_size < 2:
        raise ValueError("minimum_group_size deve ser pelo menos 2")
    suppressed = sample_size < minimum_group_size
    return {
        "privacy_suppressed": suppressed,
        "reason": "SMALL_GROUP" if suppressed else None,
        "minimum_group_size": minimum_group_size,
    }


def skill_coverage(mapped_items: int, total_items: int) -> float:
    if total_items <= 0:
        return 0.0
    return round(clamp(mapped_items / total_items), 4)


def trend_label(current: float, previous: float | None, threshold: float = 0.03) -> str:
    if previous is None:
        return "NO_BASELINE"
    delta = current - previous
    if delta >= threshold:
        return "IMPROVING"
    if delta <= -threshold:
        return "DECLINING"
    return "STABLE"
