from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssignmentStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    CLOSED = "closed"
    CANCELED = "canceled"
    ARCHIVED = "archived"


class AssignmentType(StrEnum):
    READING = "reading"
    READING_EXERCISE = "reading_exercise"
    ACTIVITY = "activity"
    QUIZ = "quiz"
    ASSESSMENT = "assessment"
    PRETEST = "pretest"
    POSTTEST = "posttest"
    REINFORCEMENT = "reinforcement"
    CHALLENGE = "challenge"


class RecipientType(StrEnum):
    CLASSROOM = "classroom"
    USER = "user"


class RecipientStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


class FeedbackPolicy(StrEnum):
    IMMEDIATE = "immediate"
    AFTER_SUBMISSION = "after_submission"
    AFTER_DUE_DATE = "after_due_date"
    MANUAL_RELEASE = "manual_release"


class AnswerKeyPolicy(StrEnum):
    NEVER = "never"
    AFTER_SUBMISSION = "after_submission"
    AFTER_DUE_DATE = "after_due_date"
    MANUAL_RELEASE = "manual_release"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_TEXT = "short_text"
    NUMERIC = "numeric"
    MULTIPLE_SELECT = "multiple_select"
    ORDERING = "ordering"
    MATCHING = "matching"
    ESSAY = "essay"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"
    REOPENED = "reopened"
    CANCELED = "canceled"


class NotificationStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class MaterialAssignment(Base):
    __tablename__ = "material_assignments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pedagogical_packages.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    assessment_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_versions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_by_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    instructions: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    assignment_type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, name="assignment_type"), nullable=False
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"),
        default=AssignmentStatus.DRAFT,
        nullable=False,
    )
    material_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    maximum_score: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    minimum_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_policy: Mapped[FeedbackPolicy] = mapped_column(
        Enum(FeedbackPolicy, name="feedback_policy"),
        default=FeedbackPolicy.AFTER_SUBMISSION,
        nullable=False,
    )
    answer_key_policy: Mapped[AnswerKeyPolicy] = mapped_column(
        Enum(AnswerKeyPolicy, name="answer_key_policy"),
        default=AnswerKeyPolicy.AFTER_DUE_DATE,
        nullable=False,
    )
    randomize_questions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    randomize_options: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_penalty_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    show_result_immediately: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    results_released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    recipients: Mapped[list["AssignmentRecipient"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", lazy="selectin"
    )
    questions: Mapped[list["AssignmentQuestion"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentQuestion.position",
        lazy="selectin",
    )
    attempts: Mapped[list["StudentAttempt"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan", lazy="selectin"
    )


class AssignmentRecipient(Base):
    __tablename__ = "assignment_recipients"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id", "classroom_id", "user_id", name="uq_assignment_recipient_target"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True
    )
    recipient_type: Mapped[RecipientType] = mapped_column(
        Enum(RecipientType, name="assignment_recipient_type"), nullable=False
    )
    classroom_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), index=True, nullable=True
    )
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    status: Mapped[RecipientStatus] = mapped_column(
        Enum(RecipientStatus, name="assignment_recipient_status"),
        default=RecipientStatus.ACTIVE,
        nullable=False,
    )
    available_from_override: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at_override: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    maximum_attempts_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_limit_minutes_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accommodations: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assignment: Mapped[MaterialAssignment] = relationship(back_populates="recipients")


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "position", name="uq_assignment_question_position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True
    )
    package_material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("package_materials.id", ondelete="SET NULL"), index=True, nullable=True
    )
    question_bank_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("question_bank_items.id", ondelete="SET NULL"), index=True, nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="assignment_question_type"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text(), nullable=False)
    options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    curriculum_skill_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    ct_pillar_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    manual_grading: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), default="teacher", nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    item_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_snapshot_checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    is_annulled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    annulment_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assignment: Mapped[MaterialAssignment] = relationship(back_populates="questions")
    answers: Mapped[list["StudentAnswer"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", lazy="selectin"
    )


class StudentAttempt(Base):
    __tablename__ = "student_attempts"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id", "student_id", "attempt_number", name="uq_student_assignment_attempt"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="student_attempt_status"),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    teacher_feedback: Mapped[str | None] = mapped_column(Text(), nullable=True)
    grading_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_penalty_applied: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_limit_minutes_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_attempts_snapshot: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    randomization_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    autosave_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reopened_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assessment_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assessment_versions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    grading_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    recalculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment: Mapped[MaterialAssignment] = relationship(back_populates="attempts")
    answers: Mapped[list["StudentAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", lazy="selectin"
    )


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question_answer"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_attempts.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("assignment_questions.id", ondelete="CASCADE"), index=True
    )
    answer_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    awarded_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    response_time_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    teacher_feedback: Mapped[str | None] = mapped_column(Text(), nullable=True)
    corrected_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    attempt: Mapped[StudentAttempt] = relationship(back_populates="answers")
    question: Mapped[AssignmentQuestion] = relationship(back_populates="answers")


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True
    )
    attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("student_attempts.id", ondelete="CASCADE"), index=True, nullable=True
    )
    question_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assignment_questions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    assignment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("material_assignments.id", ondelete="CASCADE"), index=True, nullable=True
    )
    notification_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    message: Mapped[str] = mapped_column(Text(), nullable=False)
    action_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.UNREAD,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
