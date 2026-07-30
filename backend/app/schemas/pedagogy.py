from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.pedagogy import (
    AssessmentDesign,
    DifficultyLevel,
    FidelityLevel,
    GenerationStatus,
    IntegrationMode,
    PillarRelevance,
    PrivacyLevel,
    SourceMode,
    SourceType,
)


class PillarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str
    pedagogical_examples: str | None
    is_active: bool


class GenerationPillarInput(BaseModel):
    pillar_id: UUID
    relevance: PillarRelevance = PillarRelevance.HIGH
    application_description: str | None = Field(default=None, max_length=3000)


class GenerationPillarRead(BaseModel):
    id: UUID
    pillar_id: UUID
    code: str
    name: str
    relevance: PillarRelevance
    application_description: str | None
    selected_by: str


class GenerationSourceInput(BaseModel):
    source_type: SourceType
    document_id: UUID | None = None
    chapter_id: UUID | None = None
    learning_unit_id: UUID | None = None
    content_text: str | None = Field(default=None, max_length=50000)
    instructions: str | None = Field(default=None, max_length=10000)
    priority: int = Field(default=0, ge=0, le=100)
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    is_primary: bool = False
    allow_ai_expansion: bool = True


class GenerationSourceRead(GenerationSourceInput):
    id: UUID


class LearningUnitBase(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    subject_id: UUID | None = None
    description: str | None = Field(default=None, max_length=10000)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)
    school_year: str | None = Field(default=None, max_length=80)
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    disciplinary_objective: str | None = Field(default=None, max_length=5000)
    is_confirmed: bool = False
    position: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_pages(self) -> "LearningUnitBase":
        if self.start_page is not None and self.end_page is not None:
            if self.end_page < self.start_page:
                raise ValueError("A página final deve ser maior ou igual à página inicial")
        return self


class LearningUnitCreate(LearningUnitBase):
    chapter_id: UUID | None = None


class LearningUnitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=240)
    subject_id: UUID | None = None
    description: str | None = Field(default=None, max_length=10000)
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)
    school_year: str | None = Field(default=None, max_length=80)
    difficulty_level: DifficultyLevel | None = None
    disciplinary_objective: str | None = Field(default=None, max_length=5000)
    is_confirmed: bool | None = None
    position: int | None = Field(default=None, ge=0)


class LearningUnitRead(LearningUnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    chapter_id: UUID | None
    created_at: datetime
    updated_at: datetime


class GenerationProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=220)
    project_id: UUID | None = None
    source_mode: SourceMode
    subject_id: UUID | None = None
    custom_subject_name: str | None = Field(default=None, max_length=160)
    school_year: str | None = Field(default=None, max_length=80)
    topic: str = Field(min_length=2, max_length=240)
    disciplinary_objective: str | None = Field(default=None, max_length=5000)
    computational_thinking_objective: str | None = Field(default=None, max_length=5000)
    teacher_text: str | None = Field(default=None, max_length=50000)
    teacher_instructions: str | None = Field(default=None, max_length=10000)
    allow_ai_expansion: bool = True
    fidelity_level: FidelityLevel = FidelityLevel.BALANCED
    integration_mode: IntegrationMode = IntegrationMode.BALANCED
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    privacy_level: PrivacyLevel = PrivacyLevel.PRIVATE
    credit_name: str | None = Field(default=None, max_length=180)
    rights_confirmed: bool = False
    bncc_skills: list[str] = Field(default_factory=list, max_length=30)
    desired_materials: list[str] = Field(default_factory=list, max_length=20)
    accessibility_options: list[str] = Field(default_factory=list, max_length=20)
    source_priority: list[str] = Field(default_factory=list, max_length=10)
    assessment_design: AssessmentDesign = AssessmentDesign.NONE
    assessment_notes: str | None = Field(default=None, max_length=5000)
    cognitive_levels: list[str] = Field(default_factory=list, max_length=6)
    measurable_objectives: list[str] = Field(default_factory=list, max_length=50)
    evaluation_plan: dict[str, object] = Field(default_factory=dict)
    author_credit_settings: dict[str, object] = Field(default_factory=dict)
    status: GenerationStatus = GenerationStatus.DRAFT
    pillars: list[GenerationPillarInput] = Field(default_factory=list, max_length=4)
    sources: list[GenerationSourceInput] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_source_mode(self) -> "GenerationProjectCreate":
        if self.subject_id is None and not (self.custom_subject_name or "").strip():
            raise ValueError("Selecione uma disciplina ou informe uma disciplina personalizada")
        if self.source_mode == SourceMode.TEACHER_TEXT and not (self.teacher_text or "").strip():
            raise ValueError("Digite ou cole a história do professor")
        if self.source_mode == SourceMode.DOCUMENT:
            if not any(source.document_id for source in self.sources):
                raise ValueError("Selecione ao menos um PDF para o modo documento")
        if self.source_mode == SourceMode.HYBRID and len(self.sources) < 2:
            raise ValueError("O modo híbrido exige pelo menos duas fontes")
        if not self.pillars:
            raise ValueError("Selecione ao menos um pilar do Pensamento Computacional")
        if not self.desired_materials:
            raise ValueError("Selecione ao menos um tipo de material")
        return self


class GenerationProjectUpdate(BaseModel):
    source_mode: SourceMode | None = None
    title: str | None = Field(default=None, min_length=2, max_length=220)
    project_id: UUID | None = None
    subject_id: UUID | None = None
    custom_subject_name: str | None = Field(default=None, max_length=160)
    school_year: str | None = Field(default=None, max_length=80)
    topic: str | None = Field(default=None, min_length=2, max_length=240)
    disciplinary_objective: str | None = Field(default=None, max_length=5000)
    computational_thinking_objective: str | None = Field(default=None, max_length=5000)
    teacher_text: str | None = Field(default=None, max_length=50000)
    teacher_instructions: str | None = Field(default=None, max_length=10000)
    allow_ai_expansion: bool | None = None
    fidelity_level: FidelityLevel | None = None
    integration_mode: IntegrationMode | None = None
    difficulty_level: DifficultyLevel | None = None
    privacy_level: PrivacyLevel | None = None
    credit_name: str | None = Field(default=None, max_length=180)
    rights_confirmed: bool | None = None
    bncc_skills: list[str] | None = Field(default=None, max_length=30)
    desired_materials: list[str] | None = Field(default=None, max_length=20)
    accessibility_options: list[str] | None = Field(default=None, max_length=20)
    source_priority: list[str] | None = Field(default=None, max_length=10)
    assessment_design: AssessmentDesign | None = None
    assessment_notes: str | None = Field(default=None, max_length=5000)
    cognitive_levels: list[str] | None = Field(default=None, max_length=6)
    measurable_objectives: list[str] | None = Field(default=None, max_length=50)
    evaluation_plan: dict[str, object] | None = None
    author_credit_settings: dict[str, object] | None = None
    status: GenerationStatus | None = None
    pillars: list[GenerationPillarInput] | None = Field(default=None, max_length=4)
    sources: list[GenerationSourceInput] | None = Field(default=None, max_length=20)


class GenerationProjectRead(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID | None
    created_by_user_id: UUID
    created_by_name_snapshot: str
    title: str
    source_mode: SourceMode
    subject_id: UUID | None
    custom_subject_name: str | None
    school_year: str | None
    topic: str
    disciplinary_objective: str | None
    computational_thinking_objective: str | None
    teacher_text: str | None
    teacher_instructions: str | None
    allow_ai_expansion: bool
    fidelity_level: FidelityLevel
    integration_mode: IntegrationMode
    difficulty_level: DifficultyLevel
    privacy_level: PrivacyLevel
    credit_name: str
    rights_confirmed: bool
    bncc_skills: list[str]
    desired_materials: list[str]
    accessibility_options: list[str]
    source_priority: list[str]
    assessment_design: AssessmentDesign
    assessment_notes: str | None
    cognitive_levels: list[str]
    measurable_objectives: list[str]
    evaluation_plan: dict[str, object]
    author_credit_settings: dict[str, object]
    status: GenerationStatus
    pillars: list[GenerationPillarRead]
    sources: list[GenerationSourceRead]
    mock_proposal: dict[str, object] | None
    created_at: datetime
    updated_at: datetime


class CatalogResponse(BaseModel):
    pillars: list[PillarRead]
    standard_subject_codes: list[str]
    material_types: list[str]
    accessibility_options: list[str]
    assessment_designs: list[str]


class PillarRecommendationRequest(BaseModel):
    subject_name: str = Field(min_length=2, max_length=160)
    topic: str = Field(min_length=2, max_length=240)


class PillarRecommendation(BaseModel):
    pillar_id: UUID
    code: str
    name: str
    relevance: PillarRelevance
    justification: str


class MockProposalResponse(BaseModel):
    generation_project_id: UUID
    proposal: dict[str, object]
