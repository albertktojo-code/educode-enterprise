from __future__ import annotations

from typing import Any

from ..enums import ApprovalStatus, ProgressionAction
from ..schemas import ProgressionEvaluationInput, ProgressionEvaluationResult


def evaluate_progression(
    conditions: dict[str, Any],
    result_action: ProgressionAction,
    requires_teacher_approval: bool,
    payload: ProgressionEvaluationInput,
) -> ProgressionEvaluationResult:
    failed: list[str] = []

    checks: list[tuple[str, bool]] = [
        (
            f"mastery_score >= {conditions.get('minimum_mastery_score', 0)}",
            payload.mastery_score >= float(conditions.get("minimum_mastery_score", 0)),
        ),
        (
            f"confidence_score >= {conditions.get('minimum_confidence', 0)}",
            payload.confidence_score >= float(conditions.get("minimum_confidence", 0)),
        ),
        (
            f"evidences_count >= {conditions.get('minimum_evidences', 0)}",
            payload.evidences_count >= int(conditions.get("minimum_evidences", 0)),
        ),
        (
            "prerequisites_met",
            payload.prerequisites_met if conditions.get("required_prerequisites", False) else True,
        ),
        (
            f"high_level_hints_used <= {conditions.get('maximum_high_level_hints', 999999)}",
            payload.high_level_hints_used <= int(conditions.get("maximum_high_level_hints", 999999)),
        ),
        (
            "review_not_due",
            not payload.review_due if conditions.get("require_no_pending_review", False) else True,
        ),
        (
            "teacher_validated",
            payload.teacher_validated if conditions.get("require_teacher_validation", False) else True,
        ),
        (
            f"recent_performance >= {conditions.get('minimum_recent_performance', 0)}",
            payload.recent_performance >= float(conditions.get("minimum_recent_performance", 0)),
        ),
    ]
    failed.extend(label for label, passed in checks if not passed)

    matched = not failed
    action = result_action if matched else ProgressionAction.MAINTAIN
    approval = (
        ApprovalStatus.PENDING
        if matched and requires_teacher_approval
        else ApprovalStatus.NOT_REQUIRED
    )
    reason = (
        "Todos os critérios da regra foram atendidos."
        if matched
        else "A regra não foi aplicada porque os seguintes critérios falharam: " + "; ".join(failed)
    )
    return ProgressionEvaluationResult(
        matched=matched,
        action=action,
        reason=reason,
        failed_conditions=failed,
        requires_teacher_approval=matched and requires_teacher_approval,
        approval_status=approval,
    )
