"""Structured comic generation, granular editor and versioning.

Revision ID: 0010_comic_generation_editor
Revises: 0009_rag_context_orchestration
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_comic_generation_editor"
down_revision: str | None = "0009_rag_context_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

comic_status = postgresql.ENUM(
    "DRAFT", "GENERATING", "IN_REVIEW", "APPROVED", "ARCHIVED",
    name="comic_status", create_type=False,
)
page_format = postgresql.ENUM(
    "A4", "SQUARE", "MOBILE", "INSTAGRAM", "PRESENTATION_16_9", "CUSTOM",
    name="comic_page_format", create_type=False,
)
page_orientation = postgresql.ENUM(
    "PORTRAIT", "LANDSCAPE", name="comic_page_orientation", create_type=False,
)
layout_mode = postgresql.ENUM(
    "TEMPLATE", "FREE", "RECOMMENDED", name="comic_layout_mode", create_type=False,
)
reading_direction = postgresql.ENUM(
    "LEFT_TO_RIGHT", "RIGHT_TO_LEFT", "TOP_TO_BOTTOM",
    name="comic_reading_direction", create_type=False,
)
panel_shape = postgresql.ENUM(
    "RECTANGLE", "SQUARE", "HORIZONTAL", "VERTICAL", "CIRCLE", "OVAL",
    "PANORAMIC", "CUSTOM", name="comic_panel_shape", create_type=False,
)
panel_size = postgresql.ENUM(
    "SMALL", "MEDIUM", "LARGE", "FULL_PAGE", "CUSTOM",
    name="comic_panel_size", create_type=False,
)
panel_status = postgresql.ENUM(
    "DRAFT", "NEEDS_REVIEW", "VALIDATED", "LOCKED",
    name="comic_panel_status", create_type=False,
)
balloon_type = postgresql.ENUM(
    "SPEECH", "THOUGHT", "SHOUT", "WHISPER", "NARRATION", "CAPTION",
    "PEDAGOGICAL", name="comic_balloon_type", create_type=False,
)
generation_scope = postgresql.ENUM(
    "COMIC", "PAGE", "PANEL", "BALLOONS", "DIALOGUE", "SCENE", "FROM_PANEL",
    name="comic_generation_scope", create_type=False,
)
generation_run_status = postgresql.ENUM(
    "PENDING", "RUNNING", "COMPLETED", "FAILED",
    name="comic_generation_run_status", create_type=False,
)
version_scope = postgresql.ENUM(
    "INITIAL", "COMIC", "PAGE", "PANEL", "BALLOON", "RESTORE",
    name="comic_version_scope", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        comic_status, page_format, page_orientation, layout_mode, reading_direction,
        panel_shape, panel_size, panel_status, balloon_type, generation_scope,
        generation_run_status, version_scope,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "generated_comics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=False),
        sa.Column("rag_context_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("synopsis", sa.Text(), server_default="", nullable=False),
        sa.Column("status", comic_status, server_default="DRAFT", nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("narrative_profile", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("layout_preferences", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("story_state", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("continuity_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("pedagogical_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generation_project_id"], ["generation_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "generation_project_id", "rag_context_id", "created_by_user_id"):
        op.create_index(f"ix_generated_comics_{column}", "generated_comics", [column])

    op.create_table(
        "comic_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=True),
        sa.Column("page_format", page_format, server_default="A4", nullable=False),
        sa.Column("orientation", page_orientation, server_default="PORTRAIT", nullable=False),
        sa.Column("layout_mode", layout_mode, server_default="TEMPLATE", nullable=False),
        sa.Column("layout_template", sa.String(length=80), server_default="grid_2x2", nullable=False),
        sa.Column("reading_direction", reading_direction, server_default="LEFT_TO_RIGHT", nullable=False),
        sa.Column("panel_count", sa.Integer(), server_default="4", nullable=False),
        sa.Column("width", sa.Float(), server_default="210", nullable=False),
        sa.Column("height", sa.Float(), server_default="297", nullable=False),
        sa.Column("margins", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comic_id", "page_number", name="uq_comic_page_number"),
    )
    op.create_index("ix_comic_pages_comic_id", "comic_pages", ["comic_id"])

    op.create_table(
        "comic_panels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Uuid(), nullable=False),
        sa.Column("panel_number", sa.Integer(), nullable=False),
        sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("shape", panel_shape, server_default="RECTANGLE", nullable=False),
        sa.Column("size_category", panel_size, server_default="MEDIUM", nullable=False),
        sa.Column("position_x", sa.Float(), server_default="0", nullable=False),
        sa.Column("position_y", sa.Float(), server_default="0", nullable=False),
        sa.Column("width", sa.Float(), server_default="48", nullable=False),
        sa.Column("height", sa.Float(), server_default="48", nullable=False),
        sa.Column("border_style", sa.String(length=40), server_default="solid", nullable=False),
        sa.Column("border_width", sa.Float(), server_default="2", nullable=False),
        sa.Column("rotation", sa.Float(), server_default="0", nullable=False),
        sa.Column("z_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_full_bleed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("clipping_mode", sa.String(length=40), server_default="cover", nullable=False),
        sa.Column("narrative_goal", sa.Text(), server_default="", nullable=False),
        sa.Column("pedagogical_goal", sa.Text(), server_default="", nullable=False),
        sa.Column("ct_pillar_codes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("scene_description", sa.Text(), server_default="", nullable=False),
        sa.Column("previous_panel_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("next_panel_hook", sa.Text(), server_default="", nullable=False),
        sa.Column("initial_state", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("final_state", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("emotion", sa.String(length=80), server_default="curiosity", nullable=False),
        sa.Column("plot_function", sa.String(length=100), server_default="development", nullable=False),
        sa.Column("continuity_notes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", panel_status, server_default="DRAFT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["comic_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "panel_number", name="uq_comic_panel_number"),
        sa.UniqueConstraint("page_id", "reading_order", name="uq_comic_panel_reading_order"),
    )
    op.create_index("ix_comic_panels_page_id", "comic_panels", ["page_id"])

    op.create_table(
        "comic_balloons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("panel_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("speaker_character_id", sa.Uuid(), nullable=True),
        sa.Column("speaker_name_snapshot", sa.String(length=160), nullable=True),
        sa.Column("balloon_type", balloon_type, server_default="SPEECH", nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("emotion", sa.String(length=80), nullable=True),
        sa.Column("responds_to_balloon_id", sa.Uuid(), nullable=True),
        sa.Column("pedagogical_function", sa.String(length=120), nullable=True),
        sa.Column("position_x", sa.Float(), server_default="10", nullable=False),
        sa.Column("position_y", sa.Float(), server_default="10", nullable=False),
        sa.Column("width", sa.Float(), server_default="40", nullable=False),
        sa.Column("height", sa.Float(), server_default="20", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["panel_id"], ["comic_panels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["speaker_character_id"], ["creative_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["responds_to_balloon_id"], ["comic_balloons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("panel_id", "sequence_number", name="uq_comic_balloon_sequence"),
    )
    for column in ("panel_id", "speaker_character_id", "responds_to_balloon_id"):
        op.create_index(f"ix_comic_balloons_{column}", "comic_balloons", [column])

    op.create_table(
        "comic_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("scope", version_scope, nullable=False),
        sa.Column("target_page_id", sa.Uuid(), nullable=True),
        sa.Column("target_panel_id", sa.Uuid(), nullable=True),
        sa.Column("target_balloon_id", sa.Uuid(), nullable=True),
        sa.Column("change_description", sa.Text(), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comic_id", "version_number", name="uq_comic_version_number"),
    )
    op.create_index("ix_comic_versions_comic_id", "comic_versions", ["comic_id"])
    op.create_index("ix_comic_versions_created_by_user_id", "comic_versions", ["created_by_user_id"])

    op.create_table(
        "comic_generation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", generation_scope, nullable=False),
        sa.Column("target_page_id", sa.Uuid(), nullable=True),
        sa.Column("target_panel_id", sa.Uuid(), nullable=True),
        sa.Column("status", generation_run_status, server_default="PENDING", nullable=False),
        sa.Column("provider", sa.String(length=80), server_default="mock", nullable=False),
        sa.Column("model", sa.String(length=120), server_default="narrative-mock-v1", nullable=False),
        sa.Column("configuration", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("result_summary", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_generation_runs_comic_id", "comic_generation_runs", ["comic_id"])
    op.create_index("ix_comic_generation_runs_requested_by_user_id", "comic_generation_runs", ["requested_by_user_id"])


def downgrade() -> None:
    for table in (
        "comic_generation_runs", "comic_versions", "comic_balloons", "comic_panels",
        "comic_pages", "generated_comics",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum_type in (
        version_scope, generation_run_status, generation_scope, balloon_type,
        panel_status, panel_size, panel_shape, reading_direction, layout_mode,
        page_orientation, page_format, comic_status,
    ):
        enum_type.drop(bind, checkfirst=True)
