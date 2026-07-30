from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_page_types():
    text = (
        BACKEND
        / "alembic/versions/0047_comic_cover_focus.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0047_comic_cover_focus"' in text
    assert (
        'down_revision: str | None = '
        '"0046_comic_editor_story"'
        in text
    )
    assert len("0047_comic_cover_focus") <= 32
    assert '"page_type"' in text
    assert '"content_layers"' in text
    assert '"ui_preferences"' in text
    assert "uq_hq_editor_single_cover" in text
    assert "op.create_table" not in text


def test_cover_reuses_pages_and_ai_orchestrator():
    services = (
        BACKEND
        / "app/comic_page_editor/cover_services.py"
    ).read_text(encoding="utf-8")
    assert "HQEditorPage" in services
    assert 'page_type="COVER"' in services
    assert "layout_template_id=None" in services
    assert "create_generation_request" in services
    assert 'module_name="comics"' in services
    assert "cover_generation_jobs" not in services


def test_story_distribution_only_counts_story_pages():
    services = (
        BACKEND
        / "app/comic_page_editor/story_services.py"
    ).read_text(encoding="utf-8")
    assert (
        'models.HQEditorPage.page_type == "STORY"'
        in services
    )


def test_ui_preferences_reuse_user_record():
    auth = (
        BACKEND / "app/models/auth.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/ui_preferences/router.py"
    ).read_text(encoding="utf-8")
    assert "ui_preferences" in auth
    assert "User.ui_preferences" not in router
    assert "user.ui_preferences" in router
    assert "sidebar_mode" in router
    assert "sidebar_width" in router


def test_sidebar_modes_and_focus_preferences_are_backend_contracts():
    router = (
        BACKEND / "app/ui_preferences/router.py"
    ).read_text(encoding="utf-8")
    schemas = (
        BACKEND / "app/ui_preferences/schemas.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "expanded",
        "compact",
        "hidden",
        "auto",
        "sidebar_width",
        "editor_focus_default",
        "reduce_motion",
    ):
        assert marker in router or marker in schemas
    assert "max(210, min(340, width))" in router
    assert 'width = 64 if mode == "compact"' in router


def test_cover_autosave_continuity_and_restore_endpoints_exist():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "/cover",
        "/cover/generate",
        "/continuity",
        "/autosave",
        "/autosave/latest",
        "/snapshots/",
    ):
        assert marker in router
    assert "append_domain_audit" in router


def test_activity_page_types_are_prepared_without_parallel_assessment():
    schemas = (
        BACKEND / "app/comic_page_editor/schemas.py"
    ).read_text(encoding="utf-8")
    migration = (
        BACKEND
        / "alembic/versions/0047_comic_cover_focus.py"
    ).read_text(encoding="utf-8")
    assert "ACTIVITY" in schemas
    assert "ANSWER_KEY" in schemas
    assert "page_type" in migration
    assert "activity_question_bank" not in schemas
    assert "assessment_items" not in migration
