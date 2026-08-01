from __future__ import annotations

import hashlib
import json
import math
from typing import Any

MINIMUM_GROUP_SIZE = 5
ALLOWED_EVENT_TYPES = {
    "SESSION_STARTED", "SESSION_ENDED", "PAGE_VIEWED", "PANEL_VIEWED",
    "POSITION_DWELL", "PAGE_COMPLETED", "PANEL_COMPLETED",
    "BOOKMARK_CREATED", "NARRATION_STARTED", "NARRATION_COMPLETED",
    "GLOSSARY_OPENED", "ACCESSIBILITY_CHANGED", "ASSESSMENT_OPENED",
    "PRESENTATION_JOINED", "PRESENTATION_LEFT", "PRESENTATION_SYNCED",
}


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clamp_duration(duration_ms: int | None) -> int:
    return min(max(int(duration_ms or 0), 0), 1_800_000)


def safe_rate(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator > 0 else 0.0


def privacy_guard(sample_size: int, minimum: int = MINIMUM_GROUP_SIZE) -> dict[str, Any]:
    suppressed = sample_size < minimum
    return {
        "sample_size": sample_size,
        "minimum_group_size": minimum,
        "suppressed": suppressed,
        "reason": "MINIMUM_GROUP_SIZE" if suppressed else None,
    }


def median(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[middle], 4)
    return round((ordered[middle - 1] + ordered[middle]) / 2, 4)


def pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - left_mean) ** 2 for x in left)
        * sum((y - right_mean) ** 2 for y in right)
    )
    return round(numerator / denominator, 4) if denominator else None


def correlation_label(value: float | None) -> str:
    if value is None:
        return "INSUFFICIENT_VARIATION"
    strength = "WEAK" if abs(value) < 0.3 else "MODERATE" if abs(value) < 0.7 else "STRONG"
    return f"{strength}_{'POSITIVE' if value >= 0 else 'NEGATIVE'}"
