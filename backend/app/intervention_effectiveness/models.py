from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class InterventionEvaluationCheckpoint(Base):
    __tablename__ = "intervention_evaluation_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "intervention_id",
            "window_code",
            name="uq_intervention_evaluation_window",
        ),
        Index(
            "ix_intervention_evaluation_due",
            "organization_id",
            "status",
            "scheduled_for",
        ),
        Index(
            "ix_intervention_evaluation_student",
            "organization_id",
            "student_id",
            "evaluated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    intervention_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_interventions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intervention_outcomes.id", ondelete="SET NULL"),
        index=True,
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("classrooms.id", ondelete="SET NULL"),
        index=True,
    )
    comic_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"),
        index=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("material_assignments.id", ondelete="SET NULL"),
        index=True,
    )
    accessible_resource_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accessible_resource_versions.id", ondelete="SET NULL"),
        index=True,
    )
    adaptive_path_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adaptive_learning_paths.id", ondelete="SET NULL"),
        index=True,
    )
    window_code: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        index=True,
    )
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="insufficient_evidence",
    )
    baseline_value: Mapped[float | None] = mapped_column(Float)
    observed_value: Mapped[float | None] = mapped_column(Float)
    delta_value: Mapped[float | None] = mapped_column(Float)
    target_value: Mapped[float | None] = mapped_column(Float)
    target_met: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    improved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    retained: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    alert_recurred: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    comparable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    privacy_suppressed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InterventionEffectivenessMetric(Base):
    __tablename__ = "intervention_effectiveness_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "scope_key",
            "period_start",
            "period_end",
            "window_code",
            "dimension_key",
            name="uq_intervention_effectiveness_metric",
        ),
        Index(
            "ix_intervention_effectiveness_period",
            "organization_id",
            "period_start",
            "period_end",
        ),
        Index(
            "ix_intervention_effectiveness_dimension",
            "organization_id",
            "dimension_type",
            "dimension_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    scope_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    scope_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    window_code: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
    )
    dimension_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    dimension_key: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )
    intervention_type: Mapped[str | None] = mapped_column(
        String(80),
    )
    comic_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"),
        index=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("material_assignments.id", ondelete="SET NULL"),
        index=True,
    )
    accessible_resource_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accessible_resource_versions.id", ondelete="SET NULL"),
        index=True,
    )
    adaptive_path_used: Mapped[bool | None] = mapped_column(Boolean)
    sample_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    improved_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    target_met_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    retained_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    recurrence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    insufficient_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    completion_rate: Mapped[float | None] = mapped_column(Float)
    improved_rate: Mapped[float | None] = mapped_column(Float)
    target_met_rate: Mapped[float | None] = mapped_column(Float)
    retention_rate: Mapped[float | None] = mapped_column(Float)
    recurrence_rate: Mapped[float | None] = mapped_column(Float)
    average_gain: Mapped[float | None] = mapped_column(Float)
    median_days_to_improvement: Mapped[float | None] = mapped_column(Float)
    privacy_suppressed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
