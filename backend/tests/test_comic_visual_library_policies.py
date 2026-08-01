from app.comic_visual_library.policies import (
    build_batch_plan,
    calculate_batch_progress,
    compare_snapshots,
    continuity_findings,
    stable_fingerprint,
)


def test_fingerprint_is_deterministic():
    assert stable_fingerprint({"hair": "black", "eyes": "brown"}) == stable_fingerprint({"eyes": "brown", "hair": "black"})


def test_compare_character_snapshots():
    findings = compare_snapshots(
        {"hair": "black", "glasses": True},
        {"hair": "blonde", "glasses": True},
        fields=("hair", "glasses"),
    )
    assert [item["code"] for item in findings] == ["HAIR_MISMATCH"]


def test_continuity_detects_unexplained_wardrobe_change():
    previous = {"character_states": [{"character_id": "luna", "wardrobe_variant_id": "school"}]}
    current = {"character_states": [{"character_id": "luna", "wardrobe_variant_id": "lab"}]}
    findings = continuity_findings(previous, current)
    assert findings[0]["code"] == "CHARACTER_WARDROBE_VARIANT_ID_CHANGED"


def test_batch_plan_is_ordered_and_locks_are_merged():
    plan = build_batch_plan([
        {"page_id": "p2", "panel_id": "b", "page_order": 2, "panel_order": 1, "character_locks": {"wardrobe": False}},
        {"page_id": "p1", "panel_id": "a", "page_order": 1, "panel_order": 1},
    ], {"face": True, "wardrobe": True})
    assert [item["panel_id"] for item in plan] == ["a", "b"]
    assert plan[1]["character_locks"]["wardrobe"] is False


def test_batch_progress_handles_partial_completion():
    result = calculate_batch_progress(["COMPLETED", "FAILED", "COMPLETED"])
    assert result == {"total": 3, "completed": 2, "failed": 1, "progress_percent": 100, "status": "PARTIALLY_COMPLETED"}


def test_empty_batch_stays_queued():
    result = calculate_batch_progress([])
    assert result["status"] == "QUEUED"
    assert result["progress_percent"] == 0


def test_scenario_snapshot_reports_palette_change():
    findings = compare_snapshots(
        {"location": "school", "palette": "blue"},
        {"location": "school", "palette": "orange"},
        fields=("location", "palette"),
    )
    assert findings[0]["field"] == "palette"
