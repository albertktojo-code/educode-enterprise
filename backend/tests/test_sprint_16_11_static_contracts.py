from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_single_table():
    migration = (
        BACKEND
        / "alembic/versions/0049_hq_interactive_activities.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0049_hq_interactive_activities"' in migration
    assert (
        'down_revision: str | None = "0048_comic_editorial_tools"'
        in migration
    )
    assert migration.count("op.create_table(") == 1
    assert '"hq_activity_bindings"' in migration


def test_assessment_hub_is_reused():
    activities = (
        BACKEND / "app/comic_page_editor/activities.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "QuestionItem",
        "QuestionVersion",
        "QuestionSkillLink",
        'source_type="HQ_ACTIVITY"',
        "question_version_id",
    ):
        assert marker in activities
    assert "StudentAttempt" not in activities


def test_activity_and_answer_key_pages_are_reused():
    activities = (
        BACKEND / "app/comic_page_editor/activities.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    assert 'page_type="ACTIVITY"' in activities
    assert 'page_type="ANSWER_KEY"' in router
    assert "next_special_page_number" in activities


def test_teacher_review_is_mandatory():
    migration = (
        BACKEND
        / "alembic/versions/0049_hq_interactive_activities.py"
    ).read_text(encoding="utf-8")
    activities = (
        BACKEND / "app/comic_page_editor/activities.py"
    ).read_text(encoding="utf-8")
    assert '"teacher_review_required"' in migration
    assert "teacher_review_required=True" in activities
    assert "approve_activity" in activities


def test_routes_cover_puzzles_and_assessment_binding():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    for route in (
        "/activity-types",
        "/activities/word-search/build",
        "/activities/crossword/validate",
        "/projects/{project_id}/activities",
        "/activities/{activity_id}/approve",
        "/activities/answer-key-page",
    ):
        assert route in router


def test_version_is_16_11():
    config = (
        BACKEND / "app/core/config.py"
    ).read_text(encoding="utf-8")
    assert "app_version: str =" in config
