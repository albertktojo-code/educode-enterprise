"""Enforce the canonical source invariant for legacy delivery assignments.

Revision ID: 0055_delivery_source_invariant
Revises: 0054_delivery_model_sync
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0055_delivery_source_invariant"
down_revision: str | None = "0054_delivery_model_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_CHECK = "ck_material_assignments_exactly_one_source"
ASSESSMENT_VERSION_FK = "fk_material_assignments_assessment_version"

material_assignments = sa.table(
    "material_assignments",
    sa.column("package_id", sa.Uuid()),
    sa.column("assessment_version_id", sa.Uuid()),
)


def _invalid_source_count(bind: sa.Connection) -> int:
    invalid_source = sa.or_(
        sa.and_(
            material_assignments.c.package_id.is_(None),
            material_assignments.c.assessment_version_id.is_(None),
        ),
        sa.and_(
            material_assignments.c.package_id.is_not(None),
            material_assignments.c.assessment_version_id.is_not(None),
        ),
    )
    return int(
        bind.execute(
            sa.select(sa.func.count()).select_from(material_assignments).where(invalid_source)
        ).scalar_one()
    )


def _assessment_only_count(bind: sa.Connection) -> int:
    return int(
        bind.execute(
            sa.select(sa.func.count())
            .select_from(material_assignments)
            .where(material_assignments.c.package_id.is_(None))
        ).scalar_one()
    )


def upgrade() -> None:
    bind = op.get_bind()
    invalid_count = _invalid_source_count(bind)
    if invalid_count:
        raise RuntimeError(
            "0055 blocked: material_assignments contains "
            f"{invalid_count} row(s) without exactly one canonical source"
        )

    op.drop_constraint(
        ASSESSMENT_VERSION_FK,
        "material_assignments",
        type_="foreignkey",
    )
    op.alter_column(
        "material_assignments",
        "package_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_check_constraint(
        SOURCE_CHECK,
        "material_assignments",
        "(package_id IS NOT NULL AND assessment_version_id IS NULL) OR "
        "(package_id IS NULL AND assessment_version_id IS NOT NULL)",
    )
    op.create_foreign_key(
        ASSESSMENT_VERSION_FK,
        "material_assignments",
        "assessment_versions",
        ["assessment_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    bind = op.get_bind()
    assessment_only_count = _assessment_only_count(bind)
    if assessment_only_count:
        raise RuntimeError(
            "0055 downgrade blocked: "
            f"{assessment_only_count} assessment-only assignment(s) cannot be represented by 0054"
        )

    op.drop_constraint(
        ASSESSMENT_VERSION_FK,
        "material_assignments",
        type_="foreignkey",
    )
    op.drop_constraint(
        SOURCE_CHECK,
        "material_assignments",
        type_="check",
    )
    op.alter_column(
        "material_assignments",
        "package_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.create_foreign_key(
        ASSESSMENT_VERSION_FK,
        "material_assignments",
        "assessment_versions",
        ["assessment_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
