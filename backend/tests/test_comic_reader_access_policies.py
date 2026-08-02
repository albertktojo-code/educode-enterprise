from app.comic_reader_access.policies import (
    accessibility_summary,
    calculate_progress,
    can_transition_presentation,
    generate_join_code,
    normalize_preferences,
    validate_sequence,
)


def test_preferences_are_normalized_and_clamped():
    result = normalize_preferences(
        {
            "reader_mode": "panel",
            "font_scale": 9,
            "line_spacing": 0,
            "narration_rate": 4,
            "zoom_level": 9,
            "orientation": "landscape",
        }
    )
    assert result["reader_mode"] == "PANEL"
    assert result["font_scale"] == 2.5
    assert result["line_spacing"] == 1.0
    assert result["narration_rate"] == 2.0
    assert result["zoom_level"] == 2.5
    assert result["orientation"] == "LANDSCAPE"


def test_invalid_orientation_falls_back_to_auto():
    result = normalize_preferences({"orientation": "diagonal", "zoom_level": 0.1})
    assert result["orientation"] == "AUTO"
    assert result["zoom_level"] == 0.5


def test_progress_uses_highest_position():
    result = calculate_progress(
        current_page=2, current_panel=3, total_pages=4, total_panels=10, completed_panels=8
    )
    assert result["progress_percent"] == 80.0


def test_sequence_is_idempotent():
    assert validate_sequence(10, 10)["accepted"] is False
    assert validate_sequence(10, 11)["accepted"] is True


def test_presentation_transitions():
    assert can_transition_presentation("DRAFT", "LIVE")
    assert can_transition_presentation("LIVE", "PAUSED")
    assert not can_transition_presentation("ENDED", "LIVE")


def test_join_code_avoids_ambiguous_characters():
    code = generate_join_code()
    assert len(code) == 6
    assert not set(code).intersection(set("0O1IL"))


def test_accessibility_summary():
    result = accessibility_summary(
        [{"panels": [{"alt_text": "Cena", "audio_description": "Audio"}, {}]}]
    )
    assert result["total_panels"] == 2
    assert result["missing_alt_text"] == 1
    assert result["missing_audio_description"] == 1
