from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.studio import (
    PackageMaterialStatus,
    PackageStatus,
    PublicationReadiness,
    StudioCreationMode,
    StudioDraftStatus,
    StudioMaterialType,
)


class PagePlanItem(BaseModel):
    page_number: int = Field(ge=1, le=40)
    role: str = Field(default="story", max_length=40)
    panel_count: int = Field(default=4, ge=1, le=8)
    layout_template: str = Field(default="grid_2x2", max_length=80)
    narrative_function: str = Field(default="development", max_length=120)


class ArtDirectionInput(BaseModel):
    preset_code: str = Field(default="cartoon_educational", max_length=80)
    secondary_influence: str | None = Field(default=None, max_length=80)
    influence_strength: str = Field(default="moderate", max_length=20)
    color_mode: str = Field(default="color", max_length=40)
    detail_level: str = Field(default="medium", max_length=40)
    expression_intensity: str = Field(default="medium", max_length=40)
    emotional_palette: str = Field(default="joyful", max_length=60)
    reading_direction: str = Field(default="left_to_right", max_length=40)
    allow_intentional_style_shifts: bool = True
    custom_rules: list[str] = Field(default_factory=list)


class TeacherStudioDraftCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    creation_mode: StudioCreationMode = StudioCreationMode.QUICK
    primary_material: StudioMaterialType = StudioMaterialType.COMIC
    generation_project_id: UUID | None = None
    rag_context_id: UUID | None = None
    subject_name: str = Field(default="", max_length=160)
    school_year: str = Field(default="", max_length=80)
    topic: str = Field(default="", max_length=240)
    objective: str = Field(default="", max_length=3000)
    selected_outputs: list[StudioMaterialType] = Field(default_factory=lambda: [StudioMaterialType.COMIC])
    page_plan: list[PagePlanItem] = Field(default_factory=list)
    art_direction: ArtDirectionInput = Field(default_factory=ArtDirectionInput)
    accessibility_options: list[str] = Field(default_factory=list)
    wizard_data: dict[str, object] = Field(default_factory=dict)


class TeacherStudioDraftUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    creation_mode: StudioCreationMode | None = None
    primary_material: StudioMaterialType | None = None
    generation_project_id: UUID | None = None
    rag_context_id: UUID | None = None
    subject_name: str | None = Field(default=None, max_length=160)
    school_year: str | None = Field(default=None, max_length=80)
    topic: str | None = Field(default=None, max_length=240)
    objective: str | None = Field(default=None, max_length=3000)
    current_step: int | None = Field(default=None, ge=1, le=10)
    selected_outputs: list[StudioMaterialType] | None = None
    page_plan: list[PagePlanItem] | None = None
    art_direction: ArtDirectionInput | None = None
    accessibility_options: list[str] | None = None
    wizard_data: dict[str, object] | None = None
    status: StudioDraftStatus | None = None


class RecommendPagesRequest(BaseModel):
    story_pages: int = Field(default=4, ge=1, le=24)
    include_cover: bool = True
    include_exercises: bool = True
    include_answer_key: bool = True
    include_teacher_guide: bool = False
    narrative_profile: str = Field(default="balanced", max_length=40)


class PackageCreateRequest(BaseModel):
    comic_id: UUID | None = None
    outputs: list[StudioMaterialType] | None = None


class CanvasPanelPlacement(BaseModel):
    panel_id: UUID
    position_x: float = Field(ge=0, le=100)
    position_y: float = Field(ge=0, le=100)
    width: float = Field(gt=1, le=100)
    height: float = Field(gt=1, le=100)
    rotation: float = Field(default=0, ge=-45, le=45)
    z_index: int = Field(default=0, ge=0, le=200)


class CanvasBalloonPlacement(BaseModel):
    balloon_id: UUID
    position_x: float = Field(ge=0, le=100)
    position_y: float = Field(ge=0, le=100)
    width: float = Field(gt=1, le=100)
    height: float = Field(gt=1, le=100)
    layer_config: dict[str, object] = Field(default_factory=dict)


class CanvasBulkUpdate(BaseModel):
    expected_revision: int | None = Field(default=None, ge=0)
    page_id: UUID
    panels: list[CanvasPanelPlacement] = Field(default_factory=list)
    balloons: list[CanvasBalloonPlacement] = Field(default_factory=list)
    canvas_config: dict[str, object] = Field(default_factory=dict)


class PageCreateRequest(BaseModel):
    role: str = Field(default="story", max_length=40)
    panel_count: int = Field(default=4, ge=1, le=8)
    layout_template: str = Field(default="grid_2x2", max_length=80)
    title: str | None = Field(default=None, max_length=220)


class PageReorderRequest(BaseModel):
    page_ids: list[UUID] = Field(min_length=1)


class ArtDirectionPresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    code: str
    name: str
    category: str
    description: str
    preview_config: dict[str, object]
    visual_rules: dict[str, object]
    age_groups: list[str]
    is_system: bool
    is_active: bool


class TeacherStudioDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_by_user_id: UUID
    generation_project_id: UUID | None
    rag_context_id: UUID | None
    title: str
    creation_mode: StudioCreationMode
    primary_material: StudioMaterialType
    subject_name: str
    school_year: str
    topic: str
    objective: str
    current_step: int
    wizard_data: dict[str, object]
    selected_outputs: list[str]
    page_plan: list[dict[str, object]]
    art_direction: dict[str, object]
    accessibility_options: list[str]
    status: StudioDraftStatus
    created_at: datetime
    updated_at: datetime


class PackageMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    material_type: StudioMaterialType
    title: str
    content: dict[str, object]
    status: PackageMaterialStatus
    position: int
    created_at: datetime


class PublicationPreparationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    readiness: PublicationReadiness
    checklist: list[dict[str, object]]
    manifest: dict[str, object]
    prepared_at: datetime


class PedagogicalPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    draft_id: UUID
    generation_project_id: UUID | None
    comic_id: UUID | None
    created_by_user_id: UUID
    created_by_name_snapshot: str
    title: str
    outputs: list[str]
    shared_context: dict[str, object]
    art_direction_snapshot: dict[str, object]
    status: PackageStatus
    preparation_report: dict[str, object]
    created_at: datetime
    updated_at: datetime
    materials: list[PackageMaterialRead]
    publication_preparations: list[PublicationPreparationRead]
