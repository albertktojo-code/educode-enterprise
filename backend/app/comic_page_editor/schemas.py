from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PanelRect(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)
    shape: str = "RECTANGLE"

    @model_validator(mode="after")
    def inside_page(self):
        if self.x + self.width > 1.0001 or self.y + self.height > 1.0001:
            raise ValueError("Panel must remain inside the page")
        return self


class GridDefinition(BaseModel):
    panels: list[PanelRect] = Field(min_length=1, max_length=12)
    gutter: float = Field(default=0.02, ge=0, le=0.1)
    page_margin: float = Field(default=0.02, ge=0, le=0.15)


class LayoutTemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    description: str = ""
    version: str = Field(default="1.0.0", max_length=24)
    orientation: str = "PORTRAIT"
    category: str = "TRADITIONAL"
    grid_definition: GridDefinition
    is_favorite: bool = False


class LayoutTemplateRead(LayoutTemplateCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    panel_count: int
    status: str
    is_system: bool
    organization_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class PageCreate(BaseModel):
    layout_template_id: uuid.UUID | None = None
    page_number: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=180)
    page_width: int = Field(default=1200, ge=600, le=4000)
    page_height: int = Field(default=1600, ge=600, le=5000)
    grid_definition: GridDefinition
    accessibility_settings: dict[str, Any] = Field(default_factory=dict)


class PageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    comic_project_id: uuid.UUID
    layout_template_id: uuid.UUID | None
    page_number: int
    page_type: str
    title: str | None
    status: str
    page_width: int
    page_height: int
    background_settings: dict[str, Any]
    accessibility_settings: dict[str, Any]
    content_layers: list[dict[str, Any]]
    preservation_settings: dict[str, Any]
    continuity_metadata: dict[str, Any]
    cover_generation: dict[str, Any]
    revision_number: int
    created_at: datetime
    updated_at: datetime


class PanelUpdate(BaseModel):
    scene_summary: str | None = None
    visual_prompt: str | None = None
    negative_prompt: str | None = None
    shape: str | None = None
    rect: PanelRect | None = None
    locked_elements: list[str] | None = None
    pedagogical_metadata: dict[str, Any] | None = None
    accessibility_metadata: dict[str, Any] | None = None


class PanelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    page_id: uuid.UUID
    panel_order: int
    shape: str
    x: float
    y: float
    width: float
    height: float
    aspect_ratio: str
    scene_summary: str
    visual_prompt: str
    generation_status: str
    locked_elements: list[str]


class TextLayerCreate(BaseModel):
    layer_type: str
    speaker_name: str | None = Field(default=None, max_length=120)
    content: str = Field(min_length=1, max_length=2000)
    x: float = Field(default=0.1, ge=0, le=1)
    y: float = Field(default=0.1, ge=0, le=1)
    width: float = Field(default=0.4, gt=0, le=1)
    height: float = Field(default=0.2, gt=0, le=1)
    style: dict[str, Any] = Field(default_factory=dict)
    reading_order: int = Field(default=1, ge=1)


class GenerationJobCreate(BaseModel):
    continue_in_background: bool = True
    generate_images: bool = True
    validate_bncc: bool = True
    validate_accessibility: bool = True
    selected_page_ids: list[uuid.UUID] = Field(default_factory=list)


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    comic_project_id: uuid.UUID
    status: str
    progress_percent: int
    current_step_code: str | None
    total_pages: int
    total_panels: int
    completed_panels: int
    failed_panels: int
    continue_in_background: bool
    created_at: datetime
    updated_at: datetime


class AutosaveRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=120)
    sequence: int = Field(ge=1)
    payload: dict[str, Any]
    checksum: str = Field(min_length=64, max_length=64)


class SnapshotCreate(BaseModel):
    label: str | None = Field(default=None, max_length=180)
    snapshot_type: str = "MANUAL"
    revision_number: int = Field(ge=1)
    data_snapshot: dict[str, Any]


class ReorderPagesRequest(BaseModel):
    page_ids: list[uuid.UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_pages(self):
        if len(self.page_ids) != len(set(self.page_ids)):
            raise ValueError("Page IDs must be unique")
        return self


class StoryPlanUpsert(BaseModel):
    source_mode: str = Field(default="MANUAL", pattern="^(MANUAL|AI_SUMMARY)$")
    total_pages: int = Field(default=1, ge=1, le=100)
    narrative_pacing: str = Field(
        default="BALANCED",
        pattern="^(SLOW|BALANCED|FAST|CINEMATIC)$",
    )
    distribution_mode: str = Field(
        default="AUTOMATIC",
        pattern="^(AUTOMATIC|ASSISTED|MANUAL)$",
    )
    short_summary: str = Field(default="", max_length=6000)
    full_script: str = Field(default="", max_length=100000)
    continuity_constraints: dict[str, Any] = Field(default_factory=dict)
    generation_instructions: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_story_source(self):
        if self.source_mode == "MANUAL" and not self.full_script.strip():
            if not self.short_summary.strip():
                raise ValueError(
                    "Informe o roteiro completo ou um resumo da história"
                )
        if self.source_mode == "AI_SUMMARY" and len(
            self.short_summary.strip()
        ) < 10:
            raise ValueError(
                "O resumo para geração por IA deve ter pelo menos 10 caracteres"
            )
        return self


class StoryPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    comic_project_id: uuid.UUID
    source_mode: str
    total_pages: int
    narrative_pacing: str
    distribution_mode: str
    short_summary: str
    full_script: str
    page_plan: list[dict[str, Any]]
    continuity_constraints: dict[str, Any]
    generation_instructions: dict[str, Any]
    generation_status: str
    ai_generation_request_id: uuid.UUID | None
    content_hash: str
    revision_number: int
    created_at: datetime
    updated_at: datetime


class StoryGenerateRequest(BaseModel):
    total_pages: int = Field(default=1, ge=1, le=100)
    narrative_pacing: str = Field(
        default="BALANCED",
        pattern="^(SLOW|BALANCED|FAST|CINEMATIC)$",
    )
    distribution_mode: str = Field(
        default="AUTOMATIC",
        pattern="^(AUTOMATIC|ASSISTED)$",
    )
    short_summary: str = Field(min_length=10, max_length=6000)
    continuity_constraints: dict[str, Any] = Field(default_factory=dict)
    generation_instructions: dict[str, Any] = Field(default_factory=dict)
    model_id: uuid.UUID | None = None
    prompt_template_id: uuid.UUID | None = None


class StoryDistributeRequest(BaseModel):
    ensure_total_pages: bool = True
    preserve_existing_summaries: bool = False
    apply_layout_recommendations: bool = False


class PageLayoutApplyRequest(BaseModel):
    layout_template_id: uuid.UUID
    preserve_content: bool = True


class ApplyAIStoryResultRequest(BaseModel):
    result_id: uuid.UUID
    distribute_after_apply: bool = True


class CoverTextLayer(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    layer_type: str = Field(
        pattern="^(TITLE|SUBTITLE|AUTHOR|SCHOOL|DISCIPLINE|THEME|BADGE|LOGO|CREDITS|SUMMARY)$"
    )
    content: str = Field(default="", max_length=3000)
    x: float = Field(default=0.1, ge=0, le=1)
    y: float = Field(default=0.1, ge=0, le=1)
    width: float = Field(default=0.8, gt=0, le=1)
    height: float = Field(default=0.12, gt=0, le=1)
    style: dict[str, Any] = Field(default_factory=dict)
    visible: bool = True


class CoverPageUpsert(BaseModel):
    composition_code: str = Field(
        default="CINEMATIC",
        pattern="^(CINEMATIC|CHARACTER_FOCUS|EDUCATIONAL|MINIMALIST|DIAGONAL|ENSEMBLE)$",
    )
    title: str = Field(default="", max_length=300)
    subtitle: str = Field(default="", max_length=500)
    author: str = Field(default="", max_length=300)
    school: str = Field(default="", max_length=300)
    classroom: str = Field(default="", max_length=200)
    discipline: str = Field(default="", max_length=200)
    theme: str = Field(default="", max_length=300)
    school_year: str = Field(default="", max_length=120)
    background_asset_reference: str | None = Field(default=None, max_length=1000)
    focal_point: dict[str, float] = Field(default_factory=lambda: {"x": 0.5, "y": 0.5})
    scale: float = Field(default=1.0, ge=0.5, le=3.0)
    bleed_enabled: bool = True
    safe_area_enabled: bool = True
    spine_enabled: bool = False
    content_layers: list[CoverTextLayer] = Field(default_factory=list, max_length=40)
    preservation_settings: dict[str, Any] = Field(default_factory=dict)
    continuity_metadata: dict[str, Any] = Field(default_factory=dict)
    accessibility_settings: dict[str, Any] = Field(default_factory=dict)


class CoverGenerateRequest(BaseModel):
    composition_code: str = Field(
        default="CINEMATIC",
        pattern="^(CINEMATIC|CHARACTER_FOCUS|EDUCATIONAL|MINIMALIST|DIAGONAL|ENSEMBLE)$",
    )
    variation_count: int = Field(default=4, ge=1, le=4)
    additional_instructions: str = Field(default="", max_length=5000)
    model_id: uuid.UUID | None = None
    prompt_template_id: uuid.UUID | None = None


class CoverApplyResultRequest(BaseModel):
    result_id: uuid.UUID


class SpecialPageCreate(BaseModel):
    page_type: str = Field(pattern="^(COVER|BACK_COVER|ACTIVITY|ANSWER_KEY)$")
    title: str | None = Field(default=None, max_length=180)


class PagePreservationUpdate(BaseModel):
    scope: str = Field(pattern="^(PANEL|PAGE|PROJECT)$")
    elements: list[str] = Field(default_factory=list, max_length=20)
    panel_id: uuid.UUID | None = None


class ContinuityMetadataUpdate(BaseModel):
    character: str = Field(default="", max_length=300)
    outfit: str = Field(default="", max_length=300)
    scenario: str = Field(default="", max_length=300)
    important_object: str = Field(default="", max_length=300)
    time_of_day: str = Field(default="", max_length=120)
    emotion: str = Field(default="", max_length=200)
    palette: str = Field(default="", max_length=200)


class SnapshotRestoreRequest(BaseModel):
    snapshot_id: uuid.UUID


class AdvancedPageReorderRequest(BaseModel):
    ordered_story_page_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=100,
    )
    recalculate_narrative: bool = False


class PanelReadingOrderRequest(BaseModel):
    ordered_panel_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=24,
    )


class ProductivityAnalysisRequest(BaseModel):
    expected_story_pages: int = Field(ge=1, le=100)


class SnapshotCompareRequest(BaseModel):
    left_snapshot_id: uuid.UUID
    right_snapshot_id: uuid.UUID


class CustomLayoutFromPageRequest(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    name: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="CUSTOM", max_length=40)


class TextLayerEditorialUpdate(BaseModel):
    layer_type: str | None = Field(
        default=None,
        pattern=(
            "^(SPEECH|THOUGHT|SHOUT|WHISPER|NARRATION|CAPTION|"
            "DEVICE|OFFSCREEN|SOUND_EFFECT)$"
        ),
    )
    speaker_name: str | None = Field(default=None, max_length=120)
    content: str | None = Field(default=None, max_length=2000)
    x: float | None = Field(default=None, ge=0, le=1)
    y: float | None = Field(default=None, ge=0, le=1)
    width: float | None = Field(default=None, gt=0, le=1)
    height: float | None = Field(default=None, gt=0, le=1)
    style: dict[str, Any] | None = None
    reading_order: int | None = Field(default=None, ge=1)
    bubble_metadata: dict[str, Any] | None = None
    accessibility_metadata: dict[str, Any] | None = None
    review_status: str | None = Field(
        default=None,
        pattern="^(DRAFT|IN_REVIEW|APPROVED|CHANGES_REQUESTED)$",
    )
    linked_character_id: uuid.UUID | None = None


class BubbleArrangeRequest(BaseModel):
    layer_ids: list[uuid.UUID] = Field(min_length=1, max_length=30)


class DialogueSuggestionRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    school_year: str = Field(default="", max_length=80)
    tone: str = Field(default="natural", max_length=80)


class EditorialCommentCreate(BaseModel):
    target_type: str = Field(
        pattern="^(PROJECT|PAGE|PANEL|TEXT_LAYER|COVER)$"
    )
    target_id: uuid.UUID
    content: str = Field(min_length=1, max_length=5000)
    priority: str = Field(
        default="NORMAL",
        pattern="^(LOW|NORMAL|HIGH|CRITICAL)$",
    )


class EditorialCommentStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(OPEN|IN_REVIEW|RESOLVED|REOPENED)$"
    )


class HQActivityCreate(BaseModel):
    activity_type: str = Field(
        pattern=(
            "^(MULTIPLE_CHOICE|TRUE_FALSE|MATCHING|ORDERING|FILL_BLANKS|"
            "CROSSWORD|WORD_SEARCH|SHORT_ANSWER|ESSAY|"
            "COMPUTATIONAL_THINKING|MATHEMATICS)$"
        )
    )
    title: str = Field(min_length=3, max_length=220)
    instructions: str = Field(min_length=3, max_length=5000)
    subject: str = Field(min_length=2, max_length=100)
    theme: str = Field(default="", max_length=180)
    school_year: str | None = Field(default=None, max_length=60)
    difficulty: str = Field(
        default="BASIC",
        pattern="^(INTRODUCTORY|BASIC|INTERMEDIATE|ADVANCED|CHALLENGE)$",
    )
    layout_code: str = Field(default="ACTIVITY_FULL", max_length=80)
    activity_payload: dict[str, Any] = Field(default_factory=dict)
    answer_key: dict[str, Any] = Field(default_factory=dict)
    explanation: str | None = Field(default=None, max_length=5000)
    rubric: dict[str, Any] = Field(default_factory=dict)
    accessibility: dict[str, Any] = Field(default_factory=dict)
    bncc_codes: list[str] = Field(default_factory=list, max_length=20)
    ct_pillars: list[str] = Field(default_factory=list, max_length=10)
    source_page_id: uuid.UUID | None = None
    source_panel_id: uuid.UUID | None = None
    display_order: int = Field(default=1, ge=1, le=100)
    max_score: float = Field(default=1.0, gt=0, le=100)
    predicted_difficulty: float = Field(default=0.5, ge=0, le=1)


class WordSearchBuildRequest(BaseModel):
    words: list[str] = Field(min_length=1, max_length=30)
    size: int = Field(default=12, ge=8, le=24)


class CrosswordValidateRequest(BaseModel):
    entries: list[dict[str, Any]] = Field(min_length=1, max_length=30)


class HQActivityStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(DRAFT|IN_REVIEW|APPROVED|PUBLISHED|ARCHIVED)$"
    )


class ActivityFeedbackProfileUpsert(BaseModel):
    correction_mode: str = Field(
        pattern="^(AUTOMATIC|RUBRIC|ASSISTED|HUMAN)$"
    )
    feedback_templates: dict[str, Any] = Field(default_factory=dict)
    graduated_hints: list[dict[str, Any]] = Field(default_factory=list)
    common_errors: list[dict[str, Any]] = Field(default_factory=list)
    review_rules: dict[str, Any] = Field(default_factory=dict)
    appeal_enabled: bool = True
    rubric: dict[str, Any] | None = None


class ActivityCorrectionSimulation(BaseModel):
    response: dict[str, Any] = Field(default_factory=dict)


class ActivityFeedbackProfileRead(BaseModel):
    id: uuid.UUID
    activity_binding_id: uuid.UUID
    rubric_id: uuid.UUID | None = None
    rubric_version_id: uuid.UUID | None = None
    correction_mode: str
    feedback_templates: dict[str, Any]
    graduated_hints: list[dict[str, Any]]
    common_errors: list[dict[str, Any]]
    review_rules: dict[str, Any]
    appeal_enabled: bool
    status: str

class HQDeliveryTargetCreate(BaseModel):
    target_type: str = Field(pattern="^(CLASSROOM|CLASS|STUDENT|GROUP)$")
    target_id: uuid.UUID
    available_from: datetime | None = None
    available_until: datetime | None = None
    extra_attempts: int = Field(default=0,ge=0,le=20)
    custom_duration_minutes: int | None = Field(default=None,ge=1,le=1440)

class HQDeliveryCreate(BaseModel):
    title: str = Field(min_length=3,max_length=220)
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int = Field(default=60,ge=1,le=1440)
    max_attempts: int = Field(default=1,ge=1,le=20)
    navigation_mode: str = Field(default="FREE",pattern="^(FREE|LINEAR|SECTIONED)$")
    shuffle_questions: bool = False
    shuffle_options: bool = False
    allow_resume: bool = True
    autosave_seconds: int = Field(default=15,ge=5,le=300)
    delivery_mode: str = Field(
        default="HQ_FLOW",
        pattern="^(HQ_FLOW|ACTIVITY_ONLY|TEACHER_PREVIEW)$",
    )
    reader_required: bool = True
    release_answer_key: str = Field(
        default="AFTER_SUBMISSION",
        pattern="^(NEVER|AFTER_SUBMISSION|AFTER_WINDOW|IMMEDIATE)$",
    )
    access_settings: dict[str,Any] = Field(default_factory=dict)
    monitoring_settings: dict[str,Any] = Field(default_factory=dict)
    targets: list[HQDeliveryTargetCreate] = Field(min_length=1,max_length=500)


class HQStudentExperienceStateUpdate(BaseModel):
    assessment_session_id: uuid.UUID
    current_page_number: int = Field(default=1, ge=1)
    current_panel_number: int = Field(default=1, ge=1)
    current_activity_index: int = Field(default=0, ge=0)
    reading_progress: float = Field(default=0, ge=0, le=100)
    activity_progress: float = Field(default=0, ge=0, le=100)
    answered_count: int = Field(default=0, ge=0)
    preferences: dict[str, Any] = Field(default_factory=dict)
    navigation_state: dict[str, Any] = Field(default_factory=dict)
    last_feedback: dict[str, Any] = Field(default_factory=dict)
    sequence: int = Field(ge=1)

class HQLearningAnalyticsGenerate(BaseModel):
    scope_type: str = Field(
        default="PUBLICATION",
        pattern="^(PUBLICATION|CLASS|STUDENT|ACTIVITY)$",
    )
    scope_id: uuid.UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    @model_validator(mode="after")
    def validate_scope_and_period(self):
        if self.scope_type != "PUBLICATION" and self.scope_id is None:
            raise ValueError("scope_id is required outside PUBLICATION scope")
        if self.scope_type == "PUBLICATION" and self.scope_id is not None:
            raise ValueError("scope_id must be omitted for PUBLICATION scope")
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValueError("period_end must be on or after period_start")
        return self
