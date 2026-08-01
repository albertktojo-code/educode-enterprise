from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
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


class ComicReaderPreference(TimestampMixin, Base):
    __tablename__ = "comic_reader_preferences"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_comic_reader_preference_user"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="USER")


class ComicReadingCheckpoint(TimestampMixin, Base):
    __tablename__ = "comic_reading_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "release_id", "user_id", name="uq_comic_reading_checkpoint"
        ),
        Index("ix_comic_reading_checkpoint_progress", "organization_id", "user_id", "updated_at"),
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
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    panel_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed_panels: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reader_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="PAGE")
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComicReaderBookmark(TimestampMixin, Base):
    __tablename__ = "comic_reader_bookmarks"
    __table_args__ = (
        Index("ix_comic_reader_bookmarks_user", "organization_id", "user_id", "release_id"),
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
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")


class ComicNarrationTrack(TimestampMixin, Base):
    __tablename__ = "comic_narration_tracks"
    __table_args__ = (
        Index(
            "ix_comic_narration_release",
            "organization_id", "release_id", "language", "page_number", "panel_number"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int | None] = mapped_column(Integer)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="BROWSER_TTS")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="pt-BR")
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    audio_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("institutional_assets.id", ondelete="SET NULL")
    )
    audio_url: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    voice_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="READY")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class ComicGlossaryTerm(TimestampMixin, Base):
    __tablename__ = "comic_glossary_terms"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "release_id", "normalized_term", name="uq_comic_glossary_term"
        ),
        Index(
            "ix_comic_glossary_release",
            "organization_id", "release_id", "page_number", "panel_number"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    term: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_term: Mapped[str] = mapped_column(String(120), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    simplified_definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    page_number: Mapped[int | None] = mapped_column(Integer)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    pronunciation: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )


class ComicPresentationSession(TimestampMixin, Base):
    __tablename__ = "comic_presentation_sessions"
    __table_args__ = (
        UniqueConstraint("organization_id", "join_code", name="uq_comic_presentation_join_code"),
        Index("ix_comic_presentation_status", "organization_id", "status", "updated_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    presenter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    join_code: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    current_page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_panel: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reveal_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    allow_audience_join: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_audience: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reveal_mode: Mapped[str] = mapped_column(String(30), nullable=False, default="PANEL")
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    presenter_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComicPresentationAudience(TimestampMixin, Base):
    __tablename__ = "comic_presentation_audience"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "presentation_session_id", "user_id",
            name="uq_comic_presentation_audience"
        ),
        Index(
            "ix_comic_presentation_audience_status",
            "organization_id", "presentation_session_id", "status"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    presentation_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comic_presentation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="JOINED")
    local_preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ComicEmbeddedAssessmentLink(TimestampMixin, Base):
    __tablename__ = "comic_embedded_assessment_links"
    __table_args__ = (
        Index(
            "ix_comic_embedded_assessment_position",
            "organization_id", "release_id", "page_number", "panel_number", "display_order"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comic_editorial_releases.id", ondelete="CASCADE"), nullable=False
    )
    question_bank_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("question_bank_items.id", ondelete="RESTRICT"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_assignments.id", ondelete="SET NULL")
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    panel_number: Mapped[int | None] = mapped_column(Integer)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reveal_rule: Mapped[str] = mapped_column(String(40), nullable=False, default="ON_REACH")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
