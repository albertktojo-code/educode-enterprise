from alembic.operations import ops
from sqlalchemy import Column, Index, Integer, MetaData, Table

from app.db.alembic_autogenerate import normalize_semantic_index_renames


def _index_operation_pair(
    *,
    old_name: str,
    new_name: str,
    old_unique: bool = False,
    new_unique: bool = False,
) -> tuple[ops.DropIndexOp, ops.CreateIndexOp]:
    metadata = MetaData()
    table = Table("example_records", metadata, Column("organization_id", Integer))
    old_index = Index(old_name, table.c.organization_id, unique=old_unique)
    drop_operation = ops.DropIndexOp.from_index(old_index)
    create_operation = ops.CreateIndexOp(
        new_name,
        table.name,
        [table.c.organization_id],
        unique=new_unique,
    )
    return drop_operation, create_operation


def test_normalize_semantic_index_renames_removes_name_only_pair() -> None:
    drop_operation, create_operation = _index_operation_pair(
        old_name="ix_example_org",
        new_name="ix_example_records_organization_id",
    )
    table_operations = ops.ModifyTableOps(
        "example_records",
        ops=[drop_operation, create_operation],
    )
    upgrade_operations = ops.UpgradeOps(ops=[table_operations])

    removed = normalize_semantic_index_renames(upgrade_operations)

    assert removed == 2
    assert upgrade_operations.ops == []


def test_normalize_semantic_index_renames_keeps_semantic_change() -> None:
    drop_operation, create_operation = _index_operation_pair(
        old_name="ix_example_org",
        new_name="ix_example_records_organization_id",
        old_unique=False,
        new_unique=True,
    )
    table_operations = ops.ModifyTableOps(
        "example_records",
        ops=[drop_operation, create_operation],
    )
    upgrade_operations = ops.UpgradeOps(ops=[table_operations])

    removed = normalize_semantic_index_renames(upgrade_operations)

    assert removed == 0
    assert table_operations.ops == [drop_operation, create_operation]


def test_normalize_semantic_index_renames_keeps_unpaired_addition() -> None:
    _, create_operation = _index_operation_pair(
        old_name="unused",
        new_name="ix_example_records_organization_id",
    )
    table_operations = ops.ModifyTableOps(
        "example_records",
        ops=[create_operation],
    )
    upgrade_operations = ops.UpgradeOps(ops=[table_operations])

    removed = normalize_semantic_index_renames(upgrade_operations)

    assert removed == 0
    assert table_operations.ops == [create_operation]
