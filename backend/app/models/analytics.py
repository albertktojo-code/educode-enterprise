from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, JSON, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertSeverity(StrEnum):
    INFO = "info"
    ATTENTION = "attention"
    PRIORITY = "priority"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class InterventionType(StrEnum):
    REINFORCEMENT = "reinforcement"
    EXTRA_ATTEMPT = "extra_attempt"
    INDIVIDUAL_FEEDBACK = "individual_feedback"
    ADAPTED_ACTIVITY = "adapted_activity"
    EXTENDED_DEADLINE = "extended_deadline"
    ADVANCED_CHALLENGE = "advanced_challenge"
    FOLLOW_UP = "follow_up"


class InterventionStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"


class AnalyticsJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StudentSkillMetric(Base):
    __tablename__ = "student_skill_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "student_id", "subject_id", "skill_code", "ct_pillar_code",
            name="uq_student_skill_metric_dimension",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=True)
    skill_code: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    ct_pillar_code: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    proficiency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ClassroomSkillMetric(Base):
    __tablename__ = "classroom_skill_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "classroom_id", "skill_code", "ct_pillar_code",
            name="uq_classroom_skill_metric_dimension",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    classroom_id: Mapped[UUID] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    skill_code: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    ct_pillar_code: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    average_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    median_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    student_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssignmentItemMetric(Base):
    __tablename__ = "assignment_item_metrics"
    __table_args__ = (
        UniqueConstraint(
            "assignment_question_id",
            name="assignment_item_metrics_assignment_question_id_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True)
    assignment_question_id: Mapped[UUID] = mapped_column(
        ForeignKey("assignment_questions.id", ondelete="CASCADE"),
        index=True,
    )
    response_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    omission_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    difficulty_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    discrimination_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_response_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_awarded_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    distractor_distribution: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StudentProgressSnapshot(Base):
    __tablename__ = "student_progress_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), index=True, nullable=True)
    skill_code: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    ct_pillar_code: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    proficiency_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


class LearningAlert(Base):
    __tablename__ = "learning_alerts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    classroom_id: Mapped[UUID | None] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True, nullable=True)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True, nullable=True)
    alert_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity, name="learning_alert_severity"), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, name="learning_alert_status"), default=AlertStatus.OPEN, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    explanation: Mapped[str] = mapped_column(Text(), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningIntervention(Base):
    __tablename__ = "learning_interventions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    teacher_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    classroom_id: Mapped[UUID | None] = mapped_column(ForeignKey("classrooms.id", ondelete="SET NULL"), index=True, nullable=True)
    student_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    alert_id: Mapped[UUID | None] = mapped_column(ForeignKey("learning_alerts.id", ondelete="SET NULL"), index=True, nullable=True)
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("material_assignments.id", ondelete="SET NULL"), index=True, nullable=True)
    source_recommendation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("adaptive_recommendations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    comic_release_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"), index=True, nullable=True
    )
    adaptive_path_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("adaptive_learning_paths.id", ondelete="SET NULL"), index=True, nullable=True
    )
    accessible_resource_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("accessible_resource_versions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    ai_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_generation_requests.id", ondelete="SET NULL"), index=True, nullable=True
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    intervention_type: Mapped[InterventionType] = mapped_column(Enum(InterventionType, name="learning_intervention_type"), nullable=False)
    status: Mapped[InterventionStatus] = mapped_column(Enum(InterventionStatus, name="learning_intervention_status"), default=InterventionStatus.PLANNED, nullable=False)
    reason: Mapped[str] = mapped_column(Text(), nullable=False)
    notes: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    result_summary: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    plan_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    baseline_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    target_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LearningInterventionEvent(Base):
    __tablename__ = "learning_intervention_events"
    __table_args__ = (
        Index(
            "ix_learning_intervention_events_timeline",
            "organization_id", "intervention_id", "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    intervention_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_interventions.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    from_status: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalyticsRefreshJob(Base):
    __tablename__ = "analytics_refresh_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[AnalyticsJobStatus] = mapped_column(Enum(AnalyticsJobStatus, name="analytics_job_status"), default=AnalyticsJobStatus.PENDING, nullable=False)
    attempt_policy: Mapped[str] = mapped_column(String(30), default="best", nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
