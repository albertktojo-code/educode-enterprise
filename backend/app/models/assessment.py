from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AssessmentSourceType(StrEnum):
    TEACHER = "teacher"
    AI = "ai"
    IMPORTED = "imported"
    EXTERNAL = "external"


class QuestionBankStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    RETIRED = "retired"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    NEEDS_MAPPING = "needs_mapping"
    READY = "ready"
    IMPORTED = "imported"
    FAILED = "failed"


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(60), default="assessment", nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default=AssessmentSourceType.TEACHER.value, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=AssessmentStatus.DRAFT.value, nullable=False)
    current_version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    versions: Mapped[list["AssessmentVersion"]] = relationship(back_populates="assessment", cascade="all, delete-orphan", lazy="selectin")


class AssessmentVersion(Base):
    __tablename__ = "assessment_versions"
    __table_args__ = (UniqueConstraint("assessment_id", "version_number", name="uq_assessment_version_number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instructions: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    scoring_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    delivery_defaults: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    assessment: Mapped[Assessment] = relationship(back_populates="versions")
    items: Mapped[list["AssessmentVersionItem"]] = relationship(back_populates="version", cascade="all, delete-orphan", order_by="AssessmentVersionItem.position", lazy="selectin")


class QuestionBankItem(Base):
    __tablename__ = "question_bank_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    item_type: Mapped[str] = mapped_column(String(40), nullable=False)
    prompt: Mapped[str] = mapped_column(Text(), nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    curriculum_skill_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    ct_pillar_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default=AssessmentSourceType.TEACHER.value, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ai_generation_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    requires_manual_grading: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=QuestionBankStatus.DRAFT.value, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(240), index=True, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AssessmentVersionItem(Base):
    __tablename__ = "assessment_version_items"
    __table_args__ = (UniqueConstraint("assessment_version_id", "position", name="uq_assessment_version_item_position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assessment_version_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_versions.id", ondelete="CASCADE"), index=True)
    question_bank_item_id: Mapped[UUID] = mapped_column(ForeignKey("question_bank_items.id", ondelete="RESTRICT"), index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points_override: Mapped[float | None] = mapped_column(Float, nullable=True)
    item_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    version: Mapped[AssessmentVersion] = relationship(back_populates="items")
    bank_item: Mapped[QuestionBankItem] = relationship(lazy="selectin")


class AssessmentDeliveryLink(Base):
    __tablename__ = "assessment_delivery_links"
    __table_args__ = (UniqueConstraint("material_assignment_id", name="uq_assessment_delivery_assignment"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[UUID] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    assessment_version_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_versions.id", ondelete="RESTRICT"), index=True)
    material_assignment_id: Mapped[UUID] = mapped_column(ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssessmentOutcomeEvidence(Base):
    __tablename__ = "assessment_outcome_evidence"
    __table_args__ = (UniqueConstraint("answer_id", "dimension_type", "dimension_code", name="uq_assessment_outcome_answer_dimension"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    assessment_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("assessment_versions.id", ondelete="SET NULL"), index=True, nullable=True)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("student_attempts.id", ondelete="CASCADE"), index=True)
    answer_id: Mapped[UUID] = mapped_column(ForeignKey("student_answers.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("assignment_questions.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    dimension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dimension_code: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    score_obtained: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_possible: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    calculation_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssessmentImportJob(Base):
    __tablename__ = "assessment_import_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    source_format: Mapped[str] = mapped_column(String(30), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=ImportJobStatus.PENDING.value, nullable=False)
    field_mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rows_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    imported_assessment_id: Mapped[UUID | None] = mapped_column(ForeignKey("assessments.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssessmentConnector(Base):
    __tablename__ = "assessment_connectors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="inactive", nullable=False)
    public_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    external_system_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssessmentAuditEvent(Base):
    __tablename__ = "assessment_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[UUID | None] = mapped_column(ForeignKey("assessments.id", ondelete="SET NULL"), index=True, nullable=True)
    assessment_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("assessment_versions.id", ondelete="SET NULL"), nullable=True)
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("material_assignments.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    performed_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
