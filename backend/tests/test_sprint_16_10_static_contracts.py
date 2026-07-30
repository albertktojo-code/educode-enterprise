from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_story_table_and_seven_system_grids():
    text = (
        BACKEND / "alembic/versions/0046_comic_editor_story.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0046_comic_editor_story"' in text
    assert (
        'down_revision: str | None = "0045_institutional_governance"'
        in text
    )
    assert len("0046_comic_editor_story") <= 32
    assert text.count('"code": "GRID_') == 7
    assert 'op.create_table(\n        "hq_story_plans"' in text
    assert "hq_story_plan_versions" not in text
    assert "comic_generation_jobs" not in text
    assert "op.bulk_insert(" in text
    assert "CAST(:grid_definition AS jsonb)" not in text
    assert "INSERT INTO hq_layout_templates" not in text


def test_story_plan_extends_existing_editor_domain():
    models = (
        BACKEND / "app/comic_page_editor/models.py"
    ).read_text(encoding="utf-8")
    assert 'class HQStoryPlan' in models
    assert '__tablename__ = "hq_story_plans"' in models
    assert '__tablename__ = "hq_editor_pages"' in models
    assert '__tablename__ = "hq_editor_panels"' in models


def test_story_distribution_uses_actual_page_and_panel_capacity():
    services = (
        BACKEND / "app/comic_page_editor/story_services.py"
    ).read_text(encoding="utf-8")
    policies = (
        BACKEND / "app/comic_page_editor/policies.py"
    ).read_text(encoding="utf-8")
    assert "page_capacities" in services
    assert "build_story_distribution" in services
    assert "zip(" in services
    assert "strict=True" in services
    assert "recommended_layout_code" in policies
    assert "STAGE_LAYOUTS" in policies


def test_ai_generation_reuses_canonical_orchestrator():
    services = (
        BACKEND / "app/comic_page_editor/story_services.py"
    ).read_text(encoding="utf-8")
    assert "create_generation_request" in services
    assert 'module_name="comics"' in services
    assert 'action_name="generate_script"' in services
    assert "AIGenerationCreate" in services
    assert "new_ai_jobs" not in services


def test_grid_change_preserves_existing_panel_ids_and_text_layers():
    services = (
        BACKEND / "app/comic_page_editor/story_services.py"
    ).read_text(encoding="utf-8")
    assert "current[index]" in services
    assert "HQPanelTextLayer" in services
    assert "preserve_content" in services
    apply_block = services.split(
        "async def apply_layout", 1
    )[1].split("async def ensure_story_pages", 1)[0]
    assert "delete(models.HQEditorPanel)" in apply_block
    assert "excess_ids" in apply_block
    assert "delete(models.HQEditorPanel).where" in apply_block


def test_router_exposes_manual_ai_distribution_and_layout_endpoints():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    for route in (
        '@router.get("/preservation-options")',
        '@router.get("/projects/{project_id}/story-plan")',
        '@router.put("/projects/{project_id}/story-plan")',
        '@router.post("/projects/{project_id}/story-plan/generate")',
        '@router.post("/projects/{project_id}/story-plan/distribute")',
        '@router.post("/pages/{page_id}/layout"',
    ):
        assert route in router
    assert "append_domain_audit" in router


def test_version_and_editor_settings_are_current():
    config = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")
    assert "app_version: str =" in config
    assert "comic_editor_max_pages" in config
    assert "comic_editor_default_zoom" in config
    assert "comic_editor_ai_story_review_required" in config
