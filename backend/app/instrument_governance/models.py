from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InstrumentLicense(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_licenses"
    __table_args__ = (
        UniqueConstraint("organization_id", "instrument_id", "version", name="uq_instrument_license_version"),
        Index("ix_instrument_licenses_status", "organization_id", "status", "valid_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    license_holder: Mapped[str] = mapped_column(String(240), nullable=False)
    rights_owner: Mapped[str | None] = mapped_column(String(240))
    permission_reference: Mapped[str] = mapped_column(Text, nullable=False)
    rights_scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    permitted_populations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    permitted_territories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    item_exposure_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    storage_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdministrationProtocol(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_protocols"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "instrument_id", "code", "version", name="uq_instrument_protocol_version"
        ),
        Index("ix_instrument_protocols_status", "organization_id", "status", "instrument_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    instructions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    target_population: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    administration_conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    accessibility_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scoring_reference: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NormGroup(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_norm_groups"
    __table_args__ = (
        UniqueConstraint("organization_id", "instrument_id", "code", "version", name="uq_instrument_norm_group"),
        Index("ix_instrument_norm_groups_lookup", "organization_id", "instrument_id", "locale", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="pt-BR")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    age_min: Mapped[float | None] = mapped_column(Float)
    age_max: Mapped[float | None] = mapped_column(Float)
    school_year_min: Mapped[int | None] = mapped_column(Integer)
    school_year_max: Mapped[int | None] = mapped_column(Integer)
    population_filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sample_size: Mapped[int | None] = mapped_column(Integer)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    methodology: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NormTableEntry(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_norm_entries"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "norm_group_id", "dimension_code", "raw_min", "raw_max",
            name="uq_instrument_norm_entry_range",
        ),
        Index("ix_instrument_norm_entries_lookup", "organization_id", "norm_group_id", "dimension_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    norm_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dimension_code: Mapped[str] = mapped_column(String(80), nullable=False, default="TOTAL")
    raw_min: Mapped[float] = mapped_column(Float, nullable=False)
    raw_max: Mapped[float] = mapped_column(Float, nullable=False)
    standardized_score: Mapped[float | None] = mapped_column(Float)
    percentile: Mapped[float | None] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(120), nullable=False)
    interpretation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DimensionFrameworkMapping(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_mappings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "instrument_id", "dimension_id", "framework_type", "framework_code",
            name="uq_instrument_dimension_mapping",
        ),
        Index("ix_instrument_mappings_framework", "organization_id", "framework_type", "framework_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dimension_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    framework_type: Mapped[str] = mapped_column(String(40), nullable=False)
    framework_code: Mapped[str] = mapped_column(String(100), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(40), nullable=False, default="RELATED")
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class InstrumentImportBatch(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_imports"
    __table_args__ = (
        UniqueConstraint("organization_id", "checksum_sha256", name="uq_instrument_import_checksum"),
        Index("ix_instrument_imports_status", "organization_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    file_format: Mapped[str] = mapped_column(String(40), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECEIVED")
    declared_license_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    contains_protected_items: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    imported_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    validated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InstrumentResultInterpretation(TimestampMixin, Base):
    __tablename__ = "assessment_instrument_interpretations"
    __table_args__ = (
        UniqueConstraint("organization_id", "attempt_id", "scoring_version", name="uq_instrument_interpretation"),
        Index("ix_instrument_interpretations_review", "organization_id", "status", "requires_human_review"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    norm_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    scoring_version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CALCULATED")
    raw_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    standardized_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    classifications: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    descriptive_interpretation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    calculated_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    validated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
