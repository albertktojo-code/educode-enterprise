from datetime import datetime
from enum import StrEnum
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


class SourceMode(StrEnum):
    DOCUMENT = "document"
    AI = "ai"
    TEACHER_TEXT = "teacher_text"
    HYBRID = "hybrid"


class SourceType(StrEnum):
    DOCUMENT = "document"
    TEACHER_TEXT = "teacher_text"
    AI_KNOWLEDGE = "ai_knowledge"
    MANUAL_INSTRUCTION = "manual_instruction"


class FidelityLevel(StrEnum):
    STRICT = "strict"
    BALANCED = "balanced"
    CREATIVE = "creative"


class IntegrationMode(StrEnum):
    SUBJECT_FOCUS = "subject_focus"
    COMPUTATIONAL_THINKING_FOCUS = "computational_thinking_focus"
    BALANCED = "balanced"


class DifficultyLevel(StrEnum):
    INTRODUCTORY = "introductory"
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PrivacyLevel(StrEnum):
    PRIVATE = "private"
    TEAM = "team"
    CLASSROOM = "classroom"
    ORGANIZATION = "organization"


class GenerationStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    CONFIRMED = "confirmed"
    ARCHIVED = "archived"


class PillarRelevance(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    COMPLEMENTARY = "complementary"


class AssessmentDesign(StrEnum):
    NONE = "none"
    DIAGNOSTIC = "diagnostic"
    PRE_POST = "pre_post"
    EXPERIMENTAL_CONTROL = "experimental_control"
    FORMATIVE = "formative"
    SUMMATIVE = "summative"
    TAM = "tam"


class LearningUnit(Base):
    __tablename__ = "learning_units"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chapters.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    start_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    school_year: Mapped[str | None] = mapped_column(String(80), nullable=True)
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level"),
        default=DifficultyLevel.INTERMEDIATE,
        nullable=False,
    )
    disciplinary_objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ComputationalThinkingPillar(Base):
    __tablename__ = "computational_thinking_pillars"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    pedagogical_examples: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class GenerationProject(Base):
    __tablename__ = "generation_projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    created_by_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    source_mode: Mapped[SourceMode] = mapped_column(
        Enum(SourceMode, name="source_mode"),
        nullable=False,
    )
    subject_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    custom_subject_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    school_year: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic: Mapped[str] = mapped_column(String(240), nullable=False)
    disciplinary_objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    computational_thinking_objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    teacher_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    teacher_instructions: Mapped[str | None] = mapped_column(Text(), nullable=True)
    allow_ai_expansion: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fidelity_level: Mapped[FidelityLevel] = mapped_column(
        Enum(FidelityLevel, name="fidelity_level"),
        default=FidelityLevel.BALANCED,
        nullable=False,
    )
    integration_mode: Mapped[IntegrationMode] = mapped_column(
        Enum(IntegrationMode, name="integration_mode"),
        default=IntegrationMode.BALANCED,
        nullable=False,
    )
    difficulty_level: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="generation_difficulty_level"),
        default=DifficultyLevel.INTERMEDIATE,
        nullable=False,
    )
    privacy_level: Mapped[PrivacyLevel] = mapped_column(
        Enum(PrivacyLevel, name="privacy_level"),
        default=PrivacyLevel.PRIVATE,
        nullable=False,
    )
    credit_name: Mapped[str] = mapped_column(String(180), nullable=False)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bncc_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    desired_materials: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    accessibility_options: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_priority: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assessment_design: Mapped[AssessmentDesign] = mapped_column(
        Enum(AssessmentDesign, name="assessment_design"),
        default=AssessmentDesign.NONE,
        nullable=False,
    )
    assessment_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    cognitive_levels: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    measurable_objectives: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evaluation_plan: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    author_credit_settings: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus, name="generation_status"),
        default=GenerationStatus.DRAFT,
        nullable=False,
    )
    mock_proposal: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    pillars: Mapped[list["GenerationProjectPillar"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="generation_project",
        lazy="selectin",
    )
    sources: Mapped[list["GenerationSource"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="generation_project",
        lazy="selectin",
    )


class GenerationProjectPillar(Base):
    __tablename__ = "generation_project_pillars"
    __table_args__ = (
        UniqueConstraint(
            "generation_project_id",
            "pillar_id",
            name="uq_generation_project_pillar",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_project_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="CASCADE"),
        index=True,
    )
    pillar_id: Mapped[UUID] = mapped_column(
        ForeignKey("computational_thinking_pillars.id", ondelete="RESTRICT"),
        index=True,
    )
    relevance: Mapped[PillarRelevance] = mapped_column(
        Enum(PillarRelevance, name="pillar_relevance"),
        default=PillarRelevance.HIGH,
        nullable=False,
    )
    application_description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    selected_by: Mapped[str] = mapped_column(String(30), default="teacher", nullable=False)

    generation_project: Mapped[GenerationProject] = relationship(back_populates="pillars")
    pillar: Mapped[ComputationalThinkingPillar] = relationship(lazy="joined")


class GenerationSource(Base):
    __tablename__ = "generation_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_project_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="CASCADE"),
        index=True,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="generation_source_type"),
        nullable=False,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chapters.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    learning_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_units.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    content_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text(), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_ai_expansion: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    generation_project: Mapped[GenerationProject] = relationship(back_populates="sources")
