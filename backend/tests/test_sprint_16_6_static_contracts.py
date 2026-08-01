from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain():
    text = (BACKEND / "alembic/versions/0041_comic_reader_analytics.py").read_text(encoding="utf-8")
    assert 'revision: str = "0041_comic_reader_analytics"' in text
    assert 'down_revision: str | None = "0040_comic_reader_access"' in text
    assert len("0041_comic_reader_analytics") <= 32


def test_integrations_and_reuse():
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    services = (BACKEND / "app/comic_reader_analytics/services.py").read_text(encoding="utf-8")
    models = (BACKEND / "app/comic_reader_analytics/models.py").read_text(encoding="utf-8")
    assert "comic_reader_analytics_models" in registry
    assert "comic_reader_analytics_router" in router
    assert "LearningAlert" in services
    assert "BackgroundJob" in services
    assert 'comic_reader_alerts' not in models
    assert 'comic_reader_analytics_runs' not in models
