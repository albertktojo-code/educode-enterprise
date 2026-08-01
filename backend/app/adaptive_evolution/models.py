from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
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


class GraduatedHint(Base, TimestampMixin):
    __tablename__ = "graduated_hints"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "resource_type", "resource_id", "question_id", "level_order", "version",
            name="uq_graduated_hint_scope_level_version",
        ),
        Index("ix_graduated_hints_org_resource", "organization_id", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    learning_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    level: Mapped[str] = mapped_column(String(40), nullable=False)
    level_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_format: Mapped[str] = mapped_column(String(30), nullable=False, default="PLAIN_TEXT")
    release_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    penalty_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class HintUsage(Base):
    __tablename__ = "hint_usages"
    __table_args__ = (
        Index("ix_hint_usages_student_attempt", "organization_id", "student_id", "attempt_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    question_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    graduated_hint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graduated_hints.id", ondelete="RESTRICT"), nullable=False
    )
    release_type: Mapped[str] = mapped_column(String(40), nullable=False)
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    response_after_hint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    result_after_hint: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_to_response_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class SpacedReviewSchedule(Base, TimestampMixin):
    __tablename__ = "spaced_review_schedules"
    __table_args__ = (
        UniqueConstraint("organization_id", "student_id", "learning_node_id", name="uq_review_schedule_student_node"),
        Index("ix_review_schedule_due", "organization_id", "status", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    learning_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mastery_score_at_schedule: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_at_schedule: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")


class SpacedReviewEvent(Base):
    __tablename__ = "spaced_review_events"
    __table_args__ = (Index("ix_review_events_schedule", "organization_id", "schedule_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("spaced_review_schedules.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    learning_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    new_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_applied: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveFeedback(Base):
    __tablename__ = "adaptive_feedbacks"
    __table_args__ = (Index("ix_adaptive_feedback_attempt", "organization_id", "attempt_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    response_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    learning_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    error_type: Mapped[str] = mapped_column(String(40), nullable=False)
    mastery_level: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str] = mapped_column(String(60), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    generated_by: Mapped[str] = mapped_column(String(30), nullable=False, default="DETERMINISTIC")
    review_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_REQUIRED")
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    presented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    student_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StudentDifficultyProfile(Base, TimestampMixin):
    __tablename__ = "student_difficulty_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "student_id", "learning_node_id", name="uq_student_difficulty_node"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    learning_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    difficulty_score: Mapped[float] = mapped_column(Float, nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    calculation_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ResourceDifficultyMetric(Base, TimestampMixin):
    __tablename__ = "resource_difficulty_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "resource_type", "resource_id", "learning_node_id",
            name="uq_resource_difficulty_scope",
        ),
        Index("ix_resource_difficulty_divergence", "organization_id", "difficulty_classification"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    learning_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    predicted_difficulty: Mapped[float] = mapped_column(Float, nullable=False)
    observed_difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_classification: Mapped[str] = mapped_column(String(40), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    metrics_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    calculation_version: Mapped[str] = mapped_column(String(40), nullable=False, default="1.0.0")
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProgressionRule(Base, TimestampMixin):
    __tablename__ = "progression_rules"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", "version", name="uq_progression_rule_name_version"),
        Index("ix_progression_rules_scope", "organization_id", "scope_type", "scope_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_action: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    requires_teacher_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProgressionDecision(Base):
    __tablename__ = "progression_decisions"
    __table_args__ = (Index("ix_progression_decisions_student", "organization_id", "student_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    learning_path_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    learning_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("progression_rules.id", ondelete="SET NULL"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    requires_teacher_approval: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AccessibleResourceVersion(Base, TimestampMixin):
    __tablename__ = "accessible_resource_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "source_resource_type", "source_resource_id", "adaptation_type", "version",
            name="uq_accessible_resource_version",
        ),
        Index("ix_accessible_versions_source", "organization_id", "source_resource_type", "source_resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    adaptation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accessibility_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    pedagogical_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    pedagogical_equivalence_status: Mapped[str] = mapped_column(String(50), nullable=False)
    generation_method: Mapped[str] = mapped_column(String(30), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NEEDS_REVIEW")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
