from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any, Iterable

ASSET_TYPES = {
    "adaptive_model",
    "ai_model",
    "prompt_template",
    "module_policy",
    "intervention_strategy",
    "evidence_rule",
}
RISK_TIERS = {"low", "moderate", "high", "critical"}
REVIEW_STAGES = {
    "technical",
    "pedagogical",
    "privacy",
    "safety",
    "ethics",
    "final",
}
DECISIONS = {"approved", "rejected", "changes_requested"}
ACTIVE_STATUSES = {"active"}
EXECUTION_BLOCKED_STATUSES = {
    "draft",
    "in_review",
    "changes_requested",
    "rejected",
    "review_required",
    "suspended",
    "retired",
}

REQUIRED_STAGES_BY_RISK = {
    "low": {"technical"},
    "moderate": {"technical", "pedagogical"},
    "high": {"technical", "pedagogical", "privacy", "safety"},
    "critical": {
        "technical",
        "pedagogical",
        "privacy",
        "safety",
        "ethics",
    },
}

DEFAULT_THRESHOLDS = {
    "minimum_quality_score": 0.70,
    "minimum_safety_score": 0.80,
    "minimum_effectiveness_score": 0.55,
    "minimum_fairness_score": 0.75,
    "maximum_error_rate": 0.15,
    "maximum_recurrence_rate": 0.35,
    "maximum_drift_score": 0.25,
}


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def required_stages(
    risk_tier: str,
    approval_policy: dict[str, Any] | None = None,
) -> set[str]:
    configured = (approval_policy or {}).get("required_stages")
    if configured:
        return {
            str(stage)
            for stage in configured
            if str(stage) in REVIEW_STAGES
        }
    return set(REQUIRED_STAGES_BY_RISK[risk_tier])


def required_approvals(
    risk_tier: str,
    approval_policy: dict[str, Any] | None,
    institutional_default: int,
) -> int:
    configured = (approval_policy or {}).get("minimum_approvals")
    if configured is not None:
        return max(1, min(10, int(configured)))
    risk_floor = {
        "low": 1,
        "moderate": 2,
        "high": 3,
        "critical": 4,
    }[risk_tier]
    return max(risk_floor, institutional_default)


def review_summary(
    *,
    risk_tier: str,
    approval_policy: dict[str, Any],
    reviews: Iterable[dict[str, str]],
    institutional_default: int,
) -> dict[str, Any]:
    rows = list(reviews)
    required = required_stages(risk_tier, approval_policy)
    approvals = [
        row for row in rows if row.get("decision") == "approved"
    ]
    approved_stages = {
        row.get("review_stage")
        for row in approvals
        if row.get("review_stage")
    }
    unique_approvers = {
        row.get("reviewer_user_id")
        for row in approvals
        if row.get("reviewer_user_id")
    }
    approval_count = (
        len(unique_approvers)
        if unique_approvers
        else len(approvals)
    )
    blockers = [
        row
        for row in rows
        if row.get("decision") in {"rejected", "changes_requested"}
    ]
    quorum = required_approvals(
        risk_tier,
        approval_policy,
        institutional_default,
    )
    return {
        "required_stages": sorted(required),
        "approved_stages": sorted(approved_stages),
        "missing_stages": sorted(required - approved_stages),
        "approval_count": approval_count,
        "required_approvals": quorum,
        "blocked": bool(blockers),
        "ready": (
            not blockers
            and required.issubset(approved_stages)
            and approval_count >= quorum
        ),
    }


def merged_thresholds(
    monitoring_policy: dict[str, Any] | None,
) -> dict[str, float]:
    result = dict(DEFAULT_THRESHOLDS)
    configured = (monitoring_policy or {}).get("thresholds", {})
    for key in result:
        if key in configured:
            result[key] = float(configured[key])
    return result


def threshold_breaches(
    metrics: dict[str, float | int | None],
    monitoring_policy: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    thresholds = merged_thresholds(monitoring_policy)
    checks = (
        ("quality_score", "minimum_quality_score", "minimum"),
        ("safety_score", "minimum_safety_score", "minimum"),
        ("effectiveness_score", "minimum_effectiveness_score", "minimum"),
        ("fairness_score", "minimum_fairness_score", "minimum"),
        ("error_rate", "maximum_error_rate", "maximum"),
        ("recurrence_rate", "maximum_recurrence_rate", "maximum"),
        ("drift_score", "maximum_drift_score", "maximum"),
    )
    breaches: list[dict[str, Any]] = []
    for metric_key, threshold_key, direction in checks:
        value = metrics.get(metric_key)
        if value is None:
            continue
        threshold = thresholds[threshold_key]
        violated = (
            float(value) < threshold
            if direction == "minimum"
            else float(value) > threshold
        )
        if violated:
            breaches.append(
                {
                    "metric": metric_key,
                    "value": round(float(value), 4),
                    "threshold": threshold,
                    "direction": direction,
                }
            )
    return breaches


def fairness_from_cohorts(
    values: Iterable[float],
) -> tuple[float | None, float | None]:
    rows = [float(value) for value in values]
    if len(rows) < 2:
        return None, None
    disparity = max(rows) - min(rows)
    return round(max(0.0, 1.0 - disparity), 4), round(disparity, 4)


def monitoring_period(
    period_start: date | None,
    period_end: date | None,
    lookback_days: int,
) -> tuple[date, date]:
    end = period_end or date.today()
    start = period_start or (end - timedelta(days=lookback_days))
    if end < start:
        raise ValueError("period_end deve ser igual ou posterior a period_start")
    if (end - start).days > 730:
        raise ValueError("O período não pode exceder 730 dias")
    return start, end


def documentation_completeness(
    documentation: dict[str, Any],
) -> float:
    required = (
        "summary",
        "data_sources",
        "decision_logic",
        "human_oversight",
        "known_limitations",
        "validation_evidence",
        "rollback_plan",
    )
    completed = sum(bool(documentation.get(key)) for key in required)
    return round(completed / len(required), 4)


def compare_documents(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    keys = sorted(set(left) | set(right))
    changed = [
        key for key in keys if left.get(key) != right.get(key)
    ]
    return {
        "changed_keys": changed,
        "unchanged_keys": [key for key in keys if key not in changed],
        "left_hash": canonical_hash(left),
        "right_hash": canonical_hash(right),
    }
