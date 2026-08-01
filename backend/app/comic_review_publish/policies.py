from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

ALLOWED_SESSION_TRANSITIONS = {
    "DRAFT": {"OPEN", "CANCELLED"},
    "OPEN": {"IN_REVIEW", "CANCELLED"},
    "IN_REVIEW": {"CHANGES_REQUESTED", "APPROVED", "CANCELLED"},
    "CHANGES_REQUESTED": {"OPEN", "IN_REVIEW", "CANCELLED"},
    "APPROVED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
}

ALLOWED_RELEASE_TRANSITIONS = {
    "DRAFT": {"READY", "ARCHIVED"},
    "READY": {"SCHEDULED", "PUBLISHED", "ARCHIVED"},
    "SCHEDULED": {"PUBLISHED", "WITHDRAWN"},
    "PUBLISHED": {"WITHDRAWN", "ARCHIVED"},
    "WITHDRAWN": {"ARCHIVED"},
    "ARCHIVED": set(),
}


def stable_release_hash(snapshot: dict[str, Any]) -> str:
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def can_transition_review_session(current: str, target: str) -> bool:
    current = current.upper()
    target = target.upper()
    return target in ALLOWED_SESSION_TRANSITIONS.get(current, set())


def can_transition_release(current: str, target: str) -> bool:
    current = current.upper()
    target = target.upper()
    return target in ALLOWED_RELEASE_TRANSITIONS.get(current, set())


def normalize_anchor(anchor_type: str, *, page_id: Any = None, panel_id: Any = None, layer_id: Any = None) -> dict[str, Any]:
    anchor_type = anchor_type.upper()
    if anchor_type == "PAGE" and not page_id:
        raise ValueError("PAGE anchor requires page_id")
    if anchor_type == "PANEL" and not panel_id:
        raise ValueError("PANEL anchor requires panel_id")
    if anchor_type == "LAYER" and not layer_id:
        raise ValueError("LAYER anchor requires layer_id")
    return {
        "anchor_type": anchor_type,
        "page_id": str(page_id) if page_id else None,
        "panel_id": str(panel_id) if panel_id else None,
        "layer_id": str(layer_id) if layer_id else None,
    }


def evaluate_checklist(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    required = [item for item in items if item.get("required", True)]
    passed = [item for item in items if item.get("status") == "PASSED"]
    failed_required = [
        item for item in required
        if item.get("status") not in {"PASSED", "WAIVED"}
    ]
    completion = round((len(passed) / total) * 100) if total else 0
    return {
        "total": total,
        "passed": len(passed),
        "required": len(required),
        "failed_required": len(failed_required),
        "completion_percent": completion,
        "is_blocked": bool(failed_required),
    }


def approval_quorum(
    decisions: list[dict[str, Any]],
    *,
    minimum_approvals: int,
    required_roles: list[str] | None = None,
) -> dict[str, Any]:
    required_roles = [item.upper() for item in (required_roles or [])]
    approvals = [item for item in decisions if item.get("decision", "").upper() == "APPROVE"]
    blocking = [item for item in decisions if item.get("decision", "").upper() in {"REJECT", "REQUEST_CHANGES"}]
    approved_roles = {str(item.get("reviewer_role", "")).upper() for item in approvals}
    missing_roles = [role for role in required_roles if role not in approved_roles]
    return {
        "approvals": len(approvals),
        "blocking_decisions": len(blocking),
        "missing_roles": missing_roles,
        "quorum_met": len(approvals) >= minimum_approvals and not blocking and not missing_roles,
    }


def publication_readiness(
    *,
    workflow_status: str,
    unresolved_threads: int,
    open_change_requests: int,
    checklist_blocked: bool,
    release_hash: str | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    if workflow_status.upper() != "APPROVED":
        reasons.append("WORKFLOW_NOT_APPROVED")
    if unresolved_threads:
        reasons.append("UNRESOLVED_THREADS")
    if open_change_requests:
        reasons.append("OPEN_CHANGE_REQUESTS")
    if checklist_blocked:
        reasons.append("CHECKLIST_BLOCKED")
    if not release_hash:
        reasons.append("RELEASE_SNAPSHOT_MISSING")
    return {"ready": not reasons, "blocking_reasons": reasons}


def summarize_review(decisions: list[dict[str, Any]], threads: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = Counter(str(item.get("decision", "UNKNOWN")).upper() for item in decisions)
    thread_counts = Counter(str(item.get("status", "UNKNOWN")).upper() for item in threads)
    return {
        "decisions": dict(decision_counts),
        "threads": dict(thread_counts),
        "open_threads": thread_counts.get("OPEN", 0) + thread_counts.get("REOPENED", 0),
    }
