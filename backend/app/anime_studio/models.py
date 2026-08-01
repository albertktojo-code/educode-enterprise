from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnimeProject(Base):
    __tablename__ = "anime_projects"
    __table_args__ = (
        CheckConstraint("width BETWEEN 320 AND 7680", name="ck_anime_project_width"),
        CheckConstraint("height BETWEEN 240 AND 4320", name="ck_anime_project_height"),
        CheckConstraint("fps BETWEEN 1 AND 60", name="ck_anime_project_fps"),
        CheckConstraint("revision >= 1", name="ck_anime_project_revision"),
        Index("ix_anime_projects_org_status", "organization_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    generation_project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="SET NULL"), index=True
    )
    rag_context_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="SET NULL"), index=True
    )
    teacher_studio_draft_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("teacher_studio_drafts.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    synopsis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    style_preset_code: Mapped[str] = mapped_column(
        String(80), default="anime_school", nullable=False
    )
    aspect_ratio: Mapped[str] = mapped_column(String(12), default="16:9", nullable=False)
    width: Mapped[int] = mapped_column(Integer, default=1920, nullable=False)
    height: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="pt-BR", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    accessibility_options: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    production_notes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    scenes: Mapped[list[AnimeScene]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AnimeScene.position",
        lazy="selectin",
    )
    audio_tracks: Mapped[list[AnimeAudioTrack]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AnimeAudioTrack.start_ms",
        lazy="selectin",
    )
    captions: Mapped[list[AnimeCaptionCue]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AnimeCaptionCue.cue_order",
        lazy="selectin",
    )
    renders: Mapped[list[AnimeRender]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="AnimeRender.revision.desc()",
        lazy="selectin",
    )


class AnimeScene(Base):
    __tablename__ = "anime_scenes"
    __table_args__ = (
        UniqueConstraint("project_id", "position", name="uq_anime_scene_position"),
        CheckConstraint("duration_ms BETWEEN 500 AND 600000", name="ck_anime_scene_duration"),
        CheckConstraint("revision >= 1", name="ck_anime_scene_revision"),
        Index("ix_anime_scenes_org_project", "organization_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("anime_projects.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=5000, nullable=False)
    visual_asset_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutional_asset_files.id", ondelete="SET NULL"), index=True
    )
    source_comic_page_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_pages.id", ondelete="SET NULL"), index=True
    )
    source_comic_panel_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_panels.id", ondelete="SET NULL"), index=True
    )
    screenplay_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    visual_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    camera_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    transition_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    continuity_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    pedagogical_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[AnimeProject] = relationship(back_populates="scenes")


class AnimeAudioTrack(Base):
    __tablename__ = "anime_audio_tracks"
    __table_args__ = (
        CheckConstraint("start_ms >= 0", name="ck_anime_audio_start"),
        CheckConstraint("duration_ms IS NULL OR duration_ms > 0", name="ck_anime_audio_duration"),
        CheckConstraint("trim_start_ms >= 0", name="ck_anime_audio_trim"),
        CheckConstraint("volume BETWEEN 0 AND 2", name="ck_anime_audio_volume"),
        Index("ix_anime_audio_org_project", "organization_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("anime_projects.id", ondelete="CASCADE"), index=True
    )
    scene_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("anime_scenes.id", ondelete="CASCADE"), index=True
    )
    track_kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    language: Mapped[str] = mapped_column(String(20), default="pt-BR", nullable=False)
    asset_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutional_asset_files.id", ondelete="SET NULL"), index=True
    )
    transcript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    speaker: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    trim_start_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    fade_in_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fade_out_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voice_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[AnimeProject] = relationship(back_populates="audio_tracks")


class AnimeCaptionCue(Base):
    __tablename__ = "anime_caption_cues"
    __table_args__ = (
        UniqueConstraint("project_id", "language", "cue_order", name="uq_anime_caption_order"),
        CheckConstraint("start_ms >= 0", name="ck_anime_caption_start"),
        CheckConstraint("end_ms > start_ms", name="ck_anime_caption_end"),
        Index("ix_anime_caption_org_project", "organization_id", "project_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("anime_projects.id", ondelete="CASCADE"), index=True
    )
    scene_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("anime_scenes.id", ondelete="CASCADE"), index=True
    )
    language: Mapped[str] = mapped_column(String(20), default="pt-BR", nullable=False)
    cue_order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    speaker: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    cue_kind: Mapped[str] = mapped_column(String(32), default="dialogue", nullable=False)
    accessibility_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[AnimeProject] = relationship(back_populates="captions")


class AnimeRender(Base):
    __tablename__ = "anime_renders"
    __table_args__ = (
        UniqueConstraint("project_id", "revision", name="uq_anime_render_revision"),
        CheckConstraint("revision >= 1", name="ck_anime_render_revision"),
        Index("ix_anime_renders_org_status", "organization_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("anime_projects.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    background_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("background_jobs.id", ondelete="SET NULL"), index=True
    )
    output_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutional_assets.id", ondelete="SET NULL"), index=True
    )
    output_asset_file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("institutional_asset_files.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True, nullable=False)
    format: Mapped[str] = mapped_column(String(20), default="mp4", nullable=False)
    video_codec: Mapped[str] = mapped_column(String(30), default="h264", nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(30), default="aac", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    render_settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    manifest_checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    review_decision: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[AnimeProject] = relationship(back_populates="renders")
