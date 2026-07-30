from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.comic import (
    BalloonType,
    ComicStatus,
    ComicVersionScope,
    EditOperationStatus,
    GenerationRunStatus,
    GenerationScope,
    LayoutMode,
    PageFormat,
    PageOrientation,
    PanelShape,
    PanelSize,
    PanelStatus,
    ProposalStatus,
    PreviewReviewStatus,
    ReadingDirection,
    ReviewCommentStatus,
    ReviewDecision,
    ReviewSpecialty,
)


class NarrativeProfile(BaseModel):
    main_genre: str = Field(default="adventure", min_length=2, max_length=80)
    secondary_genre: str | None = Field(default="comedy", max_length=80)
    emotional_tone: str = Field(default="surprising", max_length=80)
    humor_level: int = Field(default=3, ge=0, le=5)
    suspense_level: int = Field(default=3, ge=0, le=5)
    sadness_level: int = Field(default=1, ge=0, le=5)
    surprise_level: int = Field(default=4, ge=0, le=5)
    max_plot_twists: int = Field(default=2, ge=0, le=4)
    ending_type: str = Field(default="surprising_positive", max_length=80)
    required_elements: list[str] = Field(default_factory=list)
    prohibited_elements: list[str] = Field(default_factory=list)


class PageLayoutInput(BaseModel):
    page_number: int = Field(ge=1, le=40)
    panel_count: int = Field(default=4, ge=1, le=8)
    page_format: PageFormat = PageFormat.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    layout_mode: LayoutMode = LayoutMode.TEMPLATE
    layout_template: str = Field(default="grid_2x2", max_length=80)
    reading_direction: ReadingDirection = ReadingDirection.LEFT_TO_RIGHT
    page_role: str = Field(default="story", max_length=40)


class ComicCreate(BaseModel):
    generation_project_id: UUID
    rag_context_id: UUID
    title: str = Field(min_length=3, max_length=240)
    page_count: int = Field(default=4, ge=1, le=40)
    default_panels_per_page: int = Field(default=4, ge=1, le=8)
    page_format: PageFormat = PageFormat.A4
    orientation: PageOrientation = PageOrientation.PORTRAIT
    narrative_profile: NarrativeProfile = Field(default_factory=NarrativeProfile)
    art_direction: dict[str, object] = Field(default_factory=dict)
    page_layouts: list[PageLayoutInput] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_page_layouts(self) -> "ComicCreate":
        page_numbers = [layout.page_number for layout in self.page_layouts]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("Cada página pode possuir apenas uma configuração de layout")
        if page_numbers and max(page_numbers) > self.page_count:
            raise ValueError("Uma configuração de layout referencia página inexistente")
        return self


class ComicUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    synopsis: str | None = Field(default=None, max_length=10000)
    status: ComicStatus | None = None
    narrative_profile: dict[str, object] | None = None
    layout_preferences: dict[str, object] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    art_direction: dict[str, object] | None = None
    canvas_config: dict[str, object] | None = None
    publication_status: str | None = Field(default=None, max_length=40)


class ComicPageUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=220)
    page_format: PageFormat | None = None
    orientation: PageOrientation | None = None
    layout_mode: LayoutMode | None = None
    layout_template: str | None = Field(default=None, max_length=80)
    reading_direction: ReadingDirection | None = None
    panel_count: int | None = Field(default=None, ge=1, le=8)
    width: float | None = Field(default=None, gt=0, le=5000)
    height: float | None = Field(default=None, gt=0, le=5000)
    margins: dict[str, object] | None = None
    notes: str | None = Field(default=None, max_length=5000)
    page_role: str | None = Field(default=None, max_length=40)
    background_config: dict[str, object] | None = None
    guides_config: dict[str, object] | None = None


class ComicPanelUpdate(BaseModel):
    panel_number: int | None = Field(default=None, ge=1, le=50)
    reading_order: int | None = Field(default=None, ge=1, le=50)
    shape: PanelShape | None = None
    size_category: PanelSize | None = None
    position_x: float | None = Field(default=None, ge=-100, le=200)
    position_y: float | None = Field(default=None, ge=-100, le=200)
    width: float | None = Field(default=None, gt=0, le=200)
    height: float | None = Field(default=None, gt=0, le=200)
    border_style: str | None = Field(default=None, max_length=40)
    border_width: float | None = Field(default=None, ge=0, le=20)
    rotation: float | None = Field(default=None, ge=-180, le=180)
    z_index: int | None = Field(default=None, ge=-100, le=100)
    is_full_bleed: bool | None = None
    clipping_mode: str | None = Field(default=None, max_length=40)
    narrative_goal: str | None = Field(default=None, max_length=5000)
    pedagogical_goal: str | None = Field(default=None, max_length=5000)
    ct_pillar_codes: list[str] | None = None
    scene_description: str | None = Field(default=None, max_length=10000)
    previous_panel_summary: str | None = Field(default=None, max_length=5000)
    next_panel_hook: str | None = Field(default=None, max_length=5000)
    initial_state: dict[str, object] | None = None
    final_state: dict[str, object] | None = None
    emotion: str | None = Field(default=None, max_length=80)
    plot_function: str | None = Field(default=None, max_length=100)
    status: PanelStatus | None = None
    locked_elements: list[str] | None = None
    visual_prompt: dict[str, object] | None = None
    frozen_assets: dict[str, object] | None = None
    pacing: str | None = Field(default=None, max_length=40)
    image_asset_path: str | None = Field(default=None, max_length=500)
    alt_text: str | None = Field(default=None, max_length=5000)
    audio_description: str | None = Field(default=None, max_length=10000)
    text_word_limit: int | None = Field(default=None, ge=10, le=500)


class ComicBalloonCreate(BaseModel):
    sequence_number: int = Field(ge=1, le=50)
    speaker_character_id: UUID | None = None
    speaker_name_snapshot: str | None = Field(default=None, max_length=160)
    balloon_type: BalloonType = BalloonType.SPEECH
    text: str = Field(min_length=1, max_length=3000)
    emotion: str | None = Field(default=None, max_length=80)
    responds_to_balloon_id: UUID | None = None
    pedagogical_function: str | None = Field(default=None, max_length=120)
    position_x: float = Field(default=10.0, ge=-50, le=150)
    position_y: float = Field(default=10.0, ge=-50, le=150)
    width: float = Field(default=40.0, gt=0, le=150)
    height: float = Field(default=20.0, gt=0, le=150)
    is_locked: bool = False
    layer_config: dict[str, object] = Field(default_factory=dict)


class ComicBalloonUpdate(BaseModel):
    sequence_number: int | None = Field(default=None, ge=1, le=50)
    speaker_character_id: UUID | None = None
    speaker_name_snapshot: str | None = Field(default=None, max_length=160)
    balloon_type: BalloonType | None = None
    text: str | None = Field(default=None, min_length=1, max_length=3000)
    emotion: str | None = Field(default=None, max_length=80)
    responds_to_balloon_id: UUID | None = None
    pedagogical_function: str | None = Field(default=None, max_length=120)
    position_x: float | None = Field(default=None, ge=-50, le=150)
    position_y: float | None = Field(default=None, ge=-50, le=150)
    width: float | None = Field(default=None, gt=0, le=150)
    height: float | None = Field(default=None, gt=0, le=150)
    is_locked: bool | None = None
    layer_config: dict[str, object] | None = None


class RegenerateRequest(BaseModel):
    scope: GenerationScope
    page_id: UUID | None = None
    panel_id: UUID | None = None
    preserve_dialogue: bool = False
    preserve_scene: bool = False
    change_instruction: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def validate_target(self) -> "RegenerateRequest":
        if self.scope == GenerationScope.PAGE and self.page_id is None:
            raise ValueError("page_id é obrigatório para regenerar uma página")
        if (
            self.scope
            in {
                GenerationScope.PANEL,
                GenerationScope.BALLOONS,
                GenerationScope.DIALOGUE,
                GenerationScope.SCENE,
                GenerationScope.FROM_PANEL,
            }
            and self.panel_id is None
        ):
            raise ValueError("panel_id é obrigatório para o escopo selecionado")
        return self


class RegenerationProposalRequest(RegenerateRequest):
    alternative_count: int = Field(default=3, ge=1, le=5)
    tones: list[str] = Field(
        default_factory=lambda: ["funny", "emotional", "mysterious"], max_length=5
    )


class PanelLockRequest(BaseModel):
    locked_elements: list[str] = Field(default_factory=list, max_length=30)


class ReviewCommentCreate(BaseModel):
    specialty: ReviewSpecialty
    body: str = Field(min_length=3, max_length=5000)
    page_id: UUID | None = None
    panel_id: UUID | None = None
    balloon_id: UUID | None = None
    anchor_x: float | None = Field(default=None, ge=0, le=100)
    anchor_y: float | None = Field(default=None, ge=0, le=100)
    priority: str = Field(default="normal", pattern="^(low|normal|high|blocking)$")


class ReviewCommentUpdate(BaseModel):
    status: ReviewCommentStatus


class ReviewApprovalUpsert(BaseModel):
    specialty: ReviewSpecialty
    decision: ReviewDecision
    notes: str | None = Field(default=None, max_length=5000)


class AutosaveRequest(BaseModel):
    client_revision: int = Field(ge=0)
    expected_edit_revision: int | None = Field(default=None, ge=0)
    draft_payload: dict[str, object] = Field(default_factory=dict)


class VersionRestoreRequest(BaseModel):
    change_description: str = Field(default="Restauração de versão", min_length=3, max_length=5000)


class StabilityFindingRead(BaseModel):
    severity: str
    code: str
    message: str
    page_id: UUID | None = None
    panel_id: UUID | None = None
    balloon_id: UUID | None = None


class PageDensityRead(BaseModel):
    page_id: UUID
    page_number: int
    panel_coverage_percent: float
    word_count: int
    density_score: float
    classification: str


class StabilityReportRead(BaseModel):
    comic_id: UUID
    score: float
    language_metrics: dict[str, float | int]
    page_densities: list[PageDensityRead]
    findings: list[StabilityFindingRead]
    generated_at: datetime


class CanvasChecklistItemRead(BaseModel):
    code: str
    label: str
    passed: bool
    required: bool


class CanvasReadinessRead(BaseModel):
    comic_id: UUID
    status: str
    continuity_score: float
    checklist: list[CanvasChecklistItemRead]
    checked_at: datetime


class RegenerationPolicyRead(BaseModel):
    comic_id: UUID
    scope: GenerationScope
    affected_panel_ids: list[UUID]
    mutable_elements: list[str]
    locked_elements: list[str]
    immutable_facts: list[str]
    warnings: list[str]


class ServerDraftRead(BaseModel):
    comic_id: UUID
    autosave_revision: int
    edit_revision: int
    last_saved_at: datetime | None
    draft_payload: dict[str, object]


class ComicBalloonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    panel_id: UUID
    sequence_number: int
    speaker_character_id: UUID | None
    speaker_name_snapshot: str | None
    balloon_type: BalloonType
    text: str
    emotion: str | None
    responds_to_balloon_id: UUID | None
    pedagogical_function: str | None
    position_x: float
    position_y: float
    width: float
    height: float
    is_locked: bool
    layer_config: dict[str, object]
    created_at: datetime
    updated_at: datetime


class ComicPanelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    page_id: UUID
    panel_number: int
    reading_order: int
    shape: PanelShape
    size_category: PanelSize
    position_x: float
    position_y: float
    width: float
    height: float
    border_style: str
    border_width: float
    rotation: float
    z_index: int
    is_full_bleed: bool
    clipping_mode: str
    narrative_goal: str
    pedagogical_goal: str
    ct_pillar_codes: list[str]
    scene_description: str
    previous_panel_summary: str
    next_panel_hook: str
    initial_state: dict[str, object]
    final_state: dict[str, object]
    emotion: str
    plot_function: str
    continuity_notes: list[str]
    status: PanelStatus
    locked_elements: list[str]
    visual_prompt: dict[str, object]
    frozen_assets: dict[str, object]
    pacing: str
    image_asset_path: str | None
    alt_text: str | None
    audio_description: str | None
    text_word_limit: int
    preview_review_status: PreviewReviewStatus
    preview_reviewed_by_user_id: UUID | None
    preview_reviewed_at: datetime | None
    preview_review_notes: str | None
    created_at: datetime
    updated_at: datetime
    balloons: list[ComicBalloonRead]


class ComicPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    comic_id: UUID
    page_number: int
    title: str | None
    page_format: PageFormat
    orientation: PageOrientation
    layout_mode: LayoutMode
    layout_template: str
    reading_direction: ReadingDirection
    panel_count: int
    width: float
    height: float
    margins: dict[str, object]
    notes: str | None
    page_role: str
    background_config: dict[str, object]
    guides_config: dict[str, object]
    preview_review_status: PreviewReviewStatus
    preview_reviewed_by_user_id: UUID | None
    preview_reviewed_at: datetime | None
    preview_review_notes: str | None
    created_at: datetime
    updated_at: datetime
    panels: list[ComicPanelRead]


class ComicVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    comic_id: UUID
    version_number: int
    scope: ComicVersionScope
    target_page_id: UUID | None
    target_panel_id: UUID | None
    target_balloon_id: UUID | None
    change_description: str
    snapshot_json: dict[str, object]
    created_by_user_id: UUID
    created_at: datetime


class ComicGenerationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    comic_id: UUID
    requested_by_user_id: UUID
    scope: GenerationScope
    target_page_id: UUID | None
    target_panel_id: UUID | None
    status: GenerationRunStatus
    provider: str
    model: str
    configuration: dict[str, object]
    result_summary: dict[str, object]
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class ComicReviewCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    comic_id: UUID
    page_id: UUID | None
    panel_id: UUID | None
    balloon_id: UUID | None
    author_user_id: UUID
    author_name_snapshot: str
    specialty: ReviewSpecialty
    body: str
    anchor_x: float | None
    anchor_y: float | None
    priority: str
    status: ReviewCommentStatus
    created_at: datetime
    resolved_at: datetime | None


class ComicReviewApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    comic_id: UUID
    specialty: ReviewSpecialty
    decision: ReviewDecision
    reviewer_user_id: UUID
    reviewer_name_snapshot: str
    notes: str | None
    reviewed_at: datetime


class ComicRegenerationProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    comic_id: UUID
    requested_by_user_id: UUID
    scope: GenerationScope
    target_page_id: UUID | None
    target_panel_id: UUID | None
    label: str
    tone: str
    instruction: str | None
    proposal_payload: dict[str, object]
    status: ProposalStatus
    created_at: datetime
    accepted_at: datetime | None


class ComicEditOperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    comic_id: UUID
    actor_user_id: UUID
    operation_type: str
    target_page_id: UUID | None
    target_panel_id: UUID | None
    target_balloon_id: UUID | None
    status: EditOperationStatus
    created_at: datetime
    reverted_at: datetime | None


class NarrativeMapItem(BaseModel):
    page_number: int
    panel_id: UUID
    reading_order: int
    plot_function: str
    pacing: str
    emotion: str
    narrative_goal: str
    open_questions: list[str]
    clues: list[str]
    word_count: int
    over_text_limit: bool


class NarrativeMapRead(BaseModel):
    comic_id: UUID
    items: list[NarrativeMapItem]
    pacing_warnings: list[str]
    unresolved_clues: list[str]


class ComicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    generation_project_id: UUID
    rag_context_id: UUID
    created_by_user_id: UUID
    created_by_name_snapshot: str
    title: str
    synopsis: str
    status: ComicStatus
    current_version: int
    narrative_profile: dict[str, object]
    layout_preferences: dict[str, object]
    story_state: dict[str, object]
    continuity_score: float
    pedagogical_score: float
    notes: str | None
    art_direction: dict[str, object]
    canvas_config: dict[str, object]
    publication_status: str
    review_state: dict[str, object]
    autosave_revision: int
    last_saved_at: datetime | None
    edit_revision: int
    last_editor_user_id: UUID | None
    last_editor_name_snapshot: str | None
    last_editor_at: datetime | None
    canvas_readiness_status: str
    canvas_readiness_checked_at: datetime | None
    preview_status: PreviewReviewStatus
    preview_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    pages: list[ComicPageRead]
    versions: list[ComicVersionRead]
    generation_runs: list[ComicGenerationRunRead]
    review_comments: list[ComicReviewCommentRead]
    review_approvals: list[ComicReviewApprovalRead]
    regeneration_proposals: list[ComicRegenerationProposalRead]
    edit_operations: list[ComicEditOperationRead]


class ComicSummary(BaseModel):
    id: UUID
    generation_project_id: UUID
    rag_context_id: UUID
    title: str
    synopsis: str
    status: ComicStatus
    current_version: int
    page_count: int
    panel_count: int
    continuity_score: float
    pedagogical_score: float
    updated_at: datetime


class ContinuityIssue(BaseModel):
    severity: str
    code: str
    message: str
    page_id: UUID | None = None
    panel_id: UUID | None = None
    balloon_id: UUID | None = None


class ContinuityReport(BaseModel):
    comic_id: UUID
    score: float
    is_valid: bool
    issue_count: int
    issues: list[ContinuityIssue]


class LayoutTemplateRead(BaseModel):
    code: str
    label: str
    panel_count: int
    description: str
    panels: list[dict[str, object]]


class CanvasExport(BaseModel):
    schema_version: str
    editor: str
    document: dict[str, object]


class PanelReorderRequest(BaseModel):
    panel_ids: list[UUID] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def unique_panels(self) -> "PanelReorderRequest":
        if len(self.panel_ids) != len(set(self.panel_ids)):
            raise ValueError("A lista de quadros não pode conter duplicidades")
        return self
