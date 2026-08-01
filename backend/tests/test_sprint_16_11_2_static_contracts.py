from pathlib import Path
BACKEND=Path(__file__).resolve().parents[1]
def test_migration_chain_and_single_table():
    migration=(BACKEND/"alembic/versions/0051_hq_activity_delivery.py").read_text(encoding="utf-8")
    assert 'revision: str = "0051_hq_activity_delivery"' in migration
    assert 'down_revision: str | None = "0050_hq_activity_feedback"' in migration
    assert migration.count("op.create_table(")==1
    assert '"hq_activity_delivery_links"' in migration
def test_delivery_reuses_canonical_models():
    source=(BACKEND/"app/comic_page_editor/activity_delivery.py").read_text(encoding="utf-8")
    for marker in ("AssessmentPublication","AssessmentTarget","AssessmentSession"): assert marker in source
def test_routes_exist():
    router=(BACKEND/"app/comic_page_editor/router.py").read_text(encoding="utf-8")
    for route in ("/activity-deliveries","/publish","/monitoring"): assert route in router
def test_version():
    config=(BACKEND/"app/core/config.py").read_text(encoding="utf-8")
    assert "app_version: str =" in config
