from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ComicVisualLibrary(TimestampMixin, Base):
    __tablename__ = "comic_visual_libraries"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_comic_visual_library_code"),
        Index("ix_comic_visual_libraries_scope", "organization_id", "scope", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    comic_project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(24), nullable=False, default="PERSONAL")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicCharacter(TimestampMixin, Base):
    __tablename__ = "comic_characters"
    __table_args__ = (
        UniqueConstraint("organization_id", "library_id", "slug", name="uq_comic_character_slug"),
        Index("ix_comic_characters_filter", "organization_id", "library_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    library_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    origin_comic_project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    biography: Mapped[str] = mapped_column(Text, nullable=False, default="")
    personality: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    identity_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    default_wardrobe: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    visual_style: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reference_assets: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    identity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicCharacterVersion(TimestampMixin, Base):
    __tablename__ = "comic_character_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "character_id", "version_number", name="uq_comic_character_version"),
        Index("ix_comic_character_versions_character", "organization_id", "character_id", "version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    identity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicCharacterVariant(TimestampMixin, Base):
    __tablename__ = "comic_character_variants"
    __table_args__ = (
        UniqueConstraint("organization_id", "character_id", "code", name="uq_comic_character_variant_code"),
        Index("ix_comic_character_variants_character", "organization_id", "character_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    wardrobe: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expression: Mapped[str | None] = mapped_column(String(80))
    pose: Mapped[str | None] = mapped_column(String(120))
    accessories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    prompt_overrides: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reference_assets: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicScenario(TimestampMixin, Base):
    __tablename__ = "comic_scenarios"
    __table_args__ = (
        UniqueConstraint("organization_id", "library_id", "slug", name="uq_comic_scenario_slug"),
        Index("ix_comic_scenarios_filter", "organization_id", "library_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    library_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    origin_comic_project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    lighting_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    required_objects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    visual_style: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reference_assets: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    identity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicScenarioVersion(TimestampMixin, Base):
    __tablename__ = "comic_scenario_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "scenario_id", "version_number", name="uq_comic_scenario_version"),
        Index("ix_comic_scenario_versions_scenario", "organization_id", "scenario_id", "version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    identity_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicContinuityRecord(TimestampMixin, Base):
    __tablename__ = "comic_continuity_records"
    __table_args__ = (
        UniqueConstraint("organization_id", "comic_project_id", "page_id", "panel_id", name="uq_comic_continuity_panel"),
        Index("ix_comic_continuity_sequence", "organization_id", "comic_project_id", "sequence_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    panel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str | None] = mapped_column(String(180))
    time_of_day: Mapped[str | None] = mapped_column(String(80))
    weather: Mapped[str | None] = mapped_column(String(80))
    character_states: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    important_objects: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    narrative_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    previous_panel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    next_panel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ComicConsistencyCheck(TimestampMixin, Base):
    __tablename__ = "comic_consistency_checks"
    __table_args__ = (
        Index("ix_comic_consistency_checks_project", "organization_id", "comic_project_id", "status", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    page_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    panel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    entity_type: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    check_code: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="WARNING")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    expected_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    observed_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    resolution: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    detected_by: Mapped[str] = mapped_column(String(24), nullable=False, default="RULE")
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComicGenerationBatch(TimestampMixin, Base):
    __tablename__ = "comic_generation_batches"
    __table_args__ = (
        Index("ix_comic_generation_batches_project", "organization_id", "comic_project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    selection_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING_ONLY")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lock_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generation_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class ComicGenerationBatchItem(TimestampMixin, Base):
    __tablename__ = "comic_generation_batch_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "batch_id", "panel_id", name="uq_comic_generation_batch_panel"),
        Index("ix_comic_generation_batch_items", "organization_id", "batch_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    panel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    character_locks: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scenario_locks: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    prompt_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_asset_reference: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
