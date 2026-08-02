from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ReaderPreferenceUpsert(BaseModel):
    reader_mode: str = "PAGE"
    font_scale: float = Field(default=1.0, ge=0.75, le=2.5)
    line_spacing: float = Field(default=1.4, ge=1.0, le=2.5)
    high_contrast: bool = False
    reduced_motion: bool = False
    screen_reader_mode: bool = False
    show_alt_text: bool = False
    auto_play_narration: bool = False
    caption_mode: str = "VISIBLE"
    focus_mode: bool = False
    narration_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    zoom_level: float = Field(default=1.0, ge=0.5, le=2.5)
    orientation: str = "AUTO"

    @model_validator(mode="after")
    def normalize(self):
        self.reader_mode = self.reader_mode.upper()
        self.caption_mode = self.caption_mode.upper()
        self.orientation = self.orientation.upper()
        if self.reader_mode not in {"PAGE", "PANEL", "VERTICAL", "FOCUS"}:
            raise ValueError("Invalid reader mode")
        if self.caption_mode not in {"VISIBLE", "ON_DEMAND", "HIDDEN"}:
            raise ValueError("Invalid caption mode")
        if self.orientation not in {"AUTO", "PORTRAIT", "LANDSCAPE"}:
            raise ValueError("Invalid orientation")
        return self


class CheckpointUpsert(BaseModel):
    page_number: int = Field(default=1, ge=1)
    panel_number: int = Field(default=1, ge=1)
    completed_panels: int = Field(default=0, ge=0)
    elapsed_seconds: int = Field(default=0, ge=0)
    sequence: int = Field(ge=1)
    reader_mode: str = "PAGE"
    state: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize(self):
        self.reader_mode = self.reader_mode.upper()
        if self.reader_mode not in {"PAGE", "PANEL", "VERTICAL", "FOCUS"}:
            raise ValueError("Invalid reader mode")
        return self


class BookmarkCreate(BaseModel):
    page_number: int = Field(ge=1)
    panel_number: int | None = Field(default=None, ge=1)
    label: str = Field(default="", max_length=180)
    note: str = Field(default="", max_length=2000)


class NarrationTrackCreate(BaseModel):
    page_number: int | None = Field(default=None, ge=1)
    panel_number: int | None = Field(default=None, ge=1)
    source_type: str = "BROWSER_TTS"
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    transcript: str = Field(min_length=1, max_length=30000)
    audio_asset_id: uuid.UUID | None = None
    audio_url: str | None = Field(default=None, max_length=1000)
    duration_ms: int | None = Field(default=None, ge=0)
    voice_settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self):
        self.source_type = self.source_type.upper()
        if self.source_type not in {"BROWSER_TTS", "HUMAN_RECORDING", "UPLOADED_AUDIO"}:
            raise ValueError("Invalid narration source")
        if self.source_type != "BROWSER_TTS" and not self.audio_asset_id and not self.audio_url:
            raise ValueError("Recorded narration requires audio_asset_id or audio_url")
        return self


class GlossaryTermCreate(BaseModel):
    term: str = Field(min_length=1, max_length=120)
    definition: str = Field(min_length=3, max_length=4000)
    simplified_definition: str = Field(default="", max_length=4000)
    page_number: int | None = Field(default=None, ge=1)
    panel_number: int | None = Field(default=None, ge=1)
    pronunciation: str = Field(default="", max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssessmentLinkCreate(BaseModel):
    question_bank_item_id: uuid.UUID
    assignment_id: uuid.UUID | None = None
    page_number: int = Field(ge=1)
    panel_number: int | None = Field(default=None, ge=1)
    display_order: int = Field(default=0, ge=0)
    required: bool = False
    reveal_rule: str = Field(default="ON_REACH", max_length=40)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PresentationCreate(BaseModel):
    release_id: uuid.UUID
    title: str = Field(min_length=3, max_length=180)
    allow_audience_join: bool = True
    sync_audience: bool = True
    reveal_mode: str = Field(default="PANEL", max_length=30)
    settings: dict[str, Any] = Field(default_factory=dict)


class PresentationAdvance(BaseModel):
    page_number: int = Field(ge=1)
    panel_number: int = Field(default=0, ge=0)
    reveal_step: int = Field(default=0, ge=0)
    presenter_note: str = Field(default="", max_length=3000)
    expected_revision: int | None = Field(default=None, ge=0)


class PresentationJoin(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    local_preferences: dict[str, Any] = Field(default_factory=dict)


class PresentationTransition(BaseModel):
    target_status: str
    expected_revision: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def normalize(self):
        self.target_status = self.target_status.upper()
        return self
