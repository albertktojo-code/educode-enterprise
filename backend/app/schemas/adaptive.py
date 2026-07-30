from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdaptiveModelCreate(BaseModel):
    code: str = Field(default="mastery-v1", min_length=2, max_length=80)
    name: str = Field(default="Modelo determinístico de domínio", min_length=3, max_length=160)
    description: str = ""
    minimum_evidence_count: int = Field(default=3, ge=1, le=100)
    thresholds_json: dict[str, float] = Field(
        default_factory=lambda: {"initial": 0.4, "developing": 0.65, "adequate": 0.85}
    )
    rules_json: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = True


class AdaptiveModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    version: int
    status: str
    description: str
    rules_json: dict[str, Any]
    thresholds_json: dict[str, Any]
    minimum_evidence_count: int
    is_default: bool
    created_at: datetime


class AdaptiveRefreshRequest(BaseModel):
    student_id: UUID | None = None
    classroom_id: UUID | None = None
    model_version_id: UUID | None = None
    generate_recommendations: bool = True
    include_spaced_review: bool = True

    @model_validator(mode="after")
    def require_scope(self) -> "AdaptiveRefreshRequest":
        if self.student_id is None and self.classroom_id is None:
            raise ValueError("Informe student_id ou classroom_id")
        return self


class AdaptiveRefreshRead(BaseModel):
    students_processed: int
    skill_states_updated: int
    recommendations_created: int
    reviews_scheduled: int
    model_version_id: UUID
    calculation_version: int


class AdaptiveStudentListItem(BaseModel):
    id: UUID
    full_name: str
    email: str
    is_active: bool


class AdaptiveProfileUpdate(BaseModel):
    preferred_formats: list[str] | None = None
    accessibility_preferences: dict[str, Any] | None = None
    teacher_notes: str | None = None


class AdaptiveProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    status: str
    preferred_formats: list[str]
    accessibility_preferences: dict[str, Any]
    teacher_notes: str
    last_calculated_at: datetime | None
    created_at: datetime


class SkillStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    dimension_type: str
    dimension_code: str
    mastery_score: float
    mastery_level: str
    confidence_score: float
    confidence_level: str
    evidence_count: int
    trend: str
    calculation_explanation: str
    first_evidence_at: datetime | None
    last_evidence_at: datetime | None
    calculated_at: datetime


class StudentAdaptiveSummary(BaseModel):
    profile: AdaptiveProfileRead
    skill_states: list[SkillStateRead]
    active_paths: int
    pending_recommendations: int
    upcoming_reviews: int
    weakest_dimensions: list[SkillStateRead]
    strongest_dimensions: list[SkillStateRead]


class PrerequisiteCreate(BaseModel):
    dimension_type: str = Field(min_length=2, max_length=30)
    dimension_code: str = Field(min_length=1, max_length=120)
    prerequisite_type: str = Field(min_length=2, max_length=30)
    prerequisite_code: str = Field(min_length=1, max_length=120)
    relation_type: str = Field(default="required", max_length=40)
    minimum_mastery: float = Field(default=0.65, ge=0, le=1)
    rationale: str = ""


class PrerequisiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    dimension_type: str
    dimension_code: str
    prerequisite_type: str
    prerequisite_code: str
    relation_type: str
    minimum_mastery: float
    rationale: str


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID | None
    classroom_id: UUID | None
    group_id: UUID | None
    recommendation_type: str
    status: str
    priority: str
    title: str
    rationale: str
    target_dimension_type: str
    target_dimension_code: str
    target_mastery: float
    confidence_score: float
    evidence_summary: dict[str, Any]
    proposed_materials: list[dict[str, Any]]
    created_by_ai: bool
    review_notes: str
    reviewed_at: datetime | None
    created_at: datetime


class RecommendationReview(BaseModel):
    decision: Literal["approved", "rejected", "changes_requested"]
    review_notes: str = ""
    proposed_materials: list[dict[str, Any]] | None = None
    target_mastery: float | None = Field(default=None, ge=0, le=1)


class RecommendationGenerateRequest(BaseModel):
    student_id: UUID
    dimension_type: str | None = None
    dimension_code: str | None = None
    use_ai_assistance: bool = False
    maximum_recommendations: int = Field(default=5, ge=1, le=20)


class PathStepCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str = ""
    step_type: str = Field(default="activity", max_length=40)
    assignment_id: UUID | None = None
    content_reference: dict[str, Any] = Field(default_factory=dict)
    is_required: bool = True
    advancement_rule: dict[str, Any] = Field(default_factory=dict)
    due_at: datetime | None = None


class LearningPathCreate(BaseModel):
    student_id: UUID | None = None
    classroom_id: UUID | None = None
    group_id: UUID | None = None
    recommendation_id: UUID | None = None
    title: str = Field(min_length=3, max_length=240)
    description: str = ""
    path_type: str = Field(default="reinforcement", max_length=40)
    goal: str = Field(min_length=3)
    target_dimension_type: str = Field(max_length=30)
    target_dimension_code: str = Field(max_length=120)
    target_mastery: float = Field(default=0.75, ge=0, le=1)
    minimum_evidence_count: int = Field(default=5, ge=1, le=100)
    settings_json: dict[str, Any] = Field(default_factory=dict)
    steps: list[PathStepCreate] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_target(self) -> "LearningPathCreate":
        if sum(value is not None for value in (self.student_id, self.classroom_id, self.group_id)) != 1:
            raise ValueError("A trilha deve ter exatamente um destino: estudante, turma ou grupo")
        return self


class PathStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    path_id: UUID
    assignment_id: UUID | None
    position: int
    step_type: str
    title: str
    description: str
    content_reference: dict[str, Any]
    is_required: bool
    status: str
    advancement_rule: dict[str, Any]
    due_at: datetime | None
    available_at: datetime | None
    completed_at: datetime | None
    completion_snapshot: dict[str, Any]


class LearningPathRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID | None
    classroom_id: UUID | None
    group_id: UUID | None
    recommendation_id: UUID | None
    title: str
    description: str
    path_type: str
    status: str
    goal: str
    target_dimension_type: str
    target_dimension_code: str
    target_mastery: float
    minimum_evidence_count: int
    settings_json: dict[str, Any]
    approved_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    steps: list[PathStepRead] = Field(default_factory=list)


class PathStatusUpdate(BaseModel):
    status: Literal["draft", "approved", "active", "paused", "completed", "cancelled"]
    notes: str = ""


class PathStepComplete(BaseModel):
    score: float | None = Field(default=None, ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)
    notes: str = ""


class StudentGroupCreate(BaseModel):
    classroom_id: UUID | None = None
    name: str = Field(min_length=3, max_length=180)
    purpose: str = ""
    target_dimension_type: str = "skill"
    target_dimension_code: str = ""
    expires_at: datetime | None = None
    student_ids: list[UUID] = Field(default_factory=list)


class StudentGroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    classroom_id: UUID | None
    name: str
    purpose: str
    target_dimension_type: str
    target_dimension_code: str
    status: str
    is_visible_to_students: bool
    expires_at: datetime | None
    created_at: datetime
    member_count: int = 0


class GroupMemberUpdate(BaseModel):
    student_ids: list[UUID] = Field(min_length=1)
    reason: str = ""


class ReviewScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    student_id: UUID
    path_id: UUID | None
    step_id: UUID | None
    dimension_type: str
    dimension_code: str
    review_number: int
    scheduled_for: datetime
    status: str
    completed_at: datetime | None
    outcome_snapshot: dict[str, Any]


class ReviewComplete(BaseModel):
    score: float = Field(ge=0, le=1)
    notes: str = ""


class PathOutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    path_id: UUID
    student_id: UUID | None
    dimension_type: str
    dimension_code: str
    mastery_before: float | None
    mastery_after: float | None
    mastery_delta: float | None
    evidence_before: int
    evidence_after: int
    completion_rate: float
    interpretation: str
    calculated_at: datetime


class AdaptiveDashboardRead(BaseModel):
    students_with_profiles: int
    active_paths: int
    pending_recommendations: int
    scheduled_reviews: int
    low_confidence_states: int
    dimensions_needing_attention: int
    temporary_groups: int
    recent_recommendations: list[RecommendationRead]
    paths_by_status: dict[str, int]
    mastery_distribution: dict[str, int]


class StudentOwnPathRead(BaseModel):
    profile: AdaptiveProfileRead
    skill_states: list[SkillStateRead]
    paths: list[LearningPathRead]
    reviews: list[ReviewScheduleRead]
    explanation: str
