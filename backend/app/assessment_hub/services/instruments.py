from __future__ import annotations

from ..schemas import DimensionSummaryInput, DimensionSummaryResult


def summarize_dimensions(payload: DimensionSummaryInput) -> DimensionSummaryResult:
    weighted_earned = 0.0
    weighted_maximum = 0.0
    details: dict[str, dict[str, float]] = {}
    for dimension in payload.dimensions:
        ratio = max(0.0, min(1.0, dimension.earned_score / dimension.maximum_score))
        weighted_earned += ratio * dimension.weight
        weighted_maximum += dimension.weight
        details[dimension.dimension_code] = {
            "earned_score": dimension.earned_score,
            "maximum_score": dimension.maximum_score,
            "percentage": round(ratio * 100, 2),
            "weight": dimension.weight,
        }
    percentage = (weighted_earned / weighted_maximum * 100) if weighted_maximum else 0.0
    return DimensionSummaryResult(
        weighted_percentage=round(percentage, 2),
        dimension_scores=details,
        scoring_version="15.0.0",
    )
