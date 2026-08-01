from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0047_comic_cover_focus"
down_revision: str | None = "0046_comic_editor_story"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "ui_preferences",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column(
        "hq_editor_pages",
        sa.Column(
            "page_type",
            sa.String(24),
            nullable=False,
            server_default="STORY",
        ),
    )
    op.add_column(
        "hq_editor_pages",
        sa.Column(
            "content_layers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "hq_editor_pages",
        sa.Column(
            "preservation_settings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "hq_editor_pages",
        sa.Column(
            "continuity_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "hq_editor_pages",
        sa.Column(
            "cover_generation",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_hq_editor_page_type",
        "hq_editor_pages",
        ["organization_id", "comic_project_id", "page_type", "page_number"],
    )
    op.create_index(
        "uq_hq_editor_single_cover",
        "hq_editor_pages",
        ["organization_id", "comic_project_id", "page_type"],
        unique=True,
        postgresql_where=sa.text("page_type = 'COVER'"),
    )
    op.create_index(
        "uq_hq_editor_single_back_cover",
        "hq_editor_pages",
        ["organization_id", "comic_project_id", "page_type"],
        unique=True,
        postgresql_where=sa.text("page_type = 'BACK_COVER'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_hq_editor_single_back_cover",
        table_name="hq_editor_pages",
    )
    op.drop_index(
        "uq_hq_editor_single_cover",
        table_name="hq_editor_pages",
    )
    op.drop_index(
        "ix_hq_editor_page_type",
        table_name="hq_editor_pages",
    )
    op.drop_column("hq_editor_pages", "cover_generation")
    op.drop_column("hq_editor_pages", "continuity_metadata")
    op.drop_column("hq_editor_pages", "preservation_settings")
    op.drop_column("hq_editor_pages", "content_layers")
    op.drop_column("hq_editor_pages", "page_type")
    op.drop_column("users", "ui_preferences")
