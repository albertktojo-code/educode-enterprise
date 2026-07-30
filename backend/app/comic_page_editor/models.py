from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class HQLayoutTemplate(TimestampMixin, Base):
    __tablename__ = "hq_layout_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", "version", name="uq_hq_layout_template_version"),
        Index("ix_hq_layout_templates_filter", "organization_id", "panel_count", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(24), nullable=False, default="1.0.0")
    panel_count: Mapped[int] = mapped_column(Integer, nullable=False)
    orientation: Mapped[str] = mapped_column(String(24), nullable=False, default="PORTRAIT")
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="TRADITIONAL")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grid_definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    preview_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HQEditorPage(TimestampMixin, Base):
    __tablename__ = "hq_editor_pages"
    __table_args__ = (
        UniqueConstraint("organization_id", "comic_project_id", "page_number", name="uq_hq_editor_page_number"),
        Index("ix_hq_editor_pages_project", "organization_id", "comic_project_id", "page_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    layout_template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    page_type: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="STORY",
    )
    title: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    page_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    page_height: Mapped[int] = mapped_column(Integer, nullable=False, default=1600)
    background_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    accessibility_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_layers: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    preservation_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    continuity_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    cover_generation: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HQEditorPanel(TimestampMixin, Base):
    __tablename__ = "hq_editor_panels"
    __table_args__ = (
        UniqueConstraint("organization_id", "page_id", "panel_order", name="uq_hq_editor_panel_order"),
        Index("ix_hq_editor_panels_page", "organization_id", "page_id", "panel_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    panel_order: Mapped[int] = mapped_column(Integer, nullable=False)
    shape: Mapped[str] = mapped_column(String(24), nullable=False, default="RECTANGLE")
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    aspect_ratio: Mapped[str] = mapped_column(String(16), nullable=False, default="4:3")
    scene_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    negative_prompt: Mapped[str | None] = mapped_column(Text)
    image_reference: Mapped[str | None] = mapped_column(Text)
    generated_asset_reference: Mapped[str | None] = mapped_column(Text)
    generation_status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    locked_elements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    pedagogical_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    accessibility_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class HQPanelTextLayer(TimestampMixin, Base):
    __tablename__ = "hq_panel_text_layers"
    __table_args__ = (Index("ix_hq_panel_text_layers_panel", "organization_id", "panel_id", "layer_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    panel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    layer_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    layer_type: Mapped[str] = mapped_column(String(24), nullable=False)
    speaker_name: Mapped[str | None] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=0.4)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    style: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bubble_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    accessibility_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    review_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="DRAFT"
    )
    linked_character_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )


class HQEditorSnapshot(TimestampMixin, Base):
    __tablename__ = "hq_editor_snapshots"
    __table_args__ = (Index("ix_hq_editor_snapshots_project", "organization_id", "comic_project_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_type: Mapped[str] = mapped_column(String(24), nullable=False, default="AUTOSAVE")
    label: Mapped[str | None] = mapped_column(String(180))
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    data_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HQGenerationJob(TimestampMixin, Base):
    __tablename__ = "hq_generation_jobs"
    __table_args__ = (Index("ix_hq_generation_jobs_project", "organization_id", "comic_project_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(36), nullable=False, default="QUEUED")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_step_code: Mapped[str | None] = mapped_column(String(80))
    total_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_panels: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_panels: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_panels: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    continue_in_background: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class HQGenerationStep(TimestampMixin, Base):
    __tablename__ = "hq_generation_steps"
    __table_args__ = (
        UniqueConstraint("organization_id", "generation_job_id", "step_order", name="uq_hq_generation_step_order"),
        Index("ix_hq_generation_steps_job", "organization_id", "generation_job_id", "step_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    generation_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    playful_message: Mapped[str] = mapped_column(String(260), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    progress_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    page_number: Mapped[int | None] = mapped_column(Integer)
    panel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class HQEditorAutosave(TimestampMixin, Base):
    __tablename__ = "hq_editor_autosaves"
    __table_args__ = (
        UniqueConstraint("organization_id", "comic_project_id", "client_id", name="uq_hq_editor_autosave_client"),
        Index("ix_hq_editor_autosaves_project", "organization_id", "comic_project_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    client_id: Mapped[str] = mapped_column(String(120), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    last_saved_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HQStoryPlan(TimestampMixin, Base):
    __tablename__ = "hq_story_plans"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "comic_project_id",
            name="uq_hq_story_plan_project",
        ),
        Index(
            "ix_hq_story_plan_project",
            "organization_id",
            "comic_project_id",
        ),
        Index(
            "ix_hq_story_plan_ai_request",
            "organization_id",
            "ai_generation_request_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    comic_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    source_mode: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="MANUAL",
    )
    total_pages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    narrative_pacing: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="BALANCED",
    )
    distribution_mode: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="AUTOMATIC",
    )
    short_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    full_script: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    page_plan: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    continuity_constraints: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    generation_instructions: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    generation_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
    )
    ai_generation_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_generation_requests.id", ondelete="SET NULL"),
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="",
    )
    revision_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    updated_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )


class HQEditorialComment(TimestampMixin, Base):
    __tablename__ = "hq_editorial_comments"
    __table_args__ = (
        Index(
            "ix_hq_editorial_comments_project_status",
            "organization_id",
            "comic_project_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_hq_editorial_comments_target",
            "organization_id",
            "target_type",
            "target_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    comic_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="OPEN"
    )
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="NORMAL"
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HQActivityBinding(TimestampMixin, Base):
    __tablename__ = "hq_activity_bindings"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "activity_page_id",
            "display_order",
            name="uq_hq_activity_page_order",
        ),
        Index(
            "ix_hq_activity_project_status",
            "organization_id",
            "comic_project_id",
            "status",
            "display_order",
        ),
        Index(
            "ix_hq_activity_question_version",
            "organization_id",
            "question_version_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_page_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_page_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_panel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    question_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    question_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    publication_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    activity_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    answer_key: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    pedagogical_links: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    accessibility: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    difficulty: Mapped[str] = mapped_column(String(24), nullable=False, default="BASIC")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    teacher_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HQActivityFeedbackProfile(TimestampMixin, Base):
    __tablename__ = "hq_activity_feedback_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "activity_binding_id",
            name="uq_hq_activity_feedback_profile",
        ),
        Index(
            "ix_hq_activity_feedback_status",
            "organization_id",
            "status",
            "correction_mode",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    activity_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    rubric_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    correction_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="AUTOMATIC")
    feedback_templates: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    graduated_hints: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    common_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    review_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    appeal_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class HQActivityDeliveryLink(TimestampMixin, Base):
    __tablename__ = "hq_activity_delivery_links"
    __table_args__ = (
        UniqueConstraint("organization_id","comic_project_id","publication_id",name="uq_hq_activity_delivery_publication"),
        Index("ix_hq_activity_delivery_status","organization_id","status","published_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    delivery_mode: Mapped[str] = mapped_column(String(24),nullable=False,default="HQ_FLOW")
    reader_required: Mapped[bool] = mapped_column(Boolean,nullable=False,default=True)
    release_answer_key: Mapped[str] = mapped_column(String(24),nullable=False,default="AFTER_SUBMISSION")
    monitoring_settings: Mapped[dict[str,Any]] = mapped_column(JSONB,nullable=False,default=dict)
    status: Mapped[str] = mapped_column(String(24),nullable=False,default="DRAFT")
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    published_by_user_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True))
    published_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))


class HQStudentExperienceState(TimestampMixin, Base):
    __tablename__ = "hq_student_experience_states"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "publication_id",
            "student_id",
            name="uq_hq_student_experience_publication",
        ),
        Index(
            "ix_hq_student_experience_progress",
            "organization_id",
            "publication_id",
            "current_stage",
            "updated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assessment_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    current_stage: Mapped[str] = mapped_column(String(24), nullable=False, default="READING")
    current_page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_panel_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_activity_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reading_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    activity_progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    answered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_activity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resume_token: Mapped[str] = mapped_column(String(96), nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    navigation_state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_feedback: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class HQLearningAnalyticsSnapshot(TimestampMixin, Base):
    __tablename__ = "hq_learning_analytics_snapshots"
    __table_args__ = (
        UniqueConstraint("organization_id","publication_id","scope_type","scope_id","period_start","period_end",name="uq_hq_learning_analytics_snapshot"),
        Index("ix_hq_learning_analytics_lookup","organization_id","publication_id","scope_type","generated_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    comic_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    publication_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    scope_type: Mapped[str] = mapped_column(String(24),nullable=False,default="PUBLICATION")
    scope_id: Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True))
    period_start: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime|None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict[str,Any]] = mapped_column(JSONB,nullable=False,default=dict)
    skill_metrics: Mapped[list[dict[str,Any]]] = mapped_column(JSONB,nullable=False,default=list)
    page_metrics: Mapped[list[dict[str,Any]]] = mapped_column(JSONB,nullable=False,default=list)
    activity_metrics: Mapped[list[dict[str,Any]]] = mapped_column(JSONB,nullable=False,default=list)
    correlations: Mapped[list[dict[str,Any]]] = mapped_column(JSONB,nullable=False,default=list)
    alerts: Mapped[list[dict[str,Any]]] = mapped_column(JSONB,nullable=False,default=list)
    generated_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,default=lambda:datetime.now(UTC))
