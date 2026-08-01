from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Mapping
from typing import Any

from alembic.operations import ops


def _freeze(value: Any) -> Hashable:
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return str(value)


def _index_signature(
    operation: ops.CreateIndexOp | ops.DropIndexOp,
) -> tuple[Hashable, ...]:
    index = operation.to_index()
    columns = tuple(
        getattr(expression, "name", None) or str(expression)
        for expression in index.expressions
    )
    dialect_options = tuple(
        sorted(
            (str(key), _freeze(value))
            for key, value in index.dialect_kwargs.items()
        )
    )
    return (
        index.table.schema,
        index.table.name,
        columns,
        bool(index.unique),
        dialect_options,
    )


def normalize_semantic_index_renames(container: ops.OpContainer) -> int:
    """Remove index drop/create pairs that differ only by name.

    The installed migration chain contains explicit, shortened PostgreSQL index
    names while many ORM columns use ``index=True``. Alembic otherwise proposes
    destructive renames for structurally identical indexes. Real additions,
    removals and changes to columns, uniqueness or dialect options remain in
    the operation tree.
    """

    removed = 0
    retained_children: list[ops.MigrateOperation] = []
    for operation in container.ops:
        if isinstance(operation, ops.OpContainer):
            removed += normalize_semantic_index_renames(operation)
            if not operation.ops:
                continue
        retained_children.append(operation)
    container.ops = retained_children

    creates: dict[tuple[Hashable, ...], list[ops.CreateIndexOp]] = defaultdict(list)
    drops: dict[tuple[Hashable, ...], list[ops.DropIndexOp]] = defaultdict(list)
    for operation in container.ops:
        if isinstance(operation, ops.CreateIndexOp):
            creates[_index_signature(operation)].append(operation)
        elif isinstance(operation, ops.DropIndexOp):
            drops[_index_signature(operation)].append(operation)

    discarded: set[int] = set()
    for signature in creates.keys() & drops.keys():
        create_operations = creates[signature]
        drop_operations = drops[signature]
        for create_operation, drop_operation in zip(
            create_operations,
            drop_operations,
            strict=False,
        ):
            if create_operation.index_name == drop_operation.index_name:
                continue
            discarded.add(id(create_operation))
            discarded.add(id(drop_operation))
            removed += 2

    if discarded:
        container.ops = [
            operation for operation in container.ops if id(operation) not in discarded
        ]
    return removed


def process_revision_directives(
    _context: Any,
    _revision: Any,
    directives: list[Any],
) -> None:
    """Apply conservative drift normalization to Alembic autogeneration."""

    for directive in directives:
        for upgrade_operations in directive.upgrade_ops_list:
            normalize_semantic_index_renames(upgrade_operations)
        for downgrade_operations in directive.downgrade_ops_list:
            normalize_semantic_index_renames(downgrade_operations)
