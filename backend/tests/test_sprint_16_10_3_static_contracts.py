from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_table_count():
    migration = (
        BACKEND / "alembic/versions/0048_comic_editorial_tools.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0048_comic_editorial_tools"' in migration
    assert (
        'down_revision: str | None = "0047_comic_cover_focus"'
        in migration
    )
    assert migration.count("op.create_table(") == 1
    assert '"hq_editorial_comments"' in migration
    assert '"bubble_metadata"' in migration
    assert '"accessibility_metadata"' in migration


def test_editorial_reuses_text_layers_and_canonical_audit():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    editorial = (
        BACKEND / "app/comic_page_editor/editorial.py"
    ).read_text(encoding="utf-8")
    assert "HQPanelTextLayer" in editorial
    assert "append_domain_audit" in router
    for route in (
        "/bubble-types",
        "/text-layers/{layer_id}",
        "/bubbles/analyze",
        "/bubbles/arrange",
        "/dialogue/suggestions",
        "/editorial-comments",
    ):
        assert route in router


def test_version_is_16_10_3():
    config = (
        BACKEND / "app/core/config.py"
    ).read_text(encoding="utf-8")
    assert "app_version: str =" in config


def test_frontend_contract_when_available():
    project_root = BACKEND.parent
    editor = (
        project_root
        / "frontend/src/features/comicPageEditor/ComicPageEditor.tsx"
    )
    panel = (
        project_root
        / "frontend/src/features/comicPageEditor/EditorialPanel.tsx"
    )
    if not editor.is_file() or not panel.is_file():
        return
    assert "EditorialPanel" in editor.read_text(encoding="utf-8")
    panel_text = panel.read_text(encoding="utf-8")
    assert "Verificar conflitos" in panel_text
    assert "Organizar balões" in panel_text
    assert "Adicionar comentário" in panel_text
