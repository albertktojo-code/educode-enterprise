"""Sprint 16.1 - editor visual de paginas e grids de HQ.

Revision ID: 0036_comic_page_editor
Revises: 0035_assessment_analytics
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0036_comic_page_editor"
down_revision: str | None = "0035_assessment_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("hq_layout_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""), sa.Column("version", sa.String(24), nullable=False),
        sa.Column("panel_count", sa.Integer(), nullable=False), sa.Column("orientation", sa.String(24), nullable=False),
        sa.Column("category", sa.String(40), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("grid_definition", postgresql.JSONB(), nullable=False), sa.Column("preview_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_hq_layout_template_version"))
    op.create_index("ix_hq_layout_templates_filter", "hq_layout_templates", ["organization_id", "panel_count", "status"])
    layout_table = sa.table(
        "hq_layout_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()), sa.column("name", sa.String()), sa.column("description", sa.Text()),
        sa.column("version", sa.String()), sa.column("panel_count", sa.Integer()), sa.column("orientation", sa.String()),
        sa.column("category", sa.String()), sa.column("status", sa.String()), sa.column("is_system", sa.Boolean()),
        sa.column("is_favorite", sa.Boolean()), sa.column("grid_definition", postgresql.JSONB()),
        sa.column("preview_metadata", postgresql.JSONB()), sa.column("created_by_user_id", postgresql.UUID(as_uuid=True)),
    )
    system_user = uuid.UUID("00000000-0000-0000-0000-000000000000")
    op.bulk_insert(layout_table, [
        {"id": uuid.UUID("16010000-0000-0000-0000-000000000001"), "organization_id": None, "code": "GRID_1_FULL", "name": "Pagina inteira", "description": "Uma cena de grande impacto.", "version": "1.0.0", "panel_count": 1, "orientation": "PORTRAIT", "category": "OPENING", "status": "PUBLISHED", "is_system": True, "is_favorite": False, "grid_definition": {"gutter": 0.02, "page_margin": 0.02, "panels": [{"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0, "shape": "RECTANGLE"}]}, "preview_metadata": {}, "created_by_user_id": system_user},
        {"id": uuid.UUID("16010000-0000-0000-0000-000000000002"), "organization_id": None, "code": "GRID_2_VERTICAL", "name": "Dois quadros verticais", "description": "Dialogo ou comparacao lado a lado.", "version": "1.0.0", "panel_count": 2, "orientation": "PORTRAIT", "category": "TRADITIONAL", "status": "PUBLISHED", "is_system": True, "is_favorite": False, "grid_definition": {"gutter": 0.02, "page_margin": 0.02, "panels": [{"x": 0.0, "y": 0.0, "width": 0.49, "height": 1.0, "shape": "RECTANGLE"}, {"x": 0.51, "y": 0.0, "width": 0.49, "height": 1.0, "shape": "RECTANGLE"}]}, "preview_metadata": {}, "created_by_user_id": system_user},
        {"id": uuid.UUID("16010000-0000-0000-0000-000000000003"), "organization_id": None, "code": "GRID_3_FEATURE", "name": "Destaque e tres cenas", "description": "Grid assimetrico inspirado em paginas editoriais modernas.", "version": "1.0.0", "panel_count": 4, "orientation": "PORTRAIT", "category": "ASYMMETRIC", "status": "PUBLISHED", "is_system": True, "is_favorite": False, "grid_definition": {"gutter": 0.02, "page_margin": 0.02, "panels": [{"x": 0.0, "y": 0.0, "width": 0.66, "height": 0.5, "shape": "RECTANGLE"}, {"x": 0.67, "y": 0.0, "width": 0.33, "height": 0.5, "shape": "RECTANGLE"}, {"x": 0.0, "y": 0.51, "width": 0.33, "height": 0.49, "shape": "RECTANGLE"}, {"x": 0.34, "y": 0.51, "width": 0.66, "height": 0.49, "shape": "RECTANGLE"}]}, "preview_metadata": {}, "created_by_user_id": system_user},
        {"id": uuid.UUID("16010000-0000-0000-0000-000000000004"), "organization_id": None, "code": "GRID_4_EQUAL", "name": "Quatro quadros iguais", "description": "Sequencia regular para explicacoes passo a passo.", "version": "1.0.0", "panel_count": 4, "orientation": "PORTRAIT", "category": "TRADITIONAL", "status": "PUBLISHED", "is_system": True, "is_favorite": False, "grid_definition": {"gutter": 0.02, "page_margin": 0.02, "panels": [{"x": 0.0, "y": 0.0, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"}, {"x": 0.51, "y": 0.0, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"}, {"x": 0.0, "y": 0.51, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"}, {"x": 0.51, "y": 0.51, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"}]}, "preview_metadata": {}, "created_by_user_id": system_user},
    ])

    op.create_table("hq_editor_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("layout_template_id", postgresql.UUID(as_uuid=True)),
        sa.Column("page_number", sa.Integer(), nullable=False), sa.Column("title", sa.String(180)), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("page_width", sa.Integer(), nullable=False), sa.Column("page_height", sa.Integer(), nullable=False),
        sa.Column("background_settings", postgresql.JSONB(), nullable=False), sa.Column("accessibility_settings", postgresql.JSONB(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False), sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "comic_project_id", "page_number", name="uq_hq_editor_page_number"))
    op.create_index("ix_hq_editor_pages_project", "hq_editor_pages", ["organization_id", "comic_project_id", "page_number"])

    op.create_table("hq_editor_panels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("panel_order", sa.Integer(), nullable=False),
        sa.Column("shape", sa.String(24), nullable=False), sa.Column("x", sa.Float(), nullable=False), sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False), sa.Column("height", sa.Float(), nullable=False), sa.Column("aspect_ratio", sa.String(16), nullable=False),
        sa.Column("scene_summary", sa.Text(), nullable=False), sa.Column("visual_prompt", sa.Text(), nullable=False), sa.Column("negative_prompt", sa.Text()),
        sa.Column("image_reference", sa.Text()), sa.Column("generated_asset_reference", sa.Text()), sa.Column("generation_status", sa.String(24), nullable=False),
        sa.Column("locked_elements", postgresql.JSONB(), nullable=False), sa.Column("pedagogical_metadata", postgresql.JSONB(), nullable=False), sa.Column("accessibility_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "page_id", "panel_order", name="uq_hq_editor_panel_order"))
    op.create_index("ix_hq_editor_panels_page", "hq_editor_panels", ["organization_id", "page_id", "panel_order"])

    op.create_table("hq_panel_text_layers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("panel_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("layer_order", sa.Integer(), nullable=False), sa.Column("layer_type", sa.String(24), nullable=False),
        sa.Column("speaker_name", sa.String(120)), sa.Column("content", sa.Text(), nullable=False), sa.Column("x", sa.Float(), nullable=False), sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False), sa.Column("height", sa.Float(), nullable=False), sa.Column("style", postgresql.JSONB(), nullable=False), sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_hq_panel_text_layers_panel", "hq_panel_text_layers", ["organization_id", "panel_id", "layer_order"])

    op.create_table("hq_editor_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_type", sa.String(24), nullable=False), sa.Column("label", sa.String(180)), sa.Column("revision_number", sa.Integer(), nullable=False), sa.Column("data_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False), sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_hq_editor_snapshots_project", "hq_editor_snapshots", ["organization_id", "comic_project_id", "created_at"])

    op.create_table("hq_generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(36), nullable=False), sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("current_step_code", sa.String(80)), sa.Column("total_pages", sa.Integer(), nullable=False), sa.Column("total_panels", sa.Integer(), nullable=False),
        sa.Column("completed_panels", sa.Integer(), nullable=False), sa.Column("failed_panels", sa.Integer(), nullable=False), sa.Column("continue_in_background", sa.Boolean(), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False), sa.Column("configuration", postgresql.JSONB(), nullable=False), sa.Column("result_summary", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_hq_generation_jobs_project", "hq_generation_jobs", ["organization_id", "comic_project_id", "status"])

    op.create_table("hq_generation_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("generation_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False), sa.Column("step_code", sa.String(80), nullable=False), sa.Column("title", sa.String(180), nullable=False),
        sa.Column("playful_message", sa.String(260), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("progress_weight", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer()), sa.Column("panel_id", postgresql.UUID(as_uuid=True)), sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "generation_job_id", "step_order", name="uq_hq_generation_step_order"))
    op.create_index("ix_hq_generation_steps_job", "hq_generation_steps", ["organization_id", "generation_job_id", "step_order"])

    op.create_table("hq_editor_autosaves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", sa.String(120), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("payload", postgresql.JSONB(), nullable=False), sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("last_saved_by_user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "comic_project_id", "client_id", name="uq_hq_editor_autosave_client"))
    op.create_index("ix_hq_editor_autosaves_project", "hq_editor_autosaves", ["organization_id", "comic_project_id", "updated_at"])


def downgrade() -> None:
    for table in ["hq_editor_autosaves", "hq_generation_steps", "hq_generation_jobs", "hq_editor_snapshots", "hq_panel_text_layers", "hq_editor_panels", "hq_editor_pages", "hq_layout_templates"]:
        op.drop_table(table)
