"""Sprint 16.3 - visual consistency and reusable comic assets.

Revision ID: 0038_comic_visual_library
Revises: 0037_comic_layout_studio
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0038_comic_visual_library"
down_revision: str | None = "0037_comic_layout_studio"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "comic_visual_libraries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("owner_user_id", UUID),
        sa.Column("comic_project_id", UUID),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("scope", sa.String(24), nullable=False, server_default="PERSONAL"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "code", name="uq_comic_visual_library_code"),
    )
    op.create_index("ix_comic_visual_libraries_scope", "comic_visual_libraries", ["organization_id", "scope", "status"])

    op.create_table(
        "comic_characters",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("library_id", UUID, nullable=False),
        sa.Column("origin_comic_project_id", UUID),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("biography", sa.Text(), nullable=False, server_default=""),
        sa.Column("personality", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("identity_profile", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("default_wardrobe", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("visual_style", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prompt_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_assets", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("identity_fingerprint", sa.String(64), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "library_id", "slug", name="uq_comic_character_slug"),
    )
    op.create_index("ix_comic_characters_filter", "comic_characters", ["organization_id", "library_id", "status"])

    op.create_table(
        "comic_character_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("character_id", UUID, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("identity_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "character_id", "version_number", name="uq_comic_character_version"),
    )
    op.create_index("ix_comic_character_versions_character", "comic_character_versions", ["organization_id", "character_id", "version_number"])

    op.create_table(
        "comic_character_variants",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("character_id", UUID, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("wardrobe", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expression", sa.String(80)),
        sa.Column("pose", sa.String(120)),
        sa.Column("accessories", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("prompt_overrides", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reference_assets", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "character_id", "code", name="uq_comic_character_variant_code"),
    )
    op.create_index("ix_comic_character_variants_character", "comic_character_variants", ["organization_id", "character_id", "status"])

    op.create_table(
        "comic_scenarios",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("library_id", UUID, nullable=False),
        sa.Column("origin_comic_project_id", UUID),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("location_profile", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("lighting_profile", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("required_objects", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("visual_style", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prompt_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("reference_assets", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("identity_fingerprint", sa.String(64), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "library_id", "slug", name="uq_comic_scenario_slug"),
    )
    op.create_index("ix_comic_scenarios_filter", "comic_scenarios", ["organization_id", "library_id", "status"])

    op.create_table(
        "comic_scenario_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("scenario_id", UUID, nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("identity_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "scenario_id", "version_number", name="uq_comic_scenario_version"),
    )
    op.create_index("ix_comic_scenario_versions_scenario", "comic_scenario_versions", ["organization_id", "scenario_id", "version_number"])

    op.create_table(
        "comic_continuity_records",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("comic_project_id", UUID, nullable=False),
        sa.Column("page_id", UUID, nullable=False),
        sa.Column("panel_id", UUID, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(180)),
        sa.Column("time_of_day", sa.String(80)),
        sa.Column("weather", sa.String(80)),
        sa.Column("character_states", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("important_objects", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("narrative_state", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("previous_panel_id", UUID),
        sa.Column("next_panel_id", UUID),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "comic_project_id", "page_id", "panel_id", name="uq_comic_continuity_panel"),
    )
    op.create_index("ix_comic_continuity_sequence", "comic_continuity_records", ["organization_id", "comic_project_id", "sequence_number"])

    op.create_table(
        "comic_consistency_checks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("comic_project_id", UUID, nullable=False),
        sa.Column("page_id", UUID),
        sa.Column("panel_id", UUID),
        sa.Column("entity_type", sa.String(36), nullable=False),
        sa.Column("entity_id", UUID),
        sa.Column("check_code", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="WARNING"),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expected_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("observed_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolution", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("detected_by", sa.String(24), nullable=False, server_default="RULE"),
        sa.Column("resolved_by_user_id", UUID),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_comic_consistency_checks_project", "comic_consistency_checks", ["organization_id", "comic_project_id", "status", "severity"])

    op.create_table(
        "comic_generation_batches",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("comic_project_id", UUID, nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("selection_mode", sa.String(24), nullable=False, server_default="PENDING_ONLY"),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lock_policy", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("generation_settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("requested_by_user_id", UUID, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_comic_generation_batches_project", "comic_generation_batches", ["organization_id", "comic_project_id", "status"])

    op.create_table(
        "comic_generation_batch_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("batch_id", UUID, nullable=False),
        sa.Column("page_id", UUID, nullable=False),
        sa.Column("panel_id", UUID, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column("character_locks", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scenario_locks", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("prompt_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_asset_reference", sa.Text()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "batch_id", "panel_id", name="uq_comic_generation_batch_panel"),
    )
    op.create_index("ix_comic_generation_batch_items", "comic_generation_batch_items", ["organization_id", "batch_id", "status"])


def downgrade() -> None:
    for table in (
        "comic_generation_batch_items",
        "comic_generation_batches",
        "comic_consistency_checks",
        "comic_continuity_records",
        "comic_scenario_versions",
        "comic_scenarios",
        "comic_character_variants",
        "comic_character_versions",
        "comic_characters",
        "comic_visual_libraries",
    ):
        op.drop_table(table)
