from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_single_table():
    migration = (
        BACKEND / "alembic/versions/0050_hq_activity_feedback.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0050_hq_activity_feedback"' in migration
    assert (
        'down_revision: str | None = "0049_hq_interactive_activities"'
        in migration
    )
    assert migration.count("op.create_table(") == 1
    assert '"hq_activity_feedback_profiles"' in migration


def test_assessment_review_rubrics_are_reused():
    service = (
        BACKEND / "app/comic_page_editor/activity_feedback.py"
    ).read_text(encoding="utf-8")
    assert "ReviewRubric" in service
    assert "ReviewRubricVersion" in service
    assert "assessment_review.models" in service
    assert "class Rubric" not in service


def test_feedback_routes_and_human_review_exist():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    for route in (
        "/feedback-profile",
        "/feedback-profile/approve",
        "/correction/simulate",
    ):
        assert route in router
    assert "append_domain_audit" in router


def test_objective_and_discursive_modes_are_supported():
    service = (
        BACKEND / "app/comic_page_editor/activity_feedback.py"
    ).read_text(encoding="utf-8")
    assert "OBJECTIVE_TYPES" in service
    assert '"REQUIRES_REVIEW"' in service
    assert '"AUTOMATIC"' in (
        BACKEND / "alembic/versions/0050_hq_activity_feedback.py"
    ).read_text(encoding="utf-8")


def test_version_is_16_11_1():
    config = (
        BACKEND / "app/core/config.py"
    ).read_text(encoding="utf-8")
    assert "app_version: str =" in config
