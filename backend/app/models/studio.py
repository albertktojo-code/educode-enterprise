from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudioCreationMode(StrEnum):
    QUICK = "quick"
    ADVANCED = "advanced"


class StudioMaterialType(StrEnum):
    COMIC = "comic"
    QUIZ = "quiz"
    EXERCISE = "exercise"
    ACTIVITY = "activity"
    GAME = "game"
    LESSON_PLAN = "lesson_plan"
    TEACHING_SEQUENCE = "teaching_sequence"
    ANSWER_KEY = "answer_key"
    TEACHER_GUIDE = "teacher_guide"


class StudioDraftStatus(StrEnum):
    DRAFT = "draft"
    CONFIGURED = "configured"
    GENERATING = "generating"
    READY = "ready"
    ARCHIVED = "archived"


class PackageStatus(StrEnum):
    DRAFT = "draft"
    PREPARING = "preparing"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    ARCHIVED = "archived"


class PackageMaterialStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"


class PublicationReadiness(StrEnum):
    NOT_READY = "not_ready"
    READY_WITH_WARNINGS = "ready_with_warnings"
    READY = "ready"


class TeacherStudioDraft(Base):
    __tablename__ = "teacher_studio_drafts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    generation_project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    rag_context_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    creation_mode: Mapped[StudioCreationMode] = mapped_column(
        Enum(StudioCreationMode, name="studio_creation_mode"),
        default=StudioCreationMode.QUICK,
        nullable=False,
    )
    primary_material: Mapped[StudioMaterialType] = mapped_column(
        Enum(StudioMaterialType, name="studio_material_type"),
        default=StudioMaterialType.COMIC,
        nullable=False,
    )
    subject_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    school_year: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    topic: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    objective: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    current_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    wizard_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    selected_outputs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    page_plan: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    art_direction: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    accessibility_options: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[StudioDraftStatus] = mapped_column(
        Enum(StudioDraftStatus, name="studio_draft_status"),
        default=StudioDraftStatus.DRAFT,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    packages: Mapped[list["PedagogicalPackage"]] = relationship(
        back_populates="draft", cascade="all, delete-orphan", lazy="selectin"
    )


class ArtDirectionPreset(Base):
    __tablename__ = "art_direction_presets"
    __table_args__ = (
        UniqueConstraint(
            "code",
            name="art_direction_presets_code_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    preview_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    visual_rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    age_groups: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PedagogicalPackage(Base):
    __tablename__ = "pedagogical_packages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("teacher_studio_drafts.id", ondelete="CASCADE"), index=True
    )
    generation_project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    comic_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generated_comics.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_by_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    outputs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    shared_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    art_direction_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[PackageStatus] = mapped_column(
        Enum(PackageStatus, name="pedagogical_package_status"),
        default=PackageStatus.DRAFT,
        nullable=False,
    )
    preparation_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    draft: Mapped[TeacherStudioDraft] = relationship(back_populates="packages")
    materials: Mapped[list["PackageMaterial"]] = relationship(
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="PackageMaterial.position",
        lazy="selectin",
    )
    publication_preparations: Mapped[list["PublicationPreparation"]] = relationship(
        back_populates="package", cascade="all, delete-orphan", lazy="selectin"
    )


class PackageMaterial(Base):
    __tablename__ = "package_materials"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    package_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedagogical_packages.id", ondelete="CASCADE"), index=True
    )
    material_type: Mapped[StudioMaterialType] = mapped_column(
        Enum(StudioMaterialType, name="studio_material_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[PackageMaterialStatus] = mapped_column(
        Enum(PackageMaterialStatus, name="package_material_status"),
        default=PackageMaterialStatus.DRAFT,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    package: Mapped[PedagogicalPackage] = relationship(back_populates="materials")


class PublicationPreparation(Base):
    __tablename__ = "publication_preparations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    package_id: Mapped[UUID] = mapped_column(
        ForeignKey("pedagogical_packages.id", ondelete="CASCADE"), index=True
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    readiness: Mapped[PublicationReadiness] = mapped_column(
        Enum(PublicationReadiness, name="publication_readiness"),
        default=PublicationReadiness.NOT_READY,
        nullable=False,
    )
    checklist: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    package: Mapped[PedagogicalPackage] = relationship(back_populates="publication_preparations")
