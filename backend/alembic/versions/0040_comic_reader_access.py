from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0040_comic_reader_access"
down_revision: str | None = "0039_comic_review_publish"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def uid(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "comic_reader_preferences",
        uid("id"), uid("organization_id"), uid("user_id"),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source", sa.String(30), nullable=False, server_default="USER"),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_comic_reader_preference_user"),
    )
    op.create_table(
        "comic_reading_checkpoints",
        uid("id"), uid("organization_id"), uid("release_id"), uid("user_id"),
        sa.Column("page_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("panel_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completed_panels", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reader_mode", sa.String(24), nullable=False, server_default="PAGE"),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "release_id", "user_id", name="uq_comic_reading_checkpoint"),
    )
    op.create_index("ix_comic_reading_checkpoint_progress", "comic_reading_checkpoints", ["organization_id", "user_id", "updated_at"])
    op.create_table(
        "comic_reader_bookmarks",
        uid("id"), uid("organization_id"), uid("release_id"), uid("user_id"),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("panel_number", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(180), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_comic_reader_bookmarks_user", "comic_reader_bookmarks", ["organization_id", "user_id", "release_id"])
    op.create_table(
        "comic_narration_tracks",
        uid("id"), uid("organization_id"), uid("release_id"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("panel_number", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="BROWSER_TTS"),
        sa.Column("language", sa.String(20), nullable=False, server_default="pt-BR"),
        sa.Column("transcript", sa.Text(), nullable=False),
        uid("audio_asset_id", True),
        sa.Column("audio_url", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("voice_settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="READY"),
        uid("created_by_user_id"),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audio_asset_id"], ["institutional_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_comic_narration_release", "comic_narration_tracks", ["organization_id", "release_id", "language", "page_number", "panel_number"])
    op.create_table(
        "comic_glossary_terms",
        uid("id"), uid("organization_id"), uid("release_id"),
        sa.Column("term", sa.String(120), nullable=False),
        sa.Column("normalized_term", sa.String(120), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("simplified_definition", sa.Text(), nullable=False, server_default=""),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("panel_number", sa.Integer(), nullable=True),
        sa.Column("pronunciation", sa.String(500), nullable=False, server_default=""),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uid("created_by_user_id"),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "release_id", "normalized_term", name="uq_comic_glossary_term"),
    )
    op.create_index("ix_comic_glossary_release", "comic_glossary_terms", ["organization_id", "release_id", "page_number", "panel_number"])
    op.create_table(
        "comic_presentation_sessions",
        uid("id"), uid("organization_id"), uid("release_id"), uid("presenter_user_id"),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("join_code", sa.String(20), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("current_page", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_panel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reveal_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allow_audience_join", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sync_audience", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reveal_mode", sa.String(30), nullable=False, server_default="PANEL"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("presenter_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["presenter_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "join_code", name="uq_comic_presentation_join_code"),
    )
    op.create_index("ix_comic_presentation_status", "comic_presentation_sessions", ["organization_id", "status", "updated_at"])
    op.create_table(
        "comic_presentation_audience",
        uid("id"), uid("organization_id"), uid("presentation_session_id"), uid("user_id"),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="JOINED"),
        sa.Column("local_preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["presentation_session_id"], ["comic_presentation_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "presentation_session_id", "user_id", name="uq_comic_presentation_audience"),
    )
    op.create_index("ix_comic_presentation_audience_status", "comic_presentation_audience", ["organization_id", "presentation_session_id", "status"])
    op.create_table(
        "comic_embedded_assessment_links",
        uid("id"), uid("organization_id"), uid("release_id"), uid("question_bank_item_id"),
        uid("assignment_id", True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("panel_number", sa.Integer(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reveal_rule", sa.String(40), nullable=False, server_default="ON_REACH"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uid("created_by_user_id"),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_bank_item_id"], ["question_bank_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_comic_embedded_assessment_position", "comic_embedded_assessment_links", ["organization_id", "release_id", "page_number", "panel_number", "display_order"])


def downgrade() -> None:
    for table_name in (
        "comic_embedded_assessment_links",
        "comic_presentation_audience",
        "comic_presentation_sessions",
        "comic_glossary_terms",
        "comic_narration_tracks",
        "comic_reader_bookmarks",
        "comic_reading_checkpoints",
        "comic_reader_preferences",
    ):
        op.drop_table(table_name)
