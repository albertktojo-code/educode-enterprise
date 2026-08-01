"""Sprint 16.2 - layout livre e diagramacao avancada de HQ.

Revision ID: 0037_comic_layout_studio
Revises: 0036_comic_page_editor
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0037_comic_layout_studio"
down_revision: str | None = "0036_comic_page_editor"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "hq_canvas_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("page_width", sa.Float(), nullable=False),
        sa.Column("page_height", sa.Float(), nullable=False),
        sa.Column("measurement_unit", sa.String(12), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=False),
        sa.Column("bleed_mm", sa.Float(), nullable=False),
        sa.Column("safe_margin_mm", sa.Float(), nullable=False),
        sa.Column("grid_size", sa.Float(), nullable=False),
        sa.Column("snap_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rulers_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_bleed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("show_safe_area", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("background_settings", postgresql.JSONB(), nullable=False),
        sa.Column("editor_settings", postgresql.JSONB(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "page_id", name="uq_hq_canvas_document_page"),
    )
    op.create_index(
        "ix_hq_canvas_documents_project",
        "hq_canvas_documents",
        ["organization_id", "comic_project_id", "status"],
    )

    op.create_table(
        "hq_canvas_layers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_panel_id", postgresql.UUID(as_uuid=True)),
        sa.Column("group_id", postgresql.UUID(as_uuid=True)),
        sa.Column("layer_type", sa.String(36), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("z_index", sa.Integer(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("rotation_deg", sa.Float(), nullable=False),
        sa.Column("opacity", sa.Float(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blend_mode", sa.String(32), nullable=False),
        sa.Column("shape", sa.String(32), nullable=False),
        sa.Column("clip_path", postgresql.JSONB(), nullable=False),
        sa.Column("transform_origin", postgresql.JSONB(), nullable=False),
        sa.Column("style", postgresql.JSONB(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("asset_reference", sa.Text()),
        sa.Column("accessibility_metadata", postgresql.JSONB(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "document_id", "z_index", name="uq_hq_canvas_layer_z"),
    )
    op.create_index(
        "ix_hq_canvas_layers_document",
        "hq_canvas_layers",
        ["organization_id", "document_id", "z_index"],
    )

    op.create_table(
        "hq_canvas_guides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("orientation", sa.String(16), nullable=False),
        sa.Column("position", sa.Float(), nullable=False),
        sa.Column("guide_type", sa.String(24), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("label", sa.String(120)),
        *timestamps(),
    )
    op.create_index(
        "ix_hq_canvas_guides_document",
        "hq_canvas_guides",
        ["organization_id", "document_id", "orientation"],
    )

    op.create_table(
        "hq_canvas_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("layer_ids", postgresql.JSONB(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transform", postgresql.JSONB(), nullable=False),
        *timestamps(),
    )
    op.create_index(
        "ix_hq_canvas_groups_document",
        "hq_canvas_groups",
        ["organization_id", "document_id", "name"],
    )

    op.create_table(
        "hq_canvas_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(24), nullable=False),
        sa.Column("target_type", sa.String(24), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("forward_payload", postgresql.JSONB(), nullable=False),
        sa.Column("reverse_payload", postgresql.JSONB(), nullable=False),
        sa.Column("applied", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "document_id", "sequence", name="uq_hq_canvas_operation_seq"),
    )
    op.create_index(
        "ix_hq_canvas_operations_document",
        "hq_canvas_operations",
        ["organization_id", "document_id", "sequence"],
    )

    op.create_table(
        "hq_export_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.String(24), nullable=False),
        sa.Column("output_format", sa.String(16), nullable=False),
        sa.Column("page_size", sa.String(32), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=False),
        sa.Column("color_profile", sa.String(32), nullable=False),
        sa.Column("include_bleed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_crop_marks", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("flatten_layers", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("accessibility_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_hq_export_preset_version"),
    )
    op.create_index(
        "ix_hq_export_presets_filter",
        "hq_export_presets",
        ["organization_id", "output_format", "status"],
    )

    preset_table = sa.table(
        "hq_export_presets",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("version", sa.String()),
        sa.column("output_format", sa.String()),
        sa.column("page_size", sa.String()),
        sa.column("dpi", sa.Integer()),
        sa.column("color_profile", sa.String()),
        sa.column("include_bleed", sa.Boolean()),
        sa.column("include_crop_marks", sa.Boolean()),
        sa.column("flatten_layers", sa.Boolean()),
        sa.column("accessibility_enabled", sa.Boolean()),
        sa.column("configuration", postgresql.JSONB()),
        sa.column("status", sa.String()),
        sa.column("is_system", sa.Boolean()),
        sa.column("created_by_user_id", postgresql.UUID(as_uuid=True)),
    )
    system_user = uuid.UUID("00000000-0000-0000-0000-000000000000")
    op.bulk_insert(
        preset_table,
        [
            {
                "id": uuid.UUID("16020000-0000-0000-0000-000000000001"),
                "organization_id": None,
                "code": "PDF_PRINT_A4",
                "name": "PDF A4 para impressao",
                "description": "PDF em 300 DPI com sangria e marcas de corte opcionais.",
                "version": "1.0.0",
                "output_format": "PDF",
                "page_size": "A4",
                "dpi": 300,
                "color_profile": "SRGB",
                "include_bleed": True,
                "include_crop_marks": True,
                "flatten_layers": True,
                "accessibility_enabled": True,
                "configuration": {"quality": "PRINT", "embed_fonts": True},
                "status": "PUBLISHED",
                "is_system": True,
                "created_by_user_id": system_user,
            },
            {
                "id": uuid.UUID("16020000-0000-0000-0000-000000000002"),
                "organization_id": None,
                "code": "PNG_CLASSROOM",
                "name": "PNG para apresentacao",
                "description": "Imagem em alta resolucao para projetor e sala de aula.",
                "version": "1.0.0",
                "output_format": "PNG",
                "page_size": "CUSTOM",
                "dpi": 144,
                "color_profile": "SRGB",
                "include_bleed": False,
                "include_crop_marks": False,
                "flatten_layers": True,
                "accessibility_enabled": True,
                "configuration": {"quality": "SCREEN", "transparent_background": False},
                "status": "PUBLISHED",
                "is_system": True,
                "created_by_user_id": system_user,
            },
            {
                "id": uuid.UUID("16020000-0000-0000-0000-000000000003"),
                "organization_id": None,
                "code": "WEB_READING",
                "name": "Leitura digital acessivel",
                "description": "Pacote para leitura web com metadados de acessibilidade.",
                "version": "1.0.0",
                "output_format": "WEBP",
                "page_size": "RESPONSIVE",
                "dpi": 144,
                "color_profile": "SRGB",
                "include_bleed": False,
                "include_crop_marks": False,
                "flatten_layers": False,
                "accessibility_enabled": True,
                "configuration": {"quality": "WEB", "include_reading_order": True},
                "status": "PUBLISHED",
                "is_system": True,
                "created_by_user_id": system_user,
            },
        ],
    )

    op.create_table(
        "hq_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preset_id", postgresql.UUID(as_uuid=True)),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(36), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("configuration", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("output_reference", sa.Text()),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index(
        "ix_hq_export_jobs_document",
        "hq_export_jobs",
        ["organization_id", "document_id", "status"],
    )

    op.create_table(
        "hq_preflight_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(24), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index(
        "ix_hq_preflight_findings_document",
        "hq_preflight_findings",
        ["organization_id", "document_id", "severity", "resolved"],
    )


def downgrade() -> None:
    for table in [
        "hq_preflight_findings",
        "hq_export_jobs",
        "hq_export_presets",
        "hq_canvas_operations",
        "hq_canvas_groups",
        "hq_canvas_guides",
        "hq_canvas_layers",
        "hq_canvas_documents",
    ]:
        op.drop_table(table)
