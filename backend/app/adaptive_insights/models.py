from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class InterventionOutcomeRecord(TimestampMixin, Base):
    __tablename__ = "intervention_outcomes"
    __table_args__ = (
        Index("ix_intervention_outcomes_student_node", "organization_id", "student_id", "learning_node_id", "occurred_at"),
        Index("ix_intervention_outcomes_material", "organization_id", "material_id", "intervention_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    learning_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(80), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    learning_intervention_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("learning_interventions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comic_release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mastery_before: Mapped[float] = mapped_column(Float, nullable=False)
    mastery_after: Mapped[float] = mapped_column(Float, nullable=False)
    mastery_gain: Mapped[float] = mapped_column(Float, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    hints_average: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    attempts_average: Mapped[float] = mapped_column(Float, nullable=False, default=1)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class MaterialEffectivenessMetric(TimestampMixin, Base):
    __tablename__ = "material_effectiveness_metrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "resource_type", "resource_id", "calculation_version", name="uq_material_effectiveness_version"),
        Index("ix_material_effectiveness_classification", "organization_id", "classification", "sample_size"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_rate: Mapped[float | None] = mapped_column(Float)
    average_gain: Mapped[float | None] = mapped_column(Float)
    median_gain: Mapped[float | None] = mapped_column(Float)
    average_attempts: Mapped[float] = mapped_column(Float, nullable=False)
    average_hints: Mapped[float] = mapped_column(Float, nullable=False)
    average_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(60), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveModelVersion(TimestampMixin, Base):
    __tablename__ = "adaptive_insight_model_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", "version", name="uq_adaptive_insight_model_name_version"),
        Index("ix_adaptive_insight_models_scope", "organization_id", "scope_type", "scope_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    algorithm_type: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecommendationSimulation(TimestampMixin, Base):
    __tablename__ = "recommendation_simulations"
    __table_args__ = (Index("ix_recommendation_simulations_org_created", "organization_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    profiles_count: Mapped[int] = mapped_column(Integer, nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ControlledExperiment(TimestampMixin, Base):
    __tablename__ = "controlled_experiments"
    __table_args__ = (Index("ix_controlled_experiments_status", "organization_id", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    primary_metric: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_direction: Mapped[str] = mapped_column(String(30), nullable=False)
    assignment_strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    strategies: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    minimum_sample_per_strategy: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    __table_args__ = (
        UniqueConstraint("organization_id", "experiment_id", "participant_id", name="uq_experiment_participant"),
        Index("ix_experiment_assignments_strategy", "organization_id", "experiment_id", "strategy_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(30), nullable=False)
    assignment_strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ExperimentObservation(Base):
    __tablename__ = "experiment_observations"
    __table_args__ = (Index("ix_experiment_observations_strategy", "organization_id", "experiment_id", "strategy_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    experiment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    strategy_key: Mapped[str] = mapped_column(String(30), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
