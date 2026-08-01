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


class AssessmentAnalyticsModel(TimestampMixin, Base):
    __tablename__ = "assessment_analytics_models"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_assessment_analytics_model_version"),
        Index("ix_assessment_analytics_models_status", "organization_id", "status", "is_default"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    privacy_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metric_definitions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentAnalyticsRun(TimestampMixin, Base):
    __tablename__ = "assessment_analytics_runs"
    __table_args__ = (
        Index("ix_assessment_analytics_runs_status", "organization_id", "status", "created_at"),
        Index("ix_assessment_analytics_runs_scope", "organization_id", "scope_type", "scope_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    analytics_model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class AssessmentItemMetric(TimestampMixin, Base):
    __tablename__ = "assessment_item_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "analytics_run_id", "question_version_id", name="uq_assessment_item_metric_run"),
        Index("ix_assessment_item_metrics_question", "organization_id", "question_version_id", "calculated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    question_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_difficulty: Mapped[float | None] = mapped_column(Float)
    observed_difficulty: Mapped[float | None] = mapped_column(Float)
    difficulty_delta: Mapped[float | None] = mapped_column(Float)
    facility_index: Mapped[float | None] = mapped_column(Float)
    discrimination_index: Mapped[float | None] = mapped_column(Float)
    point_biserial: Mapped[float | None] = mapped_column(Float)
    omission_rate: Mapped[float | None] = mapped_column(Float)
    average_response_time_seconds: Mapped[float | None] = mapped_column(Float)
    average_attempts: Mapped[float | None] = mapped_column(Float)
    hint_usage_rate: Mapped[float | None] = mapped_column(Float)
    review_rate: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    calculation_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssessmentDistractorMetric(TimestampMixin, Base):
    __tablename__ = "assessment_distractor_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "item_metric_id", "option_code", name="uq_assessment_distractor_option"),
        Index("ix_assessment_distractor_item", "organization_id", "item_metric_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    item_metric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    option_code: Mapped[str] = mapped_column(String(80), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selection_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    upper_group_rate: Mapped[float | None] = mapped_column(Float)
    lower_group_rate: Mapped[float | None] = mapped_column(Float)
    discrimination_signal: Mapped[float | None] = mapped_column(Float)
    non_functioning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class AssessmentSkillMetric(TimestampMixin, Base):
    __tablename__ = "assessment_skill_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "analytics_run_id", "skill_type", "skill_code", "cohort_key", name="uq_assessment_skill_metric"),
        Index("ix_assessment_skill_metrics_skill", "organization_id", "skill_type", "skill_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    skill_type: Mapped[str] = mapped_column(String(30), nullable=False)
    skill_code: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(220), nullable=False)
    cohort_key: Mapped[str] = mapped_column(String(160), nullable=False, default="ALL")
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    items_count: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mastery_rate: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    trend: Mapped[str | None] = mapped_column(String(30))
    gap_indicators: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AssessmentCohortMetric(TimestampMixin, Base):
    __tablename__ = "assessment_cohort_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "analytics_run_id", "cohort_type", "cohort_id", name="uq_assessment_cohort_metric"),
        Index("ix_assessment_cohort_metrics_cohort", "organization_id", "cohort_type", "cohort_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cohort_type: Mapped[str] = mapped_column(String(30), nullable=False)
    cohort_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cohort_name: Mapped[str] = mapped_column(String(220), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    median_score: Mapped[float | None] = mapped_column(Float)
    standard_deviation: Mapped[float | None] = mapped_column(Float)
    average_duration_seconds: Mapped[float | None] = mapped_column(Float)
    review_pending_rate: Mapped[float | None] = mapped_column(Float)
    accessibility_usage_rate: Mapped[float | None] = mapped_column(Float)
    privacy_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AssessmentReportDefinition(TimestampMixin, Base):
    __tablename__ = "assessment_report_definitions"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_assessment_report_definition_code"),
        Index("ix_assessment_report_definitions_status", "organization_id", "status", "audience"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    audience: Mapped[str] = mapped_column(String(30), nullable=False, default="TEACHER")
    sections: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    privacy_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class AssessmentReportExport(TimestampMixin, Base):
    __tablename__ = "assessment_report_exports"
    __table_args__ = (
        Index("ix_assessment_report_exports_status", "organization_id", "status", "created_at"),
        Index("ix_assessment_report_exports_definition", "organization_id", "report_definition_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    report_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    analytics_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="QUEUED")
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="CSV")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    storage_reference: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(64))
    row_count: Mapped[int | None] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
