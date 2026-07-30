"""Storyboard derivado, pré-visualização e revisão granular.

Revision ID: 0015_storyboard_preview
Revises: 0014_learning_delivery
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_storyboard_preview"
down_revision: str | None = "0014_learning_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

preview_review_status = postgresql.ENUM(
    "NOT_REVIEWED",
    "IN_REVIEW",
    "CHANGES_REQUESTED",
    "APPROVED",
    "LOCKED",
    name="comic_preview_review_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    preview_review_status.create(bind, checkfirst=True)

    op.add_column(
        "generated_comics",
        sa.Column(
            "preview_status",
            preview_review_status,
            server_default="NOT_REVIEWED",
            nullable=False,
        ),
    )
    op.add_column(
        "generated_comics",
        sa.Column("preview_checked_at", sa.DateTime(timezone=True), nullable=True),
    )

    for table_name in ("comic_pages", "comic_panels"):
        op.add_column(
            table_name,
            sa.Column(
                "preview_review_status",
                preview_review_status,
                server_default="NOT_REVIEWED",
                nullable=False,
            ),
        )
        op.add_column(
            table_name,
            sa.Column("preview_reviewed_by_user_id", sa.Uuid(), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("preview_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("preview_review_notes", sa.Text(), nullable=True),
        )
        op.create_foreign_key(
            f"fk_{table_name}_preview_reviewer",
            table_name,
            "users",
            ["preview_reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            f"ix_{table_name}_preview_reviewed_by_user_id",
            table_name,
            ["preview_reviewed_by_user_id"],
        )

    op.add_column("comic_review_comments", sa.Column("anchor_x", sa.Float(), nullable=True))
    op.add_column("comic_review_comments", sa.Column("anchor_y", sa.Float(), nullable=True))
    op.add_column(
        "comic_review_comments",
        sa.Column("priority", sa.String(length=24), server_default="normal", nullable=False),
    )
    op.create_check_constraint(
        "ck_comic_review_comment_anchor_x",
        "comic_review_comments",
        "anchor_x IS NULL OR (anchor_x >= 0 AND anchor_x <= 100)",
    )
    op.create_check_constraint(
        "ck_comic_review_comment_anchor_y",
        "comic_review_comments",
        "anchor_y IS NULL OR (anchor_y >= 0 AND anchor_y <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_comic_review_comment_anchor_y", "comic_review_comments", type_="check")
    op.drop_constraint("ck_comic_review_comment_anchor_x", "comic_review_comments", type_="check")
    op.drop_column("comic_review_comments", "priority")
    op.drop_column("comic_review_comments", "anchor_y")
    op.drop_column("comic_review_comments", "anchor_x")

    for table_name in ("comic_panels", "comic_pages"):
        op.drop_index(f"ix_{table_name}_preview_reviewed_by_user_id", table_name=table_name)
        op.drop_constraint(f"fk_{table_name}_preview_reviewer", table_name, type_="foreignkey")
        op.drop_column(table_name, "preview_review_notes")
        op.drop_column(table_name, "preview_reviewed_at")
        op.drop_column(table_name, "preview_reviewed_by_user_id")
        op.drop_column(table_name, "preview_review_status")

    op.drop_column("generated_comics", "preview_checked_at")
    op.drop_column("generated_comics", "preview_status")
    preview_review_status.drop(op.get_bind(), checkfirst=True)
