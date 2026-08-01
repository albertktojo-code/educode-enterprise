from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = (
    BACKEND / "alembic/versions/0055_delivery_source_invariant.py"
).read_text(encoding="utf-8")


def test_migration_extends_the_real_head() -> None:
    assert 'revision: str = "0055_delivery_source_invariant"' in MIGRATION
    assert 'down_revision: str | None = "0054_delivery_model_sync"' in MIGRATION


def test_migration_enforces_one_source_without_creating_parallel_tables() -> None:
    assert "op.create_table(" not in MIGRATION
    assert "ck_material_assignments_exactly_one_source" in MIGRATION
    assert "package_id IS NOT NULL AND assessment_version_id IS NULL" in MIGRATION
    assert "package_id IS NULL AND assessment_version_id IS NOT NULL" in MIGRATION
    assert "ondelete=\"RESTRICT\"" in MIGRATION


def test_migration_guards_upgrade_and_lossy_downgrade() -> None:
    assert "_invalid_source_count" in MIGRATION
    assert "_assessment_only_count" in MIGRATION
    assert "0055 blocked:" in MIGRATION
    assert "0055 downgrade blocked:" in MIGRATION
