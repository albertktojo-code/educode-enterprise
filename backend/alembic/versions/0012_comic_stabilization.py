"""Comic stabilization, optimistic concurrency and canvas readiness.

Revision ID: 0012_comic_stabilization
Revises: 0011_comic_review_control
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_comic_stabilization"
down_revision: str | None = "0011_comic_review_control"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "generated_comics",
        sa.Column("edit_revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "generated_comics",
        sa.Column("last_editor_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "generated_comics",
        sa.Column("last_editor_name_snapshot", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "generated_comics",
        sa.Column("last_editor_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "generated_comics",
        sa.Column(
            "canvas_readiness_status",
            sa.String(length=40),
            server_default="not_ready",
            nullable=False,
        ),
    )
    op.add_column(
        "generated_comics",
        sa.Column("canvas_readiness_checked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_generated_comics_last_editor_user_id",
        "generated_comics",
        "users",
        ["last_editor_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_generated_comics_last_editor_user_id",
        "generated_comics",
        ["last_editor_user_id"],
    )
    # PostgreSQL enum values cannot be safely removed on downgrade.
    op.execute(
        "ALTER TYPE comic_generation_run_status "
        "ADD VALUE IF NOT EXISTS 'CANCELED'"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_comics_last_editor_user_id",
        table_name="generated_comics",
    )
    op.drop_constraint(
        "fk_generated_comics_last_editor_user_id",
        "generated_comics",
        type_="foreignkey",
    )
    for column in (
        "canvas_readiness_checked_at",
        "canvas_readiness_status",
        "last_editor_at",
        "last_editor_name_snapshot",
        "last_editor_user_id",
        "edit_revision",
    ):
        op.drop_column("generated_comics", column)
