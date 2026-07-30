from __future__ import annotations

import hashlib
import json
from typing import Any

IDENTITY_FIELDS = ("face", "hair", "eyes", "age_group", "body_type", "skin_tone", "glasses")
SCENARIO_FIELDS = ("location", "architecture", "key_objects", "palette", "lighting")


def stable_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def character_identity_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {field: profile.get(field) for field in IDENTITY_FIELDS if field in profile}


def scenario_identity_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {field: profile.get(field) for field in SCENARIO_FIELDS if field in profile}


def compare_snapshots(expected: dict[str, Any], observed: dict[str, Any], *, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for field in fields:
        expected_value = expected.get(field)
        observed_value = observed.get(field)
        if expected_value is None or observed_value is None:
            continue
        if expected_value != observed_value:
            findings.append({
                "code": f"{field.upper()}_MISMATCH",
                "field": field,
                "expected": expected_value,
                "observed": observed_value,
                "severity": "WARNING",
            })
    return findings


def continuity_findings(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if previous.get("location") and current.get("location") and previous["location"] != current["location"]:
        if not current.get("narrative_state", {}).get("location_change_explained"):
            findings.append({"code": "UNEXPLAINED_LOCATION_CHANGE", "severity": "WARNING"})
    previous_states = {item.get("character_id"): item for item in previous.get("character_states", [])}
    for item in current.get("character_states", []):
        prior = previous_states.get(item.get("character_id"))
        if not prior:
            continue
        for field in ("wardrobe_variant_id", "glasses", "accessories"):
            if prior.get(field) != item.get(field) and not item.get("change_explained"):
                findings.append({
                    "code": f"CHARACTER_{field.upper()}_CHANGED",
                    "character_id": item.get("character_id"),
                    "severity": "WARNING",
                })
    return findings


def build_batch_plan(items: list[dict[str, Any]], default_locks: dict[str, Any]) -> list[dict[str, Any]]:
    ordered = sorted(items, key=lambda item: (item.get("page_order", 0), item.get("panel_order", 0)))
    result: list[dict[str, Any]] = []
    for index, item in enumerate(ordered, start=1):
        result.append({
            "page_id": item["page_id"],
            "panel_id": item["panel_id"],
            "sequence_number": index,
            "status": "QUEUED",
            "character_locks": {**default_locks, **item.get("character_locks", {})},
            "scenario_locks": item.get("scenario_locks", {}),
            "prompt_snapshot": item.get("prompt_snapshot", {}),
        })
    return result


def calculate_batch_progress(statuses: list[str]) -> dict[str, int | str]:
    total = len(statuses)
    completed = sum(status == "COMPLETED" for status in statuses)
    failed = sum(status == "FAILED" for status in statuses)
    progress = round(((completed + failed) / total) * 100) if total else 0
    if total and completed == total:
        status = "COMPLETED"
    elif failed and completed + failed == total:
        status = "PARTIALLY_COMPLETED"
    elif total == 0:
        status = "QUEUED"
    else:
        status = "RUNNING"
    return {"total": total, "completed": completed, "failed": failed, "progress_percent": progress, "status": status}


def can_publish_asset(status: str, scope: str, review_required: bool) -> bool:
    if scope == "INSTITUTIONAL" and review_required:
        return status == "APPROVED"
    return status in {"APPROVED", "PUBLISHED"}
