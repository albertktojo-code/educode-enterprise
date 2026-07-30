from datetime import datetime
from enum import StrEnum
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


class CreativeItemKind(StrEnum):
    CHARACTER = "character"
    SCENE = "scene"
    STYLE = "style"


class CreativeVisibility(StrEnum):
    PRIVATE = "private"
    TEAM = "team"
    ORGANIZATION = "organization"


class CreativeStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class SequenceStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class CreativeItem(Base):
    __tablename__ = "creative_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "kind",
            "name",
            name="uq_creative_item_org_kind_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    created_by_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[CreativeItemKind] = mapped_column(
        Enum(CreativeItemKind, name="creative_item_kind"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    canonical_prompt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text(), nullable=True)
    profile_data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, nullable=False)
    visibility: Mapped[CreativeVisibility] = mapped_column(
        Enum(CreativeVisibility, name="creative_visibility"),
        default=CreativeVisibility.PRIVATE,
        nullable=False,
    )
    status: Mapped[CreativeStatus] = mapped_column(
        Enum(CreativeStatus, name="creative_status"),
        default=CreativeStatus.DRAFT,
        nullable=False,
    )
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    original_author: Mapped[str | None] = mapped_column(String(180), nullable=True)
    license_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assets: Mapped[list["CreativeAsset"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="creative_item",
        lazy="selectin",
    )
    versions: Mapped[list["CreativeVersion"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="creative_item",
        lazy="selectin",
    )


class CreativeAsset(Base):
    __tablename__ = "creative_assets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    creative_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("creative_items.id", ondelete="CASCADE"),
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    asset_role: Mapped[str] = mapped_column(String(80), default="reference", nullable=False)
    pdf_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creative_item: Mapped[CreativeItem] = relationship(back_populates="assets")


class CreativeVersion(Base):
    __tablename__ = "creative_versions"
    __table_args__ = (
        UniqueConstraint(
            "creative_item_id",
            "version_number",
            name="uq_creative_version_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    creative_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("creative_items.id", ondelete="CASCADE"),
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    change_description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    creative_item: Mapped[CreativeItem] = relationship(back_populates="versions")


class GenerationProjectCreativeItem(Base):
    __tablename__ = "generation_project_creative_items"
    __table_args__ = (
        UniqueConstraint(
            "generation_project_id",
            "creative_item_id",
            name="uq_generation_project_creative_item",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_project_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="CASCADE"),
        index=True,
    )
    creative_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("creative_items.id", ondelete="RESTRICT"),
        index=True,
    )
    creative_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("creative_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    narrative_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    creative_item: Mapped[CreativeItem] = relationship(lazy="joined")
    creative_version: Mapped[CreativeVersion | None] = relationship(lazy="joined")


class CreativeBible(Base):
    __tablename__ = "creative_bibles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    generation_project_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    age_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    visual_language: Mapped[str | None] = mapped_column(Text(), nullable=True)
    narrative_tone: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pedagogical_tone: Mapped[str | None] = mapped_column(Text(), nullable=True)
    color_palette: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    mandatory_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    prohibited_elements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    institution_identity: Mapped[dict[str, object]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    updated_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TeachingSequence(Base):
    __tablename__ = "teaching_sequences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
    )
    generation_project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[SequenceStatus] = mapped_column(
        Enum(SequenceStatus, name="sequence_status"),
        default=SequenceStatus.DRAFT,
        nullable=False,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    created_by_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[list["TeachingSequenceItem"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="sequence",
        order_by="TeachingSequenceItem.position",
        lazy="selectin",
    )


class TeachingSequenceItem(Base):
    __tablename__ = "teaching_sequence_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sequence_id: Mapped[UUID] = mapped_column(
        ForeignKey("teaching_sequences.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    material_type: Mapped[str] = mapped_column(String(80), nullable=False)
    learning_objective: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pillar_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_role: Mapped[str] = mapped_column(String(60), default="none", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    sequence: Mapped[TeachingSequence] = relationship(back_populates="items")
