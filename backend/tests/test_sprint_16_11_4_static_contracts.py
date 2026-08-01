from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_single_table():
    migration = (
        BACKEND / "alembic/versions/0053_hq_learning_analytics.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0053_hq_learning_analytics"' in migration
    assert (
        'down_revision: str | None = "0052_hq_student_experience"'
        in migration
    )
    assert migration.count("op.create_table(") == 1
    assert '"hq_learning_analytics_snapshots"' in migration


def test_canonical_domains_are_reused():
    source = (
        BACKEND / "app/comic_page_editor/learning_analytics.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "AssessmentPublication",
        "AssessmentSession",
        "HQStudentExperienceState",
        "HQActivityBinding",
        "HQEditorPage",
    ):
        assert marker in source


def test_routes_exist():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    assert "/analytics/generate" in router
    assert "/analytics/latest" in router


def test_version_keeps_16_11_compatibility():
    config = (
        BACKEND / "app/core/config.py"
    ).read_text(encoding="utf-8")
    assert 'app_version: str = "0.16.11.' in config
