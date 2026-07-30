from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.assets import (
    InstitutionalAssetStatus,
    InstitutionalAssetType,
    InstitutionalAssetVisibility,
    InstitutionalLicenseType,
)


class AssetFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    variant_id: UUID | None
    file_name: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    view_type: str
    is_primary: bool
    created_at: datetime


class AssetVariantInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    variant_type: str = Field(default="default", max_length=100)
    metadata_json: dict[str, object] = Field(default_factory=dict)
    is_default: bool = False


class AssetVariantRead(AssetVariantInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    asset_id: UUID
    created_at: datetime


class InstitutionalAssetCreate(BaseModel):
    asset_type: InstitutionalAssetType
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    category: str = Field(default="Geral", max_length=120)
    subcategory: str | None = Field(default=None, max_length=120)
    visibility: InstitutionalAssetVisibility = InstitutionalAssetVisibility.ORGANIZATION
    metadata_json: dict[str, object] = Field(default_factory=dict)
    compatibility: list[str] = Field(default_factory=list, max_length=30)
    age_groups: list[str] = Field(default_factory=list, max_length=20)
    subject_codes: list[str] = Field(default_factory=list, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=100)
    canonical_prompt: str | None = Field(default=None, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=8000)
    immutable_traits: list[str] = Field(default_factory=list, max_length=100)
    license_type: InstitutionalLicenseType = InstitutionalLicenseType.AUTHORIZED_USE
    original_author: str | None = Field(default=None, max_length=180)
    attribution_text: str | None = Field(default=None, max_length=5000)
    usage_restrictions: str | None = Field(default=None, max_length=5000)
    rights_confirmed: bool = False
    is_real_person: bool = False


class InstitutionalAssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=120)
    subcategory: str | None = Field(default=None, max_length=120)
    visibility: InstitutionalAssetVisibility | None = None
    metadata_json: dict[str, object] | None = None
    compatibility: list[str] | None = Field(default=None, max_length=30)
    age_groups: list[str] | None = Field(default=None, max_length=20)
    subject_codes: list[str] | None = Field(default=None, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=100)
    canonical_prompt: str | None = Field(default=None, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=8000)
    immutable_traits: list[str] | None = Field(default=None, max_length=100)
    license_type: InstitutionalLicenseType | None = None
    original_author: str | None = Field(default=None, max_length=180)
    attribution_text: str | None = Field(default=None, max_length=5000)
    usage_restrictions: str | None = Field(default=None, max_length=5000)
    rights_confirmed: bool | None = None
    is_real_person: bool | None = None
    change_description: str = Field(default="Atualização de metadados", max_length=2000)


class AssetStatusRequest(BaseModel):
    status: InstitutionalAssetStatus
    notes: str | None = Field(default=None, max_length=5000)


class InstitutionalAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    asset_type: InstitutionalAssetType
    name: str
    description: str | None
    category: str
    subcategory: str | None
    status: InstitutionalAssetStatus
    visibility: InstitutionalAssetVisibility
    current_version: int
    metadata_json: dict[str, object]
    compatibility: list[str]
    age_groups: list[str]
    subject_codes: list[str]
    canonical_prompt: str | None
    negative_prompt: str | None
    immutable_traits: list[str]
    license_type: InstitutionalLicenseType
    original_author: str | None
    attribution_text: str | None
    usage_restrictions: str | None
    rights_confirmed: bool
    is_real_person: bool
    source_comic_id: UUID | None
    source_page_id: UUID | None
    source_panel_id: UUID | None
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    files: list[AssetFileRead]
    variants: list[AssetVariantRead]
    tags: list[str] = Field(default_factory=list)


class AssetCollectionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    is_kit: bool = False
    metadata_json: dict[str, object] = Field(default_factory=dict)
    asset_ids: list[UUID] = Field(default_factory=list, max_length=200)


class AssetCollectionRead(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    is_kit: bool
    metadata_json: dict[str, object]
    asset_ids: list[UUID]
    created_at: datetime


class GeneratedCharacterSaveRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    page_id: UUID | None = None
    panel_id: UUID | None = None
    description: str | None = Field(default=None, max_length=10000)
    personality: str | None = Field(default=None, max_length=5000)
    speaking_style: str | None = Field(default=None, max_length=5000)
    pedagogical_role: str | None = Field(default=None, max_length=5000)
    canonical_prompt: str | None = Field(default=None, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=8000)
    immutable_traits: list[str] = Field(default_factory=list, max_length=100)
    destination: str = Field(default="personal", pattern="^(project|personal|institutional_review)$")
    rights_confirmed: bool = False


class GeneratedCharacterSaveResponse(BaseModel):
    creative_item_id: UUID
    institutional_asset_id: UUID | None
    name: str
    destination: str
    status: str


class AssetCatalogResponse(BaseModel):
    types: list[str]
    statuses: list[str]
    visibilities: list[str]
    license_types: list[str]
    compatibility_options: list[str]
