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


class QuestionItem(TimestampMixin, Base):
    __tablename__ = "assessment_hub_question_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_assessment_question_code"),
        Index("ix_assessment_questions_catalog", "organization_id", "status", "subject", "school_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    school_year: Mapped[str | None] = mapped_column(String(60))
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="INTERNAL")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class QuestionVersion(TimestampMixin, Base):
    __tablename__ = "assessment_hub_question_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "question_id", "version", name="uq_assessment_question_version"),
        Index("ix_assessment_question_versions_status", "organization_id", "status", "question_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(40), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    correct_answer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text)
    rubric: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    predicted_difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    accessibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class QuestionSkillLink(TimestampMixin, Base):
    __tablename__ = "assessment_hub_question_skills"
    __table_args__ = (
        UniqueConstraint("organization_id", "question_version_id", "skill_type", "skill_code", name="uq_assessment_question_skill"),
        Index("ix_assessment_question_skills_code", "organization_id", "skill_type", "skill_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    skill_type: Mapped[str] = mapped_column(String(40), nullable=False)
    skill_code: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(220), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AssessmentBlueprint(TimestampMixin, Base):
    __tablename__ = "assessment_hub_blueprints"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_assessment_blueprint_version"),
        Index("ix_assessment_blueprints_status", "organization_id", "status", "assessment_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    selection_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    delivery_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scoring_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExternalInstrument(TimestampMixin, Base):
    __tablename__ = "assessment_hub_external_instruments"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_assessment_external_instrument"),
        Index("ix_assessment_external_instruments_type", "organization_id", "instrument_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(60), nullable=False)
    authorship: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    license_status: Mapped[str] = mapped_column(String(60), nullable=False, default="REQUIRES_PERMISSION")
    permission_reference: Mapped[str | None] = mapped_column(Text)
    administration_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scoring_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    interpretation_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class InstrumentDimension(TimestampMixin, Base):
    __tablename__ = "assessment_hub_instrument_dimensions"
    __table_args__ = (
        UniqueConstraint("organization_id", "instrument_id", "code", name="uq_assessment_instrument_dimension"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    minimum_score: Mapped[float | None] = mapped_column(Float)
    maximum_score: Mapped[float | None] = mapped_column(Float)
    interpretation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AssessmentAttempt(TimestampMixin, Base):
    __tablename__ = "assessment_hub_attempts"
    __table_args__ = (
        Index("ix_assessment_attempts_student", "organization_id", "student_id", "status", "started_at"),
        Index("ix_assessment_attempts_blueprint", "organization_id", "blueprint_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    blueprint_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    external_instrument_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    question_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_score: Mapped[float | None] = mapped_column(Float)
    maximum_score: Mapped[float | None] = mapped_column(Float)
    percentage_score: Mapped[float | None] = mapped_column(Float)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)


class AssessmentResponse(TimestampMixin, Base):
    __tablename__ = "assessment_hub_responses"
    __table_args__ = (
        UniqueConstraint("organization_id", "attempt_id", "question_version_id", name="uq_assessment_attempt_response"),
        Index("ix_assessment_responses_review", "organization_id", "requires_human_review", "correction_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    score: Mapped[float | None] = mapped_column(Float)
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    correction_type: Mapped[str | None] = mapped_column(String(30))
    feedback: Mapped[str | None] = mapped_column(Text)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    corrected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class ScoreReview(TimestampMixin, Base):
    __tablename__ = "assessment_hub_score_reviews"
    __table_args__ = (Index("ix_assessment_score_reviews_status", "organization_id", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_score: Mapped[float | None] = mapped_column(Float)
    proposed_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[float | None] = mapped_column(Float)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentResultSummary(TimestampMixin, Base):
    __tablename__ = "assessment_hub_result_summaries"
    __table_args__ = (
        UniqueConstraint("organization_id", "attempt_id", name="uq_assessment_result_attempt"),
        Index("ix_assessment_results_student", "organization_id", "student_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_score: Mapped[float] = mapped_column(Float, nullable=False)
    percentage_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    skill_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    descriptive_interpretation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    scoring_version: Mapped[str] = mapped_column(String(60), nullable=False, default="1.0.0")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
