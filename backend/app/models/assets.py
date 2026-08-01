from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InstitutionalAssetType(StrEnum):
    CHARACTER = "character"
    SCENE = "scene"
    OBJECT = "object"
    BACKGROUND = "background"
    ANIMAL = "animal"
    VEHICLE = "vehicle"
    FURNITURE = "furniture"
    CLOTHING = "clothing"
    ACCESSORY = "accessory"
    EFFECT = "effect"
    BALLOON = "balloon"
    ICON = "icon"
    FRAME = "frame"
    COVER = "cover"
    PAGE_LAYOUT = "page_layout"
    PALETTE = "palette"
    LOGO = "logo"
    OTHER = "other"


class InstitutionalAssetStatus(StrEnum):
    DRAFT = "draft"
    PROCESSING = "processing"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    OBSOLETE = "obsolete"
    BLOCKED = "blocked"
    ARCHIVED = "archived"


class InstitutionalAssetVisibility(StrEnum):
    ORGANIZATION = "organization"
    SELECTED_TEACHERS = "selected_teachers"
    PROJECT_ONLY = "project_only"


class InstitutionalLicenseType(StrEnum):
    PROPRIETARY = "proprietary"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    PUBLIC_DOMAIN = "public_domain"
    AUTHORIZED_USE = "authorized_use"
    OTHER = "other"


class InstitutionalAsset(Base):
    __tablename__ = "institutional_assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "asset_type", "name", name="uq_institutional_asset_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    asset_type: Mapped[InstitutionalAssetType] = mapped_column(Enum(InstitutionalAssetType, name="institutional_asset_type"), index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(120), default="Geral", index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[InstitutionalAssetStatus] = mapped_column(Enum(InstitutionalAssetStatus, name="institutional_asset_status"), default=InstitutionalAssetStatus.DRAFT, index=True)
    visibility: Mapped[InstitutionalAssetVisibility] = mapped_column(Enum(InstitutionalAssetVisibility, name="institutional_asset_visibility"), default=InstitutionalAssetVisibility.ORGANIZATION)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    compatibility: Mapped[list[str]] = mapped_column(JSON, default=list)
    age_groups: Mapped[list[str]] = mapped_column(JSON, default=list)
    subject_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    canonical_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    immutable_traits: Mapped[list[str]] = mapped_column(JSON, default=list)
    license_type: Mapped[InstitutionalLicenseType] = mapped_column(Enum(InstitutionalLicenseType, name="institutional_license_type"), default=InstitutionalLicenseType.AUTHORIZED_USE)
    original_author: Mapped[str | None] = mapped_column(String(180), nullable=True)
    attribution_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_real_person: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_comic_id: Mapped[UUID | None] = mapped_column(ForeignKey("generated_comics.id", ondelete="SET NULL"), index=True, nullable=True)
    source_page_id: Mapped[UUID | None] = mapped_column(ForeignKey("comic_pages.id", ondelete="SET NULL"), nullable=True)
    source_panel_id: Mapped[UUID | None] = mapped_column(ForeignKey("comic_panels.id", ondelete="SET NULL"), nullable=True)
    source_creative_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("creative_items.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    files: Mapped[list["InstitutionalAssetFile"]] = relationship(cascade="all, delete-orphan", back_populates="asset", lazy="selectin")
    variants: Mapped[list["InstitutionalAssetVariant"]] = relationship(cascade="all, delete-orphan", back_populates="asset", lazy="selectin")
    versions: Mapped[list["InstitutionalAssetVersion"]] = relationship(cascade="all, delete-orphan", back_populates="asset", lazy="selectin")
    tags: Mapped[list["InstitutionalAssetTag"]] = relationship(cascade="all, delete-orphan", back_populates="asset", lazy="selectin")


class InstitutionalAssetVariant(Base):
    __tablename__ = "institutional_asset_variants"
    __table_args__ = (UniqueConstraint("asset_id", "name", name="uq_institutional_asset_variant_name"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_assets.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    variant_type: Mapped[str] = mapped_column(String(100), default="default")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    asset: Mapped[InstitutionalAsset] = relationship(back_populates="variants")


class InstitutionalAssetFile(Base):
    __tablename__ = "institutional_asset_files"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_assets.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[UUID | None] = mapped_column(ForeignKey("institutional_asset_variants.id", ondelete="SET NULL"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_type: Mapped[str] = mapped_column(String(80), default="reference")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_original: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    asset: Mapped[InstitutionalAsset] = relationship(back_populates="files")


class InstitutionalAssetVersion(Base):
    __tablename__ = "institutional_asset_versions"
    __table_args__ = (UniqueConstraint("asset_id", "version_number", name="uq_institutional_asset_version"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_assets.id", ondelete="CASCADE"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    change_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    asset: Mapped[InstitutionalAsset] = relationship(back_populates="versions")


class InstitutionalAssetTag(Base):
    __tablename__ = "institutional_asset_tags"
    __table_args__ = (UniqueConstraint("asset_id", "tag", name="uq_institutional_asset_tag"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_assets.id", ondelete="CASCADE"), index=True)
    tag: Mapped[str] = mapped_column(String(80), index=True)
    asset: Mapped[InstitutionalAsset] = relationship(back_populates="tags")


class AssetCollection(Base):
    __tablename__ = "asset_collections"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_kit: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["AssetCollectionItem"]] = relationship(cascade="all, delete-orphan", back_populates="collection", lazy="selectin")


class AssetCollectionItem(Base):
    __tablename__ = "asset_collection_items"
    __table_args__ = (UniqueConstraint("collection_id", "asset_id", name="uq_asset_collection_item"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("asset_collections.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_assets.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    collection: Mapped[AssetCollection] = relationship(back_populates="items")


class InstitutionalAssetUsage(Base):
    __tablename__ = "institutional_asset_usages"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("institutional_assets.id", ondelete="RESTRICT"), index=True)
    asset_version: Mapped[int] = mapped_column(Integer)
    comic_id: Mapped[UUID | None] = mapped_column(ForeignKey("generated_comics.id", ondelete="CASCADE"), nullable=True, index=True)
    panel_id: Mapped[UUID | None] = mapped_column(ForeignKey("comic_panels.id", ondelete="CASCADE"), nullable=True)
    used_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InstitutionalAssetAudit(Base):
    __tablename__ = "institutional_asset_audit"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("institutional_assets.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
