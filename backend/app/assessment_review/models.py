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


class ReviewRubric(TimestampMixin, Base):
    __tablename__ = "assessment_review_rubrics"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_review_rubric_code"),
        Index("ix_review_rubrics_status", "organization_id", "status", "scope_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False, default="QUESTION")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class ReviewRubricVersion(TimestampMixin, Base):
    __tablename__ = "assessment_review_rubric_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "rubric_id", "version", name="uq_review_rubric_version"),
        Index("ix_review_rubric_versions_status", "organization_id", "status", "rubric_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rubric_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    score_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    feedback_templates: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    skill_mappings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    accessibility_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewAssignment(TimestampMixin, Base):
    __tablename__ = "assessment_review_assignments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "response_id", "reviewer_user_id", "review_round",
            name="uq_review_assignment_round"
        ),
        Index("ix_review_assignments_queue", "organization_id", "reviewer_user_id", "status", "priority"),
        Index("ix_review_assignments_response", "organization_id", "response_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rubric_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    review_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    review_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="SINGLE")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blinded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ReviewCriterionScore(TimestampMixin, Base):
    __tablename__ = "assessment_review_criterion_scores"
    __table_args__ = (
        UniqueConstraint("organization_id", "assignment_id", "criterion_code", name="uq_review_criterion_score"),
        Index("ix_review_criterion_scores_assignment", "organization_id", "assignment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    criterion_code: Mapped[str] = mapped_column(String(80), nullable=False)
    criterion_name: Mapped[str] = mapped_column(String(220), nullable=False)
    awarded_score: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False)
    level_code: Mapped[str | None] = mapped_column(String(80))
    evidence: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    skill_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    correction_source: Mapped[str] = mapped_column(String(30), nullable=False, default="HUMAN")
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class ReviewFeedback(TimestampMixin, Base):
    __tablename__ = "assessment_review_feedbacks"
    __table_args__ = (
        Index("ix_review_feedback_response", "organization_id", "response_id", "status", "audience"),
        Index("ix_review_feedback_attempt", "organization_id", "attempt_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    audience: Mapped[str] = mapped_column(String(30), nullable=False, default="STUDENT")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False, default="FORMATIVE")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    improvement_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    next_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    question_feedback: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    skill_feedback: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    accessible_variants: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewAppeal(TimestampMixin, Base):
    __tablename__ = "assessment_review_appeals"
    __table_args__ = (
        Index("ix_review_appeals_queue", "organization_id", "status", "created_at"),
        Index("ix_review_appeals_student", "organization_id", "student_id", "attempt_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(50), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    assigned_reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decision: Mapped[str | None] = mapped_column(String(40))
    decision_justification: Mapped[str | None] = mapped_column(Text)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewRegrade(TimestampMixin, Base):
    __tablename__ = "assessment_review_regrades"
    __table_args__ = (
        Index("ix_review_regrades_response", "organization_id", "response_id", "status"),
        Index("ix_review_regrades_attempt", "organization_id", "attempt_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    appeal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_score: Mapped[float | None] = mapped_column(Float)
    proposed_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float | None] = mapped_column(Float)
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    applied_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score_snapshot_before: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    score_snapshot_after: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ReviewAuditEvent(TimestampMixin, Base):
    __tablename__ = "assessment_review_audit_events"
    __table_args__ = (
        Index("ix_review_audit_entity", "organization_id", "entity_type", "entity_id", "created_at"),
        Index("ix_review_audit_event", "organization_id", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    new_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    justification: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(100))
