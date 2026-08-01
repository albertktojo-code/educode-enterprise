from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping, Sequence


def canonical_hash(payload: Mapping[str, Any] | Sequence[Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def validate_rubric_criteria(criteria: Sequence[Mapping[str, Any]], maximum_score: float) -> list[str]:
    errors: list[str] = []
    if maximum_score <= 0:
        errors.append("MAXIMUM_SCORE_MUST_BE_POSITIVE")
    if not criteria:
        errors.append("AT_LEAST_ONE_CRITERION_REQUIRED")
        return errors
    codes: set[str] = set()
    total = 0.0
    for index, criterion in enumerate(criteria):
        code = str(criterion.get("code", "")).strip()
        name = str(criterion.get("name", "")).strip()
        score = float(criterion.get("maximum_score", 0) or 0)
        if not code:
            errors.append(f"CRITERION_{index}_CODE_REQUIRED")
        elif code in codes:
            errors.append(f"DUPLICATE_CRITERION_CODE:{code}")
        codes.add(code)
        if not name:
            errors.append(f"CRITERION_{index}_NAME_REQUIRED")
        if score <= 0:
            errors.append(f"CRITERION_{index}_MAXIMUM_SCORE_INVALID")
        total += max(score, 0)
        levels = criterion.get("levels", []) or []
        level_codes = [str(level.get("code", "")) for level in levels if isinstance(level, Mapping)]
        if len(level_codes) != len(set(level_codes)):
            errors.append(f"CRITERION_{index}_DUPLICATE_LEVEL_CODE")
    if abs(total - maximum_score) > 0.0001:
        errors.append("CRITERIA_TOTAL_MUST_MATCH_MAXIMUM_SCORE")
    return errors


def calculate_rubric_score(
    criteria: Sequence[Mapping[str, Any]], awarded: Mapping[str, float]
) -> dict[str, Any]:
    maximum = 0.0
    total = 0.0
    breakdown: list[dict[str, Any]] = []
    for criterion in criteria:
        code = str(criterion["code"])
        criterion_max = float(criterion.get("maximum_score", 0) or 0)
        raw = float(awarded.get(code, 0) or 0)
        score = min(max(raw, 0.0), criterion_max)
        maximum += criterion_max
        total += score
        breakdown.append(
            {
                "criterion_code": code,
                "awarded_score": round(score, 4),
                "maximum_score": round(criterion_max, 4),
                "percentage": round((score / criterion_max * 100) if criterion_max else 0, 2),
            }
        )
    percentage = 0.0 if maximum <= 0 else total / maximum * 100
    return {
        "total_score": round(total, 4),
        "maximum_score": round(maximum, 4),
        "percentage": round(percentage, 2),
        "breakdown": breakdown,
    }


def determine_review_requirement(
    *,
    question_type: str,
    automatic_confidence: float | None,
    confidence_threshold: float = 0.85,
    score_difference: float | None = None,
    discrepancy_threshold: float = 0.2,
    explicitly_requested: bool = False,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    normalized_type = question_type.upper()
    if normalized_type in {"ESSAY", "DISCURSIVE", "PROJECT", "PRACTICAL", "MULTIMEDIA"}:
        reasons.append("QUESTION_TYPE_REQUIRES_HUMAN_REVIEW")
    if automatic_confidence is not None and automatic_confidence < confidence_threshold:
        reasons.append("AUTOMATIC_CONFIDENCE_BELOW_THRESHOLD")
    if score_difference is not None and abs(score_difference) > discrepancy_threshold:
        reasons.append("REVIEWER_SCORE_DISCREPANCY")
    if explicitly_requested:
        reasons.append("REVIEW_EXPLICITLY_REQUESTED")
    return bool(reasons), reasons


def reconcile_scores(scores: Sequence[float], maximum_score: float) -> dict[str, Any]:
    if not scores:
        return {"final_score": 0.0, "spread": 0.0, "requires_moderation": False}
    bounded = [min(max(float(score), 0.0), maximum_score) for score in scores]
    mean = sum(bounded) / len(bounded)
    spread = max(bounded) - min(bounded)
    threshold = max(maximum_score * 0.2, 0.5)
    return {
        "final_score": round(mean, 4),
        "spread": round(spread, 4),
        "requires_moderation": spread > threshold,
    }


def aggregate_skill_feedback(
    criterion_scores: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}
    names: dict[str, str] = {}
    for item in criterion_scores:
        awarded = float(item.get("awarded_score", 0) or 0)
        maximum = float(item.get("maximum_score", 0) or 0)
        normalized = 0.0 if maximum <= 0 else awarded / maximum
        for code, payload in (item.get("skill_scores") or {}).items():
            if isinstance(payload, Mapping):
                weight = float(payload.get("weight", 1.0) or 1.0)
                names[code] = str(payload.get("name") or code)
            else:
                weight = float(payload or 1.0)
                names[code] = code
            totals[code] = totals.get(code, 0.0) + normalized * weight
            weights[code] = weights.get(code, 0.0) + weight
    result: list[dict[str, Any]] = []
    for code in sorted(totals):
        score = 0.0 if weights[code] <= 0 else totals[code] / weights[code]
        result.append(
            {
                "skill_code": code,
                "skill_name": names[code],
                "score": round(score, 4),
                "classification": classify_skill_score(score),
            }
        )
    return result


def classify_skill_score(score: float) -> str:
    if score >= 0.9:
        return "DOMINADO"
    if score >= 0.7:
        return "AVANCADO"
    if score >= 0.45:
        return "ADEQUADO"
    if score >= 0.2:
        return "EM_DESENVOLVIMENTO"
    return "INICIAL"


def build_formative_feedback(
    *,
    total_score: float,
    maximum_score: float,
    strengths: Sequence[str],
    improvement_points: Sequence[str],
    next_steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    percentage = 0.0 if maximum_score <= 0 else total_score / maximum_score * 100
    if percentage >= 90:
        summary = "Desempenho consistente. O estudante pode avançar para desafios de aprofundamento."
    elif percentage >= 70:
        summary = "Bom desempenho, com pontos específicos que ainda podem ser consolidados."
    elif percentage >= 45:
        summary = "Aprendizagem em desenvolvimento. Recomenda-se revisar os pontos indicados."
    else:
        summary = "São necessárias novas oportunidades de aprendizagem e feedback orientado."
    return {
        "summary": summary,
        "percentage": round(percentage, 2),
        "strengths": list(strengths),
        "improvement_points": list(improvement_points),
        "next_steps": list(next_steps),
        "notice": "Feedback formativo; a decisão pedagógica final permanece sob responsabilidade humana.",
    }


def appeal_is_within_deadline(
    *, published_at: datetime | None, appeal_days: int, now: datetime | None = None
) -> bool:
    if published_at is None:
        return False
    current = now or datetime.now(UTC)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    elapsed_days = (current - published_at).total_seconds() / 86400
    return 0 <= elapsed_days <= max(appeal_days, 0)


def score_snapshot(*, score: float | None, maximum_score: float, correction_type: str | None) -> dict[str, Any]:
    return {
        "score": score,
        "maximum_score": maximum_score,
        "correction_type": correction_type,
        "captured_at": datetime.now(UTC).isoformat(),
    }
