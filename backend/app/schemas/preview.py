from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.comic import PreviewReviewStatus


class PreviewReviewRequest(BaseModel):
    status: PreviewReviewStatus
    notes: str | None = Field(default=None, max_length=5000)
    lock_after_approval: bool = False


class PreviewReviewResult(BaseModel):
    comic_id: UUID
    target_type: Literal["page", "panel"]
    target_id: UUID
    status: PreviewReviewStatus
    reviewed_by_user_id: UUID
    reviewed_by_name: str
    reviewed_at: datetime
    notes: str | None


class StoryboardDialogueRead(BaseModel):
    balloon_id: UUID
    sequence_number: int
    speaker: str
    type: str
    text: str
    emotion: str | None = None


class StoryboardSceneRead(BaseModel):
    sequence_number: int
    page_id: UUID
    page_number: int
    page_role: str
    panel_id: UUID
    panel_number: int
    reading_order: int
    review_status: PreviewReviewStatus
    scene_summary: str
    narrative_goal: str
    pedagogical_goal: str
    ct_pillar_codes: list[str]
    shot_type: str
    camera_direction: object | None = None
    action: object
    emotion: str
    pacing: str
    plot_function: str
    previous_panel_summary: str
    next_panel_hook: str
    initial_state: dict[str, object]
    final_state: dict[str, object]
    transition: str
    estimated_duration_seconds: int
    dialogue: list[StoryboardDialogueRead]
    image_asset_path: str | None = None
    alt_text: str | None = None
    audio_description: str | None = None


class StoryboardPlotPointRead(BaseModel):
    sequence_number: int
    page_number: int
    panel_number: int
    type: str
    summary: str


class StoryboardRead(BaseModel):
    comic_id: UUID
    title: str
    version: int
    page_count: int
    scene_count: int
    estimated_duration_seconds: int
    emotional_arc: list[str]
    plot_points: list[StoryboardPlotPointRead]
    scenes: list[StoryboardSceneRead]


class PreviewFindingRead(BaseModel):
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    page_id: UUID | None = None
    panel_id: UUID | None = None


class PreviewChecklistItemRead(BaseModel):
    code: str
    label: str
    passed: bool


class PreviewValidationRead(BaseModel):
    comic_id: UUID
    status: Literal["ready", "ready_with_warnings", "blocked"]
    review_coverage_percent: float
    approved_pages: int
    total_pages: int
    approved_panels: int
    total_panels: int
    error_count: int
    warning_count: int
    findings: list[PreviewFindingRead]
    checklist: list[PreviewChecklistItemRead]


class VersionPanelChangeRead(BaseModel):
    panel_id: str
    status: str
    changed_fields: list[str]


class VersionPageChangeRead(BaseModel):
    page_id: str
    page_number: int | None
    status: str
    panel_changes: list[VersionPanelChangeRead]


class VersionComparisonRead(BaseModel):
    from_version: int
    to_version: int
    top_level_changes: list[str]
    page_summary: dict[str, int]
    changed_pages: list[VersionPageChangeRead]


class StudentPreviewRead(BaseModel):
    comic_id: UUID
    title: str
    version: int
    reading_direction: str
    pages: list[dict[str, Any]]
    accessibility: dict[str, Any]
    is_simulation: bool = True
