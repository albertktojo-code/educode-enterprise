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


class ComicStatus(StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class PageFormat(StrEnum):
    A4 = "a4"
    SQUARE = "square"
    MOBILE = "mobile"
    INSTAGRAM = "instagram"
    PRESENTATION_16_9 = "presentation_16_9"
    CUSTOM = "custom"


class PageOrientation(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class LayoutMode(StrEnum):
    TEMPLATE = "template"
    FREE = "free"
    RECOMMENDED = "recommended"


class ReadingDirection(StrEnum):
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"


class PanelShape(StrEnum):
    RECTANGLE = "rectangle"
    SQUARE = "square"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    CIRCLE = "circle"
    OVAL = "oval"
    PANORAMIC = "panoramic"
    CUSTOM = "custom"


class PanelSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    FULL_PAGE = "full_page"
    CUSTOM = "custom"


class PanelStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    VALIDATED = "validated"
    LOCKED = "locked"


class BalloonType(StrEnum):
    SPEECH = "speech"
    THOUGHT = "thought"
    SHOUT = "shout"
    WHISPER = "whisper"
    NARRATION = "narration"
    CAPTION = "caption"
    PEDAGOGICAL = "pedagogical"


class GenerationScope(StrEnum):
    COMIC = "comic"
    PAGE = "page"
    PANEL = "panel"
    BALLOONS = "balloons"
    DIALOGUE = "dialogue"
    SCENE = "scene"
    FROM_PANEL = "from_panel"


class GenerationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ComicVersionScope(StrEnum):
    INITIAL = "initial"
    COMIC = "comic"
    PAGE = "page"
    PANEL = "panel"
    BALLOON = "balloon"
    RESTORE = "restore"


class ReviewSpecialty(StrEnum):
    NARRATIVE = "narrative"
    PEDAGOGICAL = "pedagogical"
    VISUAL = "visual"
    ACCESSIBILITY = "accessibility"


class ReviewDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class ReviewCommentStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class EditOperationStatus(StrEnum):
    APPLIED = "applied"
    UNDONE = "undone"
    REDONE = "redone"


class PreviewReviewStatus(StrEnum):
    NOT_REVIEWED = "not_reviewed"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    LOCKED = "locked"


class GeneratedComic(Base):
    __tablename__ = "generated_comics"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    generation_project_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="CASCADE"), index=True
    )
    rag_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="RESTRICT"), index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_by_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    synopsis: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    status: Mapped[ComicStatus] = mapped_column(
        Enum(ComicStatus, name="comic_status"), default=ComicStatus.DRAFT, nullable=False
    )
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    narrative_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    layout_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    story_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    continuity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pedagogical_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    art_direction: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    canvas_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    publication_status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    review_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    autosave_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edit_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_editor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    last_editor_name_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    last_editor_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canvas_readiness_status: Mapped[str] = mapped_column(
        String(40), default="not_ready", nullable=False
    )
    canvas_readiness_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preview_status: Mapped[PreviewReviewStatus] = mapped_column(
        Enum(PreviewReviewStatus, name="comic_preview_review_status"),
        default=PreviewReviewStatus.NOT_REVIEWED,
        nullable=False,
    )
    preview_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pages: Mapped[list["ComicPage"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="comic",
        order_by="ComicPage.page_number",
        lazy="selectin",
    )
    versions: Mapped[list["ComicVersion"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="comic",
        order_by=lambda: ComicVersion.version_number.desc(),
        lazy="selectin",
    )
    generation_runs: Mapped[list["ComicGenerationRun"]] = relationship(
        cascade="all, delete-orphan", back_populates="comic", lazy="selectin"
    )
    review_comments: Mapped[list["ComicReviewComment"]] = relationship(
        cascade="all, delete-orphan", back_populates="comic", lazy="selectin"
    )
    review_approvals: Mapped[list["ComicReviewApproval"]] = relationship(
        cascade="all, delete-orphan", back_populates="comic", lazy="selectin"
    )
    regeneration_proposals: Mapped[list["ComicRegenerationProposal"]] = relationship(
        cascade="all, delete-orphan", back_populates="comic", lazy="selectin"
    )
    edit_operations: Mapped[list["ComicEditOperation"]] = relationship(
        cascade="all, delete-orphan", back_populates="comic", lazy="selectin"
    )


class ComicPage(Base):
    __tablename__ = "comic_pages"
    __table_args__ = (UniqueConstraint("comic_id", "page_number", name="uq_comic_page_number"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(220), nullable=True)
    page_format: Mapped[PageFormat] = mapped_column(
        Enum(PageFormat, name="comic_page_format"), default=PageFormat.A4, nullable=False
    )
    orientation: Mapped[PageOrientation] = mapped_column(
        Enum(PageOrientation, name="comic_page_orientation"),
        default=PageOrientation.PORTRAIT,
        nullable=False,
    )
    layout_mode: Mapped[LayoutMode] = mapped_column(
        Enum(LayoutMode, name="comic_layout_mode"), default=LayoutMode.TEMPLATE, nullable=False
    )
    layout_template: Mapped[str] = mapped_column(String(80), default="grid_2x2", nullable=False)
    reading_direction: Mapped[ReadingDirection] = mapped_column(
        Enum(ReadingDirection, name="comic_reading_direction"),
        default=ReadingDirection.LEFT_TO_RIGHT,
        nullable=False,
    )
    panel_count: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    width: Mapped[float] = mapped_column(Float, default=210.0, nullable=False)
    height: Mapped[float] = mapped_column(Float, default=297.0, nullable=False)
    margins: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    page_role: Mapped[str] = mapped_column(String(40), default="story", nullable=False)
    background_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    guides_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    preview_review_status: Mapped[PreviewReviewStatus] = mapped_column(
        Enum(PreviewReviewStatus, name="comic_preview_review_status"),
        default=PreviewReviewStatus.NOT_REVIEWED,
        nullable=False,
    )
    preview_reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    preview_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preview_review_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    comic: Mapped[GeneratedComic] = relationship(back_populates="pages")
    panels: Mapped[list["ComicPanel"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="page",
        order_by="ComicPanel.reading_order",
        lazy="selectin",
    )


class ComicPanel(Base):
    __tablename__ = "comic_panels"
    __table_args__ = (
        UniqueConstraint("page_id", "panel_number", name="uq_comic_panel_number"),
        UniqueConstraint("page_id", "reading_order", name="uq_comic_panel_reading_order"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("comic_pages.id", ondelete="CASCADE"), index=True
    )
    panel_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False)
    shape: Mapped[PanelShape] = mapped_column(
        Enum(PanelShape, name="comic_panel_shape"), default=PanelShape.RECTANGLE, nullable=False
    )
    size_category: Mapped[PanelSize] = mapped_column(
        Enum(PanelSize, name="comic_panel_size"), default=PanelSize.MEDIUM, nullable=False
    )
    position_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    width: Mapped[float] = mapped_column(Float, default=48.0, nullable=False)
    height: Mapped[float] = mapped_column(Float, default=48.0, nullable=False)
    border_style: Mapped[str] = mapped_column(String(40), default="solid", nullable=False)
    border_width: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    rotation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    z_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_full_bleed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clipping_mode: Mapped[str] = mapped_column(String(40), default="cover", nullable=False)
    narrative_goal: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    pedagogical_goal: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    ct_pillar_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scene_description: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    previous_panel_summary: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    next_panel_hook: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    initial_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    final_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    emotion: Mapped[str] = mapped_column(String(80), default="curiosity", nullable=False)
    plot_function: Mapped[str] = mapped_column(String(100), default="development", nullable=False)
    continuity_notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[PanelStatus] = mapped_column(
        Enum(PanelStatus, name="comic_panel_status"), default=PanelStatus.DRAFT, nullable=False
    )
    locked_elements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    visual_prompt: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    frozen_assets: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    pacing: Mapped[str] = mapped_column(String(40), default="moderate", nullable=False)
    image_asset_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    audio_description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    text_word_limit: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    preview_review_status: Mapped[PreviewReviewStatus] = mapped_column(
        Enum(PreviewReviewStatus, name="comic_preview_review_status"),
        default=PreviewReviewStatus.NOT_REVIEWED,
        nullable=False,
    )
    preview_reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    preview_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preview_review_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    page: Mapped[ComicPage] = relationship(back_populates="panels")
    balloons: Mapped[list["ComicBalloon"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="panel",
        order_by="ComicBalloon.sequence_number",
        lazy="selectin",
        foreign_keys="ComicBalloon.panel_id",
    )


class ComicBalloon(Base):
    __tablename__ = "comic_balloons"
    __table_args__ = (
        UniqueConstraint("panel_id", "sequence_number", name="uq_comic_balloon_sequence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    panel_id: Mapped[UUID] = mapped_column(
        ForeignKey("comic_panels.id", ondelete="CASCADE"), index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_character_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("creative_items.id", ondelete="SET NULL"), index=True, nullable=True
    )
    speaker_name_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    balloon_type: Mapped[BalloonType] = mapped_column(
        Enum(BalloonType, name="comic_balloon_type"), default=BalloonType.SPEECH, nullable=False
    )
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    emotion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    responds_to_balloon_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_balloons.id", ondelete="SET NULL"), index=True, nullable=True
    )
    pedagogical_function: Mapped[str | None] = mapped_column(String(120), nullable=True)
    position_x: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    width: Mapped[float] = mapped_column(Float, default=40.0, nullable=False)
    height: Mapped[float] = mapped_column(Float, default=20.0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    layer_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    panel: Mapped[ComicPanel] = relationship(back_populates="balloons", foreign_keys=[panel_id])


class ComicVersion(Base):
    __tablename__ = "comic_versions"
    __table_args__ = (
        UniqueConstraint("comic_id", "version_number", name="uq_comic_version_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[ComicVersionScope] = mapped_column(
        Enum(ComicVersionScope, name="comic_version_scope"), nullable=False
    )
    target_page_id: Mapped[UUID | None] = mapped_column(nullable=True)
    target_panel_id: Mapped[UUID | None] = mapped_column(nullable=True)
    target_balloon_id: Mapped[UUID | None] = mapped_column(nullable=True)
    change_description: Mapped[str] = mapped_column(Text(), nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    comic: Mapped[GeneratedComic] = relationship(back_populates="versions")


class ComicGenerationRun(Base):
    __tablename__ = "comic_generation_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    scope: Mapped[GenerationScope] = mapped_column(
        Enum(GenerationScope, name="comic_generation_scope"), nullable=False
    )
    target_page_id: Mapped[UUID | None] = mapped_column(nullable=True)
    target_panel_id: Mapped[UUID | None] = mapped_column(nullable=True)
    status: Mapped[GenerationRunStatus] = mapped_column(
        Enum(GenerationRunStatus, name="comic_generation_run_status"),
        default=GenerationRunStatus.PENDING,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(80), default="mock", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="narrative-mock-v1", nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    comic: Mapped[GeneratedComic] = relationship(back_populates="generation_runs")


class ComicReviewComment(Base):
    __tablename__ = "comic_review_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    page_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_pages.id", ondelete="CASCADE"), nullable=True, index=True
    )
    panel_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_panels.id", ondelete="CASCADE"), nullable=True, index=True
    )
    balloon_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("comic_balloons.id", ondelete="CASCADE"), nullable=True, index=True
    )
    author_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    author_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    specialty: Mapped[ReviewSpecialty] = mapped_column(
        Enum(ReviewSpecialty, name="comic_review_specialty"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    anchor_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    anchor_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str] = mapped_column(String(24), default="normal", nullable=False)
    status: Mapped[ReviewCommentStatus] = mapped_column(
        Enum(ReviewCommentStatus, name="comic_review_comment_status"),
        default=ReviewCommentStatus.OPEN,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comic: Mapped[GeneratedComic] = relationship(back_populates="review_comments")


class ComicReviewApproval(Base):
    __tablename__ = "comic_review_approvals"
    __table_args__ = (UniqueConstraint("comic_id", "specialty", name="uq_comic_review_specialty"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    specialty: Mapped[ReviewSpecialty] = mapped_column(
        Enum(ReviewSpecialty, name="comic_review_specialty"), nullable=False
    )
    decision: Mapped[ReviewDecision] = mapped_column(
        Enum(ReviewDecision, name="comic_review_decision"),
        default=ReviewDecision.PENDING,
        nullable=False,
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    reviewer_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    comic: Mapped[GeneratedComic] = relationship(back_populates="review_approvals")


class ComicRegenerationProposal(Base):
    __tablename__ = "comic_regeneration_proposals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    scope: Mapped[GenerationScope] = mapped_column(
        Enum(GenerationScope, name="comic_generation_scope"), nullable=False
    )
    target_page_id: Mapped[UUID | None] = mapped_column(nullable=True)
    target_panel_id: Mapped[UUID | None] = mapped_column(nullable=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    tone: Mapped[str] = mapped_column(String(80), nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text(), nullable=True)
    proposal_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, name="comic_proposal_status"),
        default=ProposalStatus.PROPOSED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comic: Mapped[GeneratedComic] = relationship(back_populates="regeneration_proposals")


class ComicEditOperation(Base):
    __tablename__ = "comic_edit_operations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    comic_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    operation_type: Mapped[str] = mapped_column(String(120), nullable=False)
    target_page_id: Mapped[UUID | None] = mapped_column(nullable=True)
    target_panel_id: Mapped[UUID | None] = mapped_column(nullable=True)
    target_balloon_id: Mapped[UUID | None] = mapped_column(nullable=True)
    before_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    after_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[EditOperationStatus] = mapped_column(
        Enum(EditOperationStatus, name="comic_edit_operation_status"),
        default=EditOperationStatus.APPLIED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comic: Mapped[GeneratedComic] = relationship(back_populates="edit_operations")
