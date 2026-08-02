from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ProjectStatus = Literal[
    "draft", "in_review", "approved", "rendering", "ready", "rejected", "archived"
]
SceneStatus = Literal["draft", "in_review", "approved", "rejected"]
TrackKind = Literal["dialogue", "narration", "music", "sfx", "audio_description"]
TrackStatus = Literal["draft", "ready", "approved", "rejected"]
RenderDecision = Literal["approved", "rejected"]


class AnimeProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    synopsis: str = Field(default="", max_length=20000)
    generation_project_id: UUID | None = None
    rag_context_id: UUID | None = None
    teacher_studio_draft_id: UUID | None = None
    style_preset_code: str = Field(default="anime_school", min_length=2, max_length=80)
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3"] = "16:9"
    width: int = Field(default=1920, ge=320, le=7680)
    height: int = Field(default=1080, ge=240, le=4320)
    fps: int = Field(default=24, ge=1, le=60)
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    accessibility_options: dict[str, Any] = Field(default_factory=dict)
    production_notes: dict[str, Any] = Field(default_factory=dict)


class AnimeProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    synopsis: str | None = Field(default=None, max_length=20000)
    generation_project_id: UUID | None = None
    rag_context_id: UUID | None = None
    style_preset_code: str | None = Field(default=None, min_length=2, max_length=80)
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3"] | None = None
    width: int | None = Field(default=None, ge=320, le=7680)
    height: int | None = Field(default=None, ge=240, le=4320)
    fps: int | None = Field(default=None, ge=1, le=60)
    language: str | None = Field(default=None, min_length=2, max_length=20)
    accessibility_options: dict[str, Any] | None = None
    production_notes: dict[str, Any] | None = None
    status: ProjectStatus | None = None


class AnimeSceneCreate(BaseModel):
    position: int = Field(ge=1, le=1000)
    title: str = Field(min_length=1, max_length=180)
    duration_ms: int = Field(default=5000, ge=500, le=600000)
    visual_asset_file_id: UUID | None = None
    source_comic_page_id: UUID | None = None
    source_comic_panel_id: UUID | None = None
    screenplay_text: str = Field(default="", max_length=50000)
    visual_prompt: str = Field(default="", max_length=20000)
    negative_prompt: str = Field(default="", max_length=10000)
    camera_settings: dict[str, Any] = Field(default_factory=dict)
    transition_settings: dict[str, Any] = Field(default_factory=dict)
    continuity_data: dict[str, Any] = Field(default_factory=dict)
    pedagogical_metadata: dict[str, Any] = Field(default_factory=dict)


class AnimeSceneUpdate(BaseModel):
    position: int | None = Field(default=None, ge=1, le=1000)
    title: str | None = Field(default=None, min_length=1, max_length=180)
    duration_ms: int | None = Field(default=None, ge=500, le=600000)
    visual_asset_file_id: UUID | None = None
    source_comic_page_id: UUID | None = None
    source_comic_panel_id: UUID | None = None
    screenplay_text: str | None = Field(default=None, max_length=50000)
    visual_prompt: str | None = Field(default=None, max_length=20000)
    negative_prompt: str | None = Field(default=None, max_length=10000)
    camera_settings: dict[str, Any] | None = None
    transition_settings: dict[str, Any] | None = None
    continuity_data: dict[str, Any] | None = None
    pedagogical_metadata: dict[str, Any] | None = None
    status: SceneStatus | None = None


class AnimeStoryboardImport(BaseModel):
    comic_id: UUID


class AnimeAudioTrackCreate(BaseModel):
    scene_id: UUID | None = None
    track_kind: TrackKind
    label: str = Field(min_length=1, max_length=180)
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    asset_file_id: UUID | None = None
    transcript: str = Field(default="", max_length=50000)
    speaker: str = Field(default="", max_length=160)
    start_ms: int = Field(default=0, ge=0, le=86400000)
    duration_ms: int | None = Field(default=None, gt=0, le=86400000)
    trim_start_ms: int = Field(default=0, ge=0, le=86400000)
    volume: float = Field(default=1.0, ge=0, le=2)
    fade_in_ms: int = Field(default=0, ge=0, le=60000)
    fade_out_ms: int = Field(default=0, ge=0, le=60000)
    is_muted: bool = False
    voice_settings: dict[str, Any] = Field(default_factory=dict)


class AnimeAudioTrackUpdate(BaseModel):
    scene_id: UUID | None = None
    track_kind: TrackKind | None = None
    label: str | None = Field(default=None, min_length=1, max_length=180)
    language: str | None = Field(default=None, min_length=2, max_length=20)
    asset_file_id: UUID | None = None
    transcript: str | None = Field(default=None, max_length=50000)
    speaker: str | None = Field(default=None, max_length=160)
    start_ms: int | None = Field(default=None, ge=0, le=86400000)
    duration_ms: int | None = Field(default=None, gt=0, le=86400000)
    trim_start_ms: int | None = Field(default=None, ge=0, le=86400000)
    volume: float | None = Field(default=None, ge=0, le=2)
    fade_in_ms: int | None = Field(default=None, ge=0, le=60000)
    fade_out_ms: int | None = Field(default=None, ge=0, le=60000)
    is_muted: bool | None = None
    voice_settings: dict[str, Any] | None = None
    status: TrackStatus | None = None


class AnimeCaptionCreate(BaseModel):
    scene_id: UUID | None = None
    language: str = Field(default="pt-BR", min_length=2, max_length=20)
    cue_order: int = Field(ge=1, le=10000)
    start_ms: int = Field(ge=0, le=86400000)
    end_ms: int = Field(gt=0, le=86400000)
    text: str = Field(min_length=1, max_length=4000)
    speaker: str = Field(default="", max_length=160)
    cue_kind: Literal["dialogue", "narration", "sound", "audio_description"] = "dialogue"
    accessibility_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timing(self) -> AnimeCaptionCreate:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms deve ser maior que start_ms")
        return self


class AnimeCaptionUpdate(BaseModel):
    scene_id: UUID | None = None
    language: str | None = Field(default=None, min_length=2, max_length=20)
    cue_order: int | None = Field(default=None, ge=1, le=10000)
    start_ms: int | None = Field(default=None, ge=0, le=86400000)
    end_ms: int | None = Field(default=None, gt=0, le=86400000)
    text: str | None = Field(default=None, min_length=1, max_length=4000)
    speaker: str | None = Field(default=None, max_length=160)
    cue_kind: Literal["dialogue", "narration", "sound", "audio_description"] | None = None
    accessibility_metadata: dict[str, Any] | None = None


class AnimeRenderCreate(BaseModel):
    burn_captions: bool = True
    caption_language: str = Field(default="pt-BR", min_length=2, max_length=20)
    quality: Literal["preview", "standard", "high"] = "preview"
    normalize_audio: bool = True
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=180)


class AnimeRenderReview(BaseModel):
    decision: RenderDecision
    notes: str = Field(default="", max_length=10000)


class AnimeSceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    project_id: UUID
    position: int
    title: str
    duration_ms: int
    visual_asset_file_id: UUID | None
    source_comic_page_id: UUID | None
    source_comic_panel_id: UUID | None
    screenplay_text: str
    visual_prompt: str
    negative_prompt: str
    camera_settings: dict[str, Any]
    transition_settings: dict[str, Any]
    continuity_data: dict[str, Any]
    pedagogical_metadata: dict[str, Any]
    status: str
    revision: int
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnimeStoryboardImportRead(BaseModel):
    source_comic_id: UUID
    imported_count: int
    skipped_count: int
    total_duration_ms: int
    scenes: list[AnimeSceneRead] = Field(default_factory=list)


class AnimeAudioTrackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    project_id: UUID
    scene_id: UUID | None
    track_kind: str
    label: str
    language: str
    asset_file_id: UUID | None
    transcript: str
    speaker: str
    start_ms: int
    duration_ms: int | None
    trim_start_ms: int
    volume: float
    fade_in_ms: int
    fade_out_ms: int
    is_muted: bool
    voice_settings: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


class AnimeCaptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    project_id: UUID
    scene_id: UUID | None
    language: str
    cue_order: int
    start_ms: int
    end_ms: int
    text: str
    speaker: str
    cue_kind: str
    accessibility_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AnimeRenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    project_id: UUID
    revision: int
    background_job_id: UUID | None
    output_asset_id: UUID | None
    output_asset_file_id: UUID | None
    status: str
    format: str
    video_codec: str
    audio_codec: str
    duration_ms: int | None
    render_settings: dict[str, Any]
    manifest_checksum: str
    error_message: str
    review_decision: str
    review_notes: str
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnimeProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    synopsis: str
    style_preset_code: str
    aspect_ratio: str
    width: int
    height: int
    fps: int
    language: str
    status: str
    revision: int
    created_at: datetime
    updated_at: datetime


class AnimeProjectRead(AnimeProjectSummary):
    organization_id: UUID
    generation_project_id: UUID | None
    rag_context_id: UUID | None
    teacher_studio_draft_id: UUID | None
    accessibility_options: dict[str, Any]
    production_notes: dict[str, Any]
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    scenes: list[AnimeSceneRead] = Field(default_factory=list)
    audio_tracks: list[AnimeAudioTrackRead] = Field(default_factory=list)
    captions: list[AnimeCaptionRead] = Field(default_factory=list)
    renders: list[AnimeRenderRead] = Field(default_factory=list)
