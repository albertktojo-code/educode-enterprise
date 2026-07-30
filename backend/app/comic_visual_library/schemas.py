from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LibraryCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    description: str = ""
    scope: str = "PERSONAL"
    owner_user_id: uuid.UUID | None = None
    comic_project_id: uuid.UUID | None = None
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scope(self):
        allowed = {"PERSONAL", "COMIC", "ORGANIZATION", "INSTITUTIONAL"}
        if self.scope.upper() not in allowed:
            raise ValueError("Invalid library scope")
        self.scope = self.scope.upper()
        return self


class LibraryRead(LibraryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class CharacterCreate(BaseModel):
    library_id: uuid.UUID
    origin_comic_project_id: uuid.UUID | None = None
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=100)
    biography: str = ""
    personality: dict[str, Any] = Field(default_factory=dict)
    identity_profile: dict[str, Any]
    default_wardrobe: dict[str, Any] = Field(default_factory=dict)
    visual_style: dict[str, Any] = Field(default_factory=dict)
    prompt_template: str = ""
    negative_prompt: str = ""
    reference_assets: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_slug_and_identity(self):
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise ValueError("Slug must use lowercase letters, numbers and hyphens")
        if not any(key in self.identity_profile for key in ("face", "hair", "eyes", "age_group")):
            raise ValueError("Identity profile needs at least one stable visual attribute")
        return self


class CharacterRead(CharacterCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    identity_fingerprint: str
    current_version: int
    status: str
    created_at: datetime
    updated_at: datetime


class CharacterVersionCreate(BaseModel):
    snapshot: dict[str, Any]
    change_summary: str = Field(min_length=3, max_length=1000)


class CharacterVariantCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=180)
    wardrobe: dict[str, Any] = Field(default_factory=dict)
    expression: str | None = Field(default=None, max_length=80)
    pose: str | None = Field(default=None, max_length=120)
    accessories: list[str] = Field(default_factory=list)
    prompt_overrides: dict[str, Any] = Field(default_factory=dict)
    reference_assets: list[dict[str, Any]] = Field(default_factory=list)


class ScenarioCreate(BaseModel):
    library_id: uuid.UUID
    origin_comic_project_id: uuid.UUID | None = None
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=100)
    description: str = ""
    location_profile: dict[str, Any]
    lighting_profile: dict[str, Any] = Field(default_factory=dict)
    required_objects: list[dict[str, Any]] = Field(default_factory=list)
    visual_style: dict[str, Any] = Field(default_factory=dict)
    prompt_template: str = ""
    reference_assets: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_slug(self):
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.slug):
            raise ValueError("Slug must use lowercase letters, numbers and hyphens")
        return self


class ScenarioRead(ScenarioCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    identity_fingerprint: str
    current_version: int
    status: str
    created_at: datetime
    updated_at: datetime


class ContinuityRecordCreate(BaseModel):
    comic_project_id: uuid.UUID
    page_id: uuid.UUID
    panel_id: uuid.UUID
    sequence_number: int = Field(ge=1)
    location: str | None = Field(default=None, max_length=180)
    time_of_day: str | None = Field(default=None, max_length=80)
    weather: str | None = Field(default=None, max_length=80)
    character_states: list[dict[str, Any]] = Field(default_factory=list)
    important_objects: list[dict[str, Any]] = Field(default_factory=list)
    narrative_state: dict[str, Any] = Field(default_factory=dict)
    previous_panel_id: uuid.UUID | None = None
    next_panel_id: uuid.UUID | None = None


class ConsistencyRunRequest(BaseModel):
    comic_project_id: uuid.UUID
    page_id: uuid.UUID | None = None
    panel_id: uuid.UUID | None = None
    entity_type: str
    entity_id: uuid.UUID | None = None
    expected_snapshot: dict[str, Any]
    observed_snapshot: dict[str, Any]
    fields: list[str] = Field(default_factory=list)


class ConsistencyResolution(BaseModel):
    status: str
    note: str = Field(min_length=3, max_length=1000)
    resolution: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_status(self):
        allowed = {"ACCEPTED", "RESOLVED", "IGNORED"}
        self.status = self.status.upper()
        if self.status not in allowed:
            raise ValueError("Invalid resolution status")
        return self


class BatchItemCreate(BaseModel):
    page_id: uuid.UUID
    panel_id: uuid.UUID
    page_order: int = Field(default=0, ge=0)
    panel_order: int = Field(default=0, ge=0)
    character_locks: dict[str, Any] = Field(default_factory=dict)
    scenario_locks: dict[str, Any] = Field(default_factory=dict)
    prompt_snapshot: dict[str, Any] = Field(default_factory=dict)


class GenerationBatchCreate(BaseModel):
    comic_project_id: uuid.UUID
    name: str = Field(min_length=3, max_length=180)
    selection_mode: str = "PENDING_ONLY"
    default_locks: dict[str, Any] = Field(default_factory=dict)
    generation_settings: dict[str, Any] = Field(default_factory=dict)
    items: list[BatchItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_panels(self):
        panel_ids = [item.panel_id for item in self.items]
        if len(panel_ids) != len(set(panel_ids)):
            raise ValueError("Panel IDs must be unique in a batch")
        return self
