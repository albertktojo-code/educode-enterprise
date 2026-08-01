from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class HQCanvasDocument(TimestampMixin, Base):
    __tablename__ = "hq_canvas_documents"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "page_id", name="uq_hq_canvas_document_page"
        ),
        Index(
            "ix_hq_canvas_documents_project",
            "organization_id",
            "comic_project_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    page_width: Mapped[float] = mapped_column(Float, nullable=False, default=210.0)
    page_height: Mapped[float] = mapped_column(Float, nullable=False, default=297.0)
    measurement_unit: Mapped[str] = mapped_column(String(12), nullable=False, default="MM")
    dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    bleed_mm: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    safe_margin_mm: Mapped[float] = mapped_column(Float, nullable=False, default=8.0)
    grid_size: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    snap_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rulers_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_bleed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_safe_area: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    background_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    editor_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HQCanvasLayer(TimestampMixin, Base):
    __tablename__ = "hq_canvas_layers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document_id", "z_index", name="uq_hq_canvas_layer_z"
        ),
        Index(
            "ix_hq_canvas_layers_document",
            "organization_id",
            "document_id",
            "z_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_panel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    layer_type: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    rotation_deg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    opacity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blend_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="NORMAL")
    shape: Mapped[str] = mapped_column(String(32), nullable=False, default="RECTANGLE")
    clip_path: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    transform_origin: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    style: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    asset_reference: Mapped[str | None] = mapped_column(Text)
    accessibility_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )


class HQCanvasGuide(TimestampMixin, Base):
    __tablename__ = "hq_canvas_guides"
    __table_args__ = (
        Index(
            "ix_hq_canvas_guides_document",
            "organization_id",
            "document_id",
            "orientation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    orientation: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[float] = mapped_column(Float, nullable=False)
    guide_type: Mapped[str] = mapped_column(String(24), nullable=False, default="CUSTOM")
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    label: Mapped[str | None] = mapped_column(String(120))


class HQCanvasGroup(TimestampMixin, Base):
    __tablename__ = "hq_canvas_groups"
    __table_args__ = (
        Index(
            "ix_hq_canvas_groups_document", "organization_id", "document_id", "name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    layer_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transform: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class HQCanvasOperation(TimestampMixin, Base):
    __tablename__ = "hq_canvas_operations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document_id", "sequence", name="uq_hq_canvas_operation_seq"
        ),
        Index(
            "ix_hq_canvas_operations_document",
            "organization_id",
            "document_id",
            "sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    forward_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reverse_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HQExportPreset(TimestampMixin, Base):
    __tablename__ = "hq_export_presets"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", "version", name="uq_hq_export_preset_version"
        ),
        Index(
            "ix_hq_export_presets_filter",
            "organization_id",
            "output_format",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(24), nullable=False, default="1.0.0")
    output_format: Mapped[str] = mapped_column(String(16), nullable=False)
    page_size: Mapped[str] = mapped_column(String(32), nullable=False, default="A4")
    dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    color_profile: Mapped[str] = mapped_column(String(32), nullable=False, default="SRGB")
    include_bleed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_crop_marks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flatten_layers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    accessibility_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HQExportJob(TimestampMixin, Base):
    __tablename__ = "hq_export_jobs"
    __table_args__ = (
        Index(
            "ix_hq_export_jobs_document",
            "organization_id",
            "document_id",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    preset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(36), nullable=False, default="QUEUED")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    output_reference: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HQPreflightFinding(TimestampMixin, Base):
    __tablename__ = "hq_preflight_findings"
    __table_args__ = (
        Index(
            "ix_hq_preflight_findings_document",
            "organization_id",
            "document_id",
            "severity",
            "resolved",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    export_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(24), nullable=False, default="DOCUMENT")
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
