from app.comic_page_editor.editorial import (
    BUBBLE_TYPES,
    arrange_bubbles,
    bubble_conflicts,
    dialogue_suggestions,
)


def test_bubble_types_cover_editorial_variants():
    assert {
        "SPEECH",
        "THOUGHT",
        "SHOUT",
        "WHISPER",
        "NARRATION",
        "CAPTION",
        "DEVICE",
        "OFFSCREEN",
        "SOUND_EFFECT",
    }.issubset(BUBBLE_TYPES)


def test_conflicts_detect_overlap_and_excessive_text():
    conflicts = bubble_conflicts(
        layers=[
            {
                "id": "a",
                "x": 0.1,
                "y": 0.1,
                "width": 0.5,
                "height": 0.3,
                "content": "A" * 430,
            },
            {
                "id": "b",
                "x": 0.2,
                "y": 0.15,
                "width": 0.5,
                "height": 0.3,
                "content": "Olá",
            },
        ]
    )
    codes = {item["code"] for item in conflicts}
    assert "EXCESSIVE_BUBBLE_TEXT" in codes
    assert "BUBBLE_OVERLAP" in codes


def test_arrangement_preserves_ids_and_reading_order():
    arranged = arrange_bubbles(
        [
            {"id": "b", "content": "B", "reading_order": 2},
            {"id": "a", "content": "A", "reading_order": 1},
        ]
    )
    assert [item["id"] for item in arranged] == ["a", "b"]
    assert [item["reading_order"] for item in arranged] == [1, 2]


def test_dialogue_suggestions_keep_teacher_control():
    result = dialogue_suggestions(
        content="Esta é uma fala bastante longa para o balão.",
        school_year="6º ano",
        tone="natural",
    )
    assert {item["kind"] for item in result} >= {
        "SHORTEN",
        "QUESTION",
        "AGE_ADAPT",
    }
