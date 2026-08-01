"""Add canonical audiovisual anime authoring and render history.

Revision ID: 0056_anime_audiovisual
Revises: 0055_delivery_source_invariant
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0056_anime_audiovisual"
down_revision: str | None = "0055_delivery_source_invariant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.create_table(
        "anime_projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=True),
        sa.Column("rag_context_id", sa.Uuid(), nullable=True),
        sa.Column("teacher_studio_draft_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("synopsis", sa.Text(), server_default="", nullable=False),
        sa.Column("style_preset_code", sa.String(80), server_default="anime_school", nullable=False),
        sa.Column("aspect_ratio", sa.String(12), server_default="16:9", nullable=False),
        sa.Column("width", sa.Integer(), server_default="1920", nullable=False),
        sa.Column("height", sa.Integer(), server_default="1080", nullable=False),
        sa.Column("fps", sa.Integer(), server_default="24", nullable=False),
        sa.Column("language", sa.String(20), server_default="pt-BR", nullable=False),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("accessibility_options", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("production_notes", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("width BETWEEN 320 AND 7680", name="ck_anime_project_width"),
        sa.CheckConstraint("height BETWEEN 240 AND 4320", name="ck_anime_project_height"),
        sa.CheckConstraint("fps BETWEEN 1 AND 60", name="ck_anime_project_fps"),
        sa.CheckConstraint("revision >= 1", name="ck_anime_project_revision"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["generation_project_id"], ["generation_projects.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["teacher_studio_draft_id"], ["teacher_studio_drafts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_anime_projects_organization_id", "anime_projects", ["organization_id"])
    op.create_index("ix_anime_projects_generation_project_id", "anime_projects", ["generation_project_id"])
    op.create_index("ix_anime_projects_rag_context_id", "anime_projects", ["rag_context_id"])
    op.create_index("ix_anime_projects_teacher_studio_draft_id", "anime_projects", ["teacher_studio_draft_id"])
    op.create_index("ix_anime_projects_created_by_user_id", "anime_projects", ["created_by_user_id"])
    op.create_index("ix_anime_projects_status", "anime_projects", ["status"])
    op.create_index("ix_anime_projects_org_status", "anime_projects", ["organization_id", "status"])

    op.create_table(
        "anime_scenes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("duration_ms", sa.Integer(), server_default="5000", nullable=False),
        sa.Column("visual_asset_file_id", sa.Uuid(), nullable=True),
        sa.Column("source_comic_page_id", sa.Uuid(), nullable=True),
        sa.Column("source_comic_panel_id", sa.Uuid(), nullable=True),
        sa.Column("screenplay_text", sa.Text(), server_default="", nullable=False),
        sa.Column("visual_prompt", sa.Text(), server_default="", nullable=False),
        sa.Column("negative_prompt", sa.Text(), server_default="", nullable=False),
        sa.Column("camera_settings", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("transition_settings", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("continuity_data", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("pedagogical_metadata", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("duration_ms BETWEEN 500 AND 600000", name="ck_anime_scene_duration"),
        sa.CheckConstraint("revision >= 1", name="ck_anime_scene_revision"),
        sa.UniqueConstraint("project_id", "position", name="uq_anime_scene_position"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["anime_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["visual_asset_file_id"], ["institutional_asset_files.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_comic_page_id"], ["comic_pages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_comic_panel_id"], ["comic_panels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    for name in (
        "organization_id",
        "project_id",
        "visual_asset_file_id",
        "source_comic_page_id",
        "source_comic_panel_id",
        "status",
    ):
        op.create_index(f"ix_anime_scenes_{name}", "anime_scenes", [name])
    op.create_index("ix_anime_scenes_org_project", "anime_scenes", ["organization_id", "project_id"])

    op.create_table(
        "anime_audio_tracks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("track_kind", sa.String(32), nullable=False),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("language", sa.String(20), server_default="pt-BR", nullable=False),
        sa.Column("asset_file_id", sa.Uuid(), nullable=True),
        sa.Column("transcript", sa.Text(), server_default="", nullable=False),
        sa.Column("speaker", sa.String(160), server_default="", nullable=False),
        sa.Column("start_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("trim_start_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("volume", sa.Float(), server_default="1", nullable=False),
        sa.Column("fade_in_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fade_out_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_muted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("voice_settings", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("start_ms >= 0", name="ck_anime_audio_start"),
        sa.CheckConstraint("duration_ms IS NULL OR duration_ms > 0", name="ck_anime_audio_duration"),
        sa.CheckConstraint("trim_start_ms >= 0", name="ck_anime_audio_trim"),
        sa.CheckConstraint("volume BETWEEN 0 AND 2", name="ck_anime_audio_volume"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["anime_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["anime_scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_file_id"], ["institutional_asset_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for name in ("organization_id", "project_id", "scene_id", "track_kind", "asset_file_id", "status"):
        op.create_index(f"ix_anime_audio_tracks_{name}", "anime_audio_tracks", [name])
    op.create_index("ix_anime_audio_org_project", "anime_audio_tracks", ["organization_id", "project_id"])

    op.create_table(
        "anime_caption_cues",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("scene_id", sa.Uuid(), nullable=True),
        sa.Column("language", sa.String(20), server_default="pt-BR", nullable=False),
        sa.Column("cue_order", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker", sa.String(160), server_default="", nullable=False),
        sa.Column("cue_kind", sa.String(32), server_default="dialogue", nullable=False),
        sa.Column("accessibility_metadata", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("start_ms >= 0", name="ck_anime_caption_start"),
        sa.CheckConstraint("end_ms > start_ms", name="ck_anime_caption_end"),
        sa.UniqueConstraint("project_id", "language", "cue_order", name="uq_anime_caption_order"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["anime_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["anime_scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for name in ("organization_id", "project_id", "scene_id"):
        op.create_index(f"ix_anime_caption_cues_{name}", "anime_caption_cues", [name])
    op.create_index("ix_anime_caption_org_project", "anime_caption_cues", ["organization_id", "project_id"])

    op.create_table(
        "anime_renders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("background_job_id", sa.Uuid(), nullable=True),
        sa.Column("output_asset_id", sa.Uuid(), nullable=True),
        sa.Column("output_asset_file_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("format", sa.String(20), server_default="mp4", nullable=False),
        sa.Column("video_codec", sa.String(30), server_default="h264", nullable=False),
        sa.Column("audio_codec", sa.String(30), server_default="aac", nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("render_settings", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("source_snapshot", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("manifest_checksum", sa.String(64), server_default="", nullable=False),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("review_decision", sa.String(32), server_default="pending", nullable=False),
        sa.Column("review_notes", sa.Text(), server_default="", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("revision >= 1", name="ck_anime_render_revision"),
        sa.UniqueConstraint("project_id", "revision", name="uq_anime_render_revision"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["anime_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["background_job_id"], ["background_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["output_asset_id"], ["institutional_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["output_asset_file_id"], ["institutional_asset_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    for name in (
        "organization_id",
        "project_id",
        "background_job_id",
        "output_asset_id",
        "output_asset_file_id",
        "status",
        "requested_by_user_id",
    ):
        op.create_index(f"ix_anime_renders_{name}", "anime_renders", [name])
    op.create_index("ix_anime_renders_org_status", "anime_renders", ["organization_id", "status"])


def downgrade() -> None:
    op.drop_table("anime_renders")
    op.drop_table("anime_caption_cues")
    op.drop_table("anime_audio_tracks")
    op.drop_table("anime_scenes")
    op.drop_table("anime_projects")
