from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
MIGRATION = (
    BACKEND / "alembic/versions/0054_delivery_model_sync.py"
).read_text(encoding="utf-8")


def test_migration_extends_the_real_head() -> None:
    assert 'revision: str = "0054_delivery_model_sync"' in MIGRATION
    assert 'down_revision: str | None = "0053_hq_learning_analytics"' in MIGRATION


def test_migration_only_syncs_known_legacy_delivery_tables() -> None:
    assert "op.create_table(" not in MIGRATION
    for table_name in (
        "material_assignments",
        "assignment_questions",
        "student_attempts",
    ):
        assert f'"{table_name}"' in MIGRATION


def test_migration_has_explicit_indexes_foreign_keys_and_downgrade() -> None:
    assert MIGRATION.count("op.create_foreign_key(") == 3
    assert MIGRATION.count("op.create_index(") == 3
    assert MIGRATION.count("op.drop_constraint(") == 3
    assert MIGRATION.count("op.drop_index(") == 3
    assert MIGRATION.count("op.add_column(") == 11
    assert MIGRATION.count("op.drop_column(") == 11
