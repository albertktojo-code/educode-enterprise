from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Index, Integer,
    String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .compat import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


class ComicReaderEvent(Base):
    __tablename__ = "comic_reader_events"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", "client_event_id",
            name="uq_comic_reader_event_client",
        ),
        Index(
            "ix_comic_reader_event_release_time",
            "organization_id", "release_id", "occurred_at",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    presentation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_presentation_sessions.id", ondelete="SET NULL")
    )
    client_event_id: Mapped[str] = mapped_column(String(80), nullable=False)
    session_key: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ComicReaderSessionMetric(TimestampMixin, Base):
    __tablename__ = "comic_reader_session_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "release_id", "user_id", "session_key",
            name="uq_comic_reader_session_metric",
        ),
        Index(
            "ix_comic_reader_session_period",
            "organization_id", "release_id", "started_at",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_key: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    panel_views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revisits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    glossary_opens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    narration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accessibility_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assessment_opens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    presentation_syncs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ComicReaderContentMetric(TimestampMixin, Base):
    __tablename__ = "comic_reader_content_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "release_id", "metric_date", "dimension_key",
            name="uq_comic_reader_content_metric",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(80), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    viewer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revisit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    glossary_opens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    narration_starts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assessment_opens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ComicReaderCohortMetric(TimestampMixin, Base):
    __tablename__ = "comic_reader_cohort_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "classroom_id", "release_id", "period_start", "period_end",
            name="uq_comic_reader_cohort_metric",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    enrolled_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_active_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    median_progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    presentation_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    narration_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accessibility_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    privacy_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ComicReaderLearningMetric(TimestampMixin, Base):
    __tablename__ = "comic_reader_learning_metrics"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "scope_key", "release_id", "assignment_id",
            "period_start", "period_end",
            name="uq_comic_reader_learning_metric",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_assignments.id", ondelete="CASCADE"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_active_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    average_score_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reading_score_correlation: Mapped[float | None] = mapped_column(Float)
    completion_score_delta: Mapped[float | None] = mapped_column(Float)
    interpretation: Mapped[str] = mapped_column(String(80), nullable=False, default="INSUFFICIENT_DATA")
    privacy_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
