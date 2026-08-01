from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0048_comic_editorial_tools"
down_revision: str | None = "0047_comic_cover_focus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hq_panel_text_layers",
        sa.Column(
            "bubble_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "hq_panel_text_layers",
        sa.Column(
            "accessibility_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "hq_panel_text_layers",
        sa.Column(
            "review_status",
            sa.String(24),
            nullable=False,
            server_default="DRAFT",
        ),
    )
    op.add_column(
        "hq_panel_text_layers",
        sa.Column(
            "linked_character_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_table(
        "hq_editorial_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "comic_project_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "target_type",
            sa.String(24),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(24),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column(
            "priority",
            sa.String(16),
            nullable=False,
            server_default="NORMAL",
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "resolved_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "target_type IN ('PROJECT','PAGE','PANEL','TEXT_LAYER','COVER')",
            name="ck_hq_editorial_comment_target_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN','IN_REVIEW','RESOLVED','REOPENED')",
            name="ck_hq_editorial_comment_status",
        ),
        sa.CheckConstraint(
            "priority IN ('LOW','NORMAL','HIGH','CRITICAL')",
            name="ck_hq_editorial_comment_priority",
        ),
    )
    op.create_index(
        "ix_hq_editorial_comments_project_status",
        "hq_editorial_comments",
        ["organization_id", "comic_project_id", "status", "created_at"],
    )
    op.create_index(
        "ix_hq_editorial_comments_target",
        "hq_editorial_comments",
        ["organization_id", "target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hq_editorial_comments_target",
        table_name="hq_editorial_comments",
    )
    op.drop_index(
        "ix_hq_editorial_comments_project_status",
        table_name="hq_editorial_comments",
    )
    op.drop_table("hq_editorial_comments")
    op.drop_column("hq_panel_text_layers", "linked_character_id")
    op.drop_column("hq_panel_text_layers", "review_status")
    op.drop_column("hq_panel_text_layers", "accessibility_metadata")
    op.drop_column("hq_panel_text_layers", "bubble_metadata")
