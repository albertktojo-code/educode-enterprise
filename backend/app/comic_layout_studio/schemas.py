from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CanvasTransform(BaseModel):
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation_deg: float = 0
    opacity: float = Field(default=1, ge=0, le=1)


class CanvasDocumentCreate(BaseModel):
    comic_project_id: uuid.UUID
    page_id: uuid.UUID
    name: str = Field(min_length=3, max_length=180)
    page_width: float = Field(default=210, gt=0, le=2000)
    page_height: float = Field(default=297, gt=0, le=2000)
    measurement_unit: str = Field(default="MM", max_length=12)
    dpi: int = Field(default=300, ge=72, le=1200)
    bleed_mm: float = Field(default=3, ge=0, le=50)
    safe_margin_mm: float = Field(default=8, ge=0, le=100)
    grid_size: float = Field(default=5, gt=0, le=100)
    snap_enabled: bool = True
    rulers_enabled: bool = True
    show_bleed: bool = True
    show_safe_area: bool = True
    background_settings: dict[str, Any] = Field(default_factory=dict)
    editor_settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_margins(self):
        if self.safe_margin_mm * 2 >= min(self.page_width, self.page_height):
            raise ValueError("Safe margin consumes the entire page")
        return self


class CanvasDocumentRead(CanvasDocumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    revision_number: int
    created_at: datetime
    updated_at: datetime


class LayerCreate(BaseModel):
    source_panel_id: uuid.UUID | None = None
    layer_type: str
    name: str = Field(min_length=1, max_length=180)
    transform: CanvasTransform
    blend_mode: str = "NORMAL"
    shape: str = "RECTANGLE"
    visible: bool = True
    locked: bool = False
    clip_path: dict[str, Any] = Field(default_factory=dict)
    transform_origin: dict[str, Any] = Field(default_factory=lambda: {"x": 0.5, "y": 0.5})
    style: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    asset_reference: str | None = None
    accessibility_metadata: dict[str, Any] = Field(default_factory=dict)


class LayerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    transform: CanvasTransform | None = None
    blend_mode: str | None = None
    shape: str | None = None
    visible: bool | None = None
    locked: bool | None = None
    clip_path: dict[str, Any] | None = None
    style: dict[str, Any] | None = None
    content: dict[str, Any] | None = None
    asset_reference: str | None = None
    accessibility_metadata: dict[str, Any] | None = None


class LayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    source_panel_id: uuid.UUID | None
    group_id: uuid.UUID | None
    layer_type: str
    name: str
    z_index: int
    x: float
    y: float
    width: float
    height: float
    rotation_deg: float
    opacity: float
    visible: bool
    locked: bool
    blend_mode: str
    shape: str
    clip_path: dict[str, Any]
    style: dict[str, Any]
    content: dict[str, Any]
    asset_reference: str | None
    accessibility_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReorderLayersRequest(BaseModel):
    layer_ids: list[uuid.UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_layers(self):
        if len(self.layer_ids) != len(set(self.layer_ids)):
            raise ValueError("Layer IDs must be unique")
        return self


class GuideCreate(BaseModel):
    orientation: str
    position: float
    guide_type: str = "CUSTOM"
    visible: bool = True
    locked: bool = False
    label: str | None = Field(default=None, max_length=120)


class GuideRead(GuideCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    layer_ids: list[uuid.UUID] = Field(min_length=2)
    visible: bool = True
    locked: bool = False

    @model_validator(mode="after")
    def unique_group_layers(self):
        if len(self.layer_ids) != len(set(self.layer_ids)):
            raise ValueError("Group layer IDs must be unique")
        return self


class OperationCreate(BaseModel):
    sequence: int = Field(ge=1)
    operation_type: str
    target_type: str
    target_id: uuid.UUID | None = None
    forward_payload: dict[str, Any] = Field(default_factory=dict)
    reverse_payload: dict[str, Any] = Field(default_factory=dict)


class ExportPresetCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    description: str = ""
    version: str = Field(default="1.0.0", max_length=24)
    output_format: str = "PDF"
    page_size: str = "A4"
    dpi: int = Field(default=300, ge=72, le=1200)
    color_profile: str = "SRGB"
    include_bleed: bool = True
    include_crop_marks: bool = False
    flatten_layers: bool = True
    accessibility_enabled: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)


class ExportPresetRead(ExportPresetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID | None
    status: str
    is_system: bool
    created_at: datetime
    updated_at: datetime


class PreflightRequest(BaseModel):
    output_format: str = "PDF"
    minimum_dpi: int = Field(default=150, ge=72, le=1200)
    persist_findings: bool = True


class ExportJobCreate(BaseModel):
    preset_id: uuid.UUID | None = None
    output_format: str = "PDF"
    run_preflight: bool = True
    allow_warnings: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)


class ExportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    preset_id: uuid.UUID | None
    status: str
    progress_percent: int
    configuration: dict[str, Any]
    warnings: list[dict[str, Any]]
    output_reference: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
