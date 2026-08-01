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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AssessmentPublication(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_publications"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_delivery_publication_version"),
        Index("ix_delivery_publications_window", "organization_id", "status", "starts_at", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    item_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    navigation_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="FREE")
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_resume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    autosave_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    delivery_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    access_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    published_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentTarget(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_targets"
    __table_args__ = (
        UniqueConstraint("organization_id", "publication_id", "target_type", "target_id", name="uq_delivery_target"),
        Index("ix_delivery_targets_lookup", "organization_id", "target_type", "target_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    custom_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class AssessmentAccommodation(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_accommodations"
    __table_args__ = (
        UniqueConstraint("organization_id", "publication_id", "student_id", name="uq_delivery_accommodation"),
        Index("ix_delivery_accommodation_student", "organization_id", "student_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    extra_time_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accessible_version_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    screen_reader_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    high_contrast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reduced_motion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    keyboard_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    simplified_language: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    custom_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    approved_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class AssessmentSession(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_sessions"
    __table_args__ = (
        Index("ix_delivery_sessions_student", "organization_id", "student_id", "status", "started_at"),
        Index("ix_delivery_sessions_publication", "organization_id", "publication_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_hub_attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_item_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resume_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reconnect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    focus_loss_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    integrity_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NORMAL")
    delivery_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    accessibility_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    device_context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AssessmentSessionItem(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_session_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "session_id", "position", name="uq_delivery_session_position"),
        UniqueConstraint("organization_id", "session_id", "question_version_id", name="uq_delivery_session_question"),
        Index("ix_delivery_session_items_session", "organization_id", "session_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    original_position: Mapped[int] = mapped_column(Integer, nullable=False)
    option_order: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_SEEN")
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AssessmentAutosave(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_autosaves"
    __table_args__ = (
        UniqueConstraint("organization_id", "session_id", "sequence_number", name="uq_delivery_autosave_sequence"),
        Index("ix_delivery_autosaves_item", "organization_id", "session_id", "session_item_id", "sequence_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    client_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACCEPTED")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AssessmentSessionEvent(TimestampMixin, Base):
    __tablename__ = "assessment_delivery_session_events"
    __table_args__ = (
        Index("ix_delivery_events_session", "organization_id", "session_id", "occurred_at"),
        Index("ix_delivery_events_review", "organization_id", "severity", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="INFO")
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="CLIENT")
    client_sequence: Mapped[int | None] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_payload: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text)
