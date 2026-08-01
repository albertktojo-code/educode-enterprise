from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_later_migration_chain_has_only_one_0048_revision():
    migrations = list(
        (BACKEND / "alembic/versions").glob(
            "0048*"
        )
    )
    assert len(migrations) == 1
    assert migrations[0].name == "0048_comic_editorial_tools.py"
    productivity = (
        BACKEND / "app/comic_page_editor/productivity.py"
    ).read_text(encoding="utf-8")
    assert "class Productivity" not in productivity
    assert "op.create_table" not in productivity


def test_productivity_reuses_existing_pages_panels_snapshots_and_layouts():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    productivity = (
        BACKEND / "app/comic_page_editor/productivity.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "HQEditorPage",
        "HQEditorPanel",
        "HQEditorSnapshot",
        "HQLayoutTemplate",
    ):
        assert marker in router or marker in productivity
    for route in (
        "/productivity/analyze",
        "/pages/reorder-advanced",
        "/panels/reorder",
        "/snapshots/compare",
        "/save-as-layout",
    ):
        assert route in router


def test_reordering_preserves_special_pages_and_accessible_order():
    productivity = (
        BACKEND / "app/comic_page_editor/productivity.py"
    ).read_text(encoding="utf-8")
    assert 'page.page_type == "STORY"' in productivity
    assert '"reading_order": order' in productivity
    assert "INVALID_STORY_PAGE_ORDER" in productivity
    assert "INVALID_PANEL_ORDER" in productivity



def test_frontend_contract_is_represented_by_backend_routes():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    schemas = (
        BACKEND / "app/comic_page_editor/schemas.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "/productivity/analyze",
        "/pages/reorder-advanced",
        "/panels/reorder",
        "/save-as-layout",
        "ProductivityAnalysisRequest",
        "AdvancedPageReorderRequest",
        "PanelReadingOrderRequest",
        "CustomLayoutFromPageRequest",
    ):
        assert marker in router or marker in schemas

def test_version_setting_remains_explicit():
    config = (
        BACKEND / "app/core/config.py"
    ).read_text(encoding="utf-8")
    assert "app_version: str =" in config
    assert "0047_comic_cover_focus" not in config
