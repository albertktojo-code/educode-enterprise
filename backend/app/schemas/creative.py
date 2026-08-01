from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.creative import (
    CreativeItemKind,
    CreativeStatus,
    CreativeVisibility,
    SequenceStatus,
)


class CreativeAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    creative_item_id: UUID
    file_name: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    asset_role: str
    pdf_page_number: int | None
    is_primary: bool
    created_at: datetime


class CreativeVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    creative_item_id: UUID
    version_number: int
    profile_snapshot: dict[str, object]
    change_description: str | None
    created_by_user_id: UUID
    created_at: datetime


class CreativeItemBase(BaseModel):
    kind: CreativeItemKind
    name: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    canonical_prompt: str | None = Field(default=None, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=8000)
    profile_data: dict[str, object] = Field(default_factory=dict)
    visibility: CreativeVisibility = CreativeVisibility.PRIVATE
    status: CreativeStatus = CreativeStatus.DRAFT
    rights_confirmed: bool = False
    original_author: str | None = Field(default=None, max_length=180)
    license_notes: str | None = Field(default=None, max_length=5000)


class CreativeItemCreate(CreativeItemBase):
    pass


class CreativeItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=10000)
    canonical_prompt: str | None = Field(default=None, max_length=12000)
    negative_prompt: str | None = Field(default=None, max_length=8000)
    profile_data: dict[str, object] | None = None
    visibility: CreativeVisibility | None = None
    status: CreativeStatus | None = None
    rights_confirmed: bool | None = None
    original_author: str | None = Field(default=None, max_length=180)
    license_notes: str | None = Field(default=None, max_length=5000)
    change_description: str | None = Field(default=None, max_length=2000)


class CreativeItemRead(CreativeItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_by_user_id: UUID
    created_by_name_snapshot: str
    assets: list[CreativeAssetRead]
    versions: list[CreativeVersionRead]
    created_at: datetime
    updated_at: datetime


class CreativeProjectLinkInput(BaseModel):
    creative_item_id: UUID
    creative_version_id: UUID | None = None
    narrative_role: str | None = Field(default=None, max_length=100)
    position: int = Field(default=0, ge=0)
    is_primary: bool = False


class CreativeProjectLinkRead(CreativeProjectLinkInput):
    id: UUID
    name: str
    kind: CreativeItemKind


class CreativeBibleInput(BaseModel):
    title: str = Field(min_length=2, max_length=220)
    age_group: str | None = Field(default=None, max_length=80)
    visual_language: str | None = Field(default=None, max_length=5000)
    narrative_tone: str | None = Field(default=None, max_length=5000)
    pedagogical_tone: str | None = Field(default=None, max_length=5000)
    color_palette: list[str] = Field(default_factory=list, max_length=30)
    mandatory_rules: list[str] = Field(default_factory=list, max_length=100)
    prohibited_elements: list[str] = Field(default_factory=list, max_length=100)
    institution_identity: dict[str, object] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=10000)


class CreativeBibleRead(CreativeBibleInput):
    id: UUID
    generation_project_id: UUID
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class TeachingSequenceItemInput(BaseModel):
    position: int = Field(default=0, ge=0)
    title: str = Field(min_length=2, max_length=220)
    material_type: str = Field(min_length=2, max_length=80)
    learning_objective: str | None = Field(default=None, max_length=5000)
    pillar_codes: list[str] = Field(default_factory=list, max_length=20)
    duration_minutes: int | None = Field(default=None, ge=1, le=10000)
    evaluation_role: str = Field(default="none", max_length=60)
    notes: str | None = Field(default=None, max_length=5000)


class TeachingSequenceCreate(BaseModel):
    generation_project_id: UUID | None = None
    title: str = Field(min_length=2, max_length=220)
    description: str | None = Field(default=None, max_length=10000)
    status: SequenceStatus = SequenceStatus.DRAFT
    items: list[TeachingSequenceItemInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_positions(self) -> "TeachingSequenceCreate":
        positions = [item.position for item in self.items]
        if len(positions) != len(set(positions)):
            raise ValueError("As etapas da sequência não podem repetir a mesma posição")
        return self


class TeachingSequenceUpdate(BaseModel):
    generation_project_id: UUID | None = None
    title: str | None = Field(default=None, min_length=2, max_length=220)
    description: str | None = Field(default=None, max_length=10000)
    status: SequenceStatus | None = None
    items: list[TeachingSequenceItemInput] | None = Field(default=None, max_length=100)


class TeachingSequenceItemRead(TeachingSequenceItemInput):
    id: UUID
    sequence_id: UUID


class TeachingSequenceRead(BaseModel):
    id: UUID
    organization_id: UUID
    generation_project_id: UUID | None
    title: str
    description: str | None
    status: SequenceStatus
    created_by_user_id: UUID
    created_by_name_snapshot: str
    items: list[TeachingSequenceItemRead]
    created_at: datetime
    updated_at: datetime


class CreativeCatalogResponse(BaseModel):
    kinds: list[str]
    character_asset_roles: list[str]
    scene_asset_roles: list[str]
    style_asset_roles: list[str]
    cognitive_levels: list[str]
    evaluation_roles: list[str]
