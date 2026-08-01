from app.comic_page_editor.student_experience import (
    combined_progress,
    next_stage,
)


def test_combined_progress_weights_reading_and_activity():
    assert combined_progress(
        reading_progress=100,
        activity_progress=50,
        reader_required=True,
    ) == 72.5


def test_activity_only_ignores_reading_weight():
    assert combined_progress(
        reading_progress=0,
        activity_progress=60,
        reader_required=False,
    ) == 60


def test_stage_requires_reading_before_activity():
    assert next_stage(
        reading_progress=80,
        activity_progress=100,
        reader_required=True,
    ) == "READING"
    assert next_stage(
        reading_progress=100,
        activity_progress=40,
        reader_required=True,
    ) == "ACTIVITY"
    assert next_stage(
        reading_progress=100,
        activity_progress=100,
        reader_required=True,
    ) == "COMPLETED"
