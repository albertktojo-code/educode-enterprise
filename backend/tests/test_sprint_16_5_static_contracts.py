from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain():
    text = (BACKEND / "alembic/versions/0040_comic_reader_access.py").read_text(encoding="utf-8")
    assert 'revision: str = "0040_comic_reader_access"' in text
    assert 'down_revision: str | None = "0039_comic_review_publish"' in text
    assert len("0040_comic_reader_access") <= 32


def test_model_registry_and_router():
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    assert "comic_reader_access_models" in registry
    assert "comic_reader_access_router" in router
    assert "include_router(comic_reader_access_router)" in router


def test_canonical_references_are_used():
    models = (BACKEND / "app/comic_reader_access/models.py").read_text(encoding="utf-8")
    assert "comic_editorial_releases.id" in models
    assert "question_bank_items.id" in models
    assert "material_assignments.id" in models
    assert "comic_reader_experiences" not in models
