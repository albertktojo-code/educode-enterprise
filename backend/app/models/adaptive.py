from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdaptiveModelVersion(Base):
    __tablename__ = "adaptive_model_versions"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_adaptive_model_org_code_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    thresholds_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    minimum_evidence_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AdaptiveLearningProfile(Base):
    __tablename__ = "adaptive_learning_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "student_id", name="uq_adaptive_profile_org_student"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    preferred_formats: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    accessibility_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    teacher_notes: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    last_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AdaptiveSkillState(Base):
    __tablename__ = "adaptive_skill_states"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "student_id", "dimension_type", "dimension_code",
            name="uq_adaptive_skill_state_dimension",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_learning_profiles.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=True)
    model_version_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_model_versions.id", ondelete="RESTRICT"), index=True)
    dimension_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    dimension_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mastery_level: Mapped[str] = mapped_column(String(40), default="not_assessed", nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(30), default="insufficient", nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weighted_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weighted_possible: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trend: Mapped[str] = mapped_column(String(30), default="stable", nullable=False)
    evidence_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    calculation_explanation: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    first_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkillPrerequisite(Base):
    __tablename__ = "skill_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "dimension_type", "dimension_code", "prerequisite_type", "prerequisite_code",
            name="uq_skill_prerequisite_relation",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    dimension_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    dimension_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    prerequisite_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prerequisite_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(40), default="required", nullable=False)
    minimum_mastery: Mapped[float] = mapped_column(Float, default=0.65, nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveStudentGroup(Base):
    __tablename__ = "adaptive_student_groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    classroom_id: Mapped[UUID | None] = mapped_column(ForeignKey("classrooms.id", ondelete="SET NULL"), index=True, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    purpose: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    target_dimension_type: Mapped[str] = mapped_column(String(30), default="skill", nullable=False)
    target_dimension_code: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False, index=True)
    is_visible_to_students: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AdaptiveGroupMember(Base):
    __tablename__ = "adaptive_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "student_id", name="uq_adaptive_group_student"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_student_groups.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reason_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    added_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdaptiveRecommendation(Base):
    __tablename__ = "adaptive_recommendations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    classroom_id: Mapped[UUID | None] = mapped_column(ForeignKey("classrooms.id", ondelete="SET NULL"), index=True, nullable=True)
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("adaptive_student_groups.id", ondelete="SET NULL"), index=True, nullable=True)
    skill_state_id: Mapped[UUID | None] = mapped_column(ForeignKey("adaptive_skill_states.id", ondelete="SET NULL"), index=True, nullable=True)
    model_version_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_model_versions.id", ondelete="RESTRICT"), index=True)
    source_alert_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_alerts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_comic_release_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_ai_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_generation_requests.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_kind: Mapped[str] = mapped_column(
        String(40), default="generic_alert", nullable=False, index=True
    )
    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending_review", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    target_dimension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_dimension_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_mastery: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    proposed_materials: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_by_ai: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AdaptiveRecommendationEvidence(Base):
    __tablename__ = "adaptive_recommendation_evidence"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    recommendation_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_recommendations.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(nullable=True)
    dimension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dimension_code: Mapped[str] = mapped_column(String(120), nullable=False)
    observed_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveLearningPath(Base):
    __tablename__ = "adaptive_learning_paths"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    classroom_id: Mapped[UUID | None] = mapped_column(ForeignKey("classrooms.id", ondelete="SET NULL"), index=True, nullable=True)
    group_id: Mapped[UUID | None] = mapped_column(ForeignKey("adaptive_student_groups.id", ondelete="SET NULL"), index=True, nullable=True)
    recommendation_id: Mapped[UUID | None] = mapped_column(ForeignKey("adaptive_recommendations.id", ondelete="SET NULL"), index=True, nullable=True)
    model_version_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_model_versions.id", ondelete="RESTRICT"), index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    path_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    goal: Mapped[str] = mapped_column(Text(), nullable=False)
    target_dimension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_dimension_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    target_mastery: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    minimum_evidence_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AdaptivePathStep(Base):
    __tablename__ = "adaptive_path_steps"
    __table_args__ = (
        UniqueConstraint("path_id", "position", name="uq_adaptive_path_step_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    path_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_learning_paths.id", ondelete="CASCADE"), index=True)
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("material_assignments.id", ondelete="SET NULL"), index=True, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    content_reference: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="locked", nullable=False, index=True)
    advancement_rule: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveReviewSchedule(Base):
    __tablename__ = "adaptive_review_schedules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    path_id: Mapped[UUID | None] = mapped_column(ForeignKey("adaptive_learning_paths.id", ondelete="SET NULL"), index=True, nullable=True)
    step_id: Mapped[UUID | None] = mapped_column(ForeignKey("adaptive_path_steps.id", ondelete="SET NULL"), index=True, nullable=True)
    dimension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dimension_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    review_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptivePathOutcome(Base):
    __tablename__ = "adaptive_path_outcomes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    path_id: Mapped[UUID] = mapped_column(ForeignKey("adaptive_learning_paths.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    dimension_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dimension_code: Mapped[str] = mapped_column(String(120), nullable=False)
    mastery_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    mastery_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    mastery_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_before: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_after: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdaptiveAuditEvent(Base):
    __tablename__ = "adaptive_audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
