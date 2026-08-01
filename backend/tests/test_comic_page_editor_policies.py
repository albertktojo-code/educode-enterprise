import pytest

from app.comic_page_editor.policies import (
    apply_locked_elements,
    aspect_ratio_for_panel,
    calculate_progress,
    reorder_page_numbers,
    select_playful_message,
    stable_hash,
    validate_accessibility_payload,
    validate_grid_definition,
)


def test_grid_validation_and_aspect_ratio():
    grid = {"panels": [{"x": 0, "y": 0, "width": 0.7, "height": 0.5}, {"x": 0.7, "y": 0, "width": 0.3, "height": 0.5}]}
    assert validate_grid_definition(grid) == []
    assert aspect_ratio_for_panel(0.7, 0.5) == "4:3"
    assert aspect_ratio_for_panel(0.3, 0.5) == "9:16"


def test_invalid_grid_is_rejected():
    errors = validate_grid_definition({"panels": [{"x": 0.8, "y": 0, "width": 0.5, "height": 1}]})
    assert "PANEL_1_OUTSIDE_PAGE" in errors


def test_locked_elements_are_preserved():
    previous = {"character": "Luna", "outfit": "blue", "lighting": "day"}
    requested = {"character": "Luna 2", "outfit": "red", "lighting": "night"}
    result = apply_locked_elements(previous, requested, ["character", "outfit"])
    assert result["character"] == "Luna"
    assert result["outfit"] == "blue"
    assert result["lighting"] == "night"


def test_progress_is_weighted():
    steps = [{"status": "COMPLETED", "progress_weight": 1}, {"status": "RUNNING", "progress_weight": 3}, {"status": "PENDING", "progress_weight": 1}]
    assert calculate_progress(steps) == 50


def test_page_reorder_requires_unique_ids():
    assert reorder_page_numbers(["a", "b"]) == {"a": 1, "b": 2}
    with pytest.raises(ValueError):
        reorder_page_numbers(["a", "a"])


def test_accessibility_and_messages_are_deterministic():
    warnings = validate_accessibility_payload({"contains_image": True, "text_font_size": 12, "uses_color_only": True})
    assert "ALT_TEXT_REQUIRED" in warnings
    assert "TEXT_TOO_SMALL" in warnings
    assert select_playful_message("job", 2) == select_playful_message("job", 2)
    assert len(stable_hash({"a": 1})) == 64
