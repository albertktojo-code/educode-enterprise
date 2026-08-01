from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import (
    AdaptationType,
    ApprovalStatus,
    DifficultyClassification,
    DifficultyLevel,
    EquivalenceStatus,
    ErrorType,
    FeedbackType,
    GenerationMethod,
    HintLevel,
    HintReleaseType,
    ProgressionAction,
    ReviewStatus,
    RuleStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GraduatedHintCreate(BaseModel):
    resource_type: str = Field(min_length=2, max_length=60)
    resource_id: uuid.UUID
    question_id: uuid.UUID | None = None
    learning_node_id: uuid.UUID | None = None
    level: HintLevel
    level_order: int = Field(ge=1, le=5)
    title: str = Field(min_length=2, max_length=180)
    content: str = Field(min_length=2, max_length=10000)
    content_format: str = Field(default="PLAIN_TEXT", max_length=30)
    release_rule: dict[str, Any] = Field(default_factory=dict)
    penalty_rule: dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=1, ge=1)
    status: RuleStatus = RuleStatus.DRAFT


class GraduatedHintRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    question_id: uuid.UUID | None
    learning_node_id: uuid.UUID | None
    level: str
    level_order: int
    title: str
    content: str
    release_rule: dict[str, Any]
    penalty_rule: dict[str, Any]
    version: int
    status: str
    created_at: datetime
    updated_at: datetime


class HintSelectionInput(BaseModel):
    used_hint_ids: list[uuid.UUID] = Field(default_factory=list)
    max_level_order: int = Field(default=5, ge=1, le=5)
    incorrect_attempts: int = Field(default=0, ge=0)
    elapsed_seconds: int = Field(default=0, ge=0)
    requested_manually: bool = False
    accessibility_required: bool = False


class HintSelectionResult(BaseModel):
    selected_hint_id: uuid.UUID | None
    selected_level: HintLevel | None
    reason: str
    exhausted: bool


class HintUsageCreate(BaseModel):
    student_id: uuid.UUID
    classroom_id: uuid.UUID | None = None
    attempt_id: uuid.UUID
    question_id: uuid.UUID | None = None
    graduated_hint_id: uuid.UUID
    release_type: HintReleaseType
    release_reason: str | None = Field(default=None, max_length=1000)


class SpacedReviewInput(BaseModel):
    mastery_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    result_score: float = Field(ge=0, le=1)
    hint_level_used: int = Field(default=0, ge=0, le=5)
    previous_interval_days: int | None = Field(default=None, ge=1, le=3650)
    overdue_days: int = Field(default=0, ge=0, le=3650)
    reference_date: date | None = None
    interval_policy: dict[str, int] = Field(
        default_factory=lambda: {
            "very_low": 1,
            "low": 3,
            "adequate": 7,
            "advanced": 15,
            "mastered": 30,
        }
    )


class SpacedReviewResult(BaseModel):
    interval_days: int
    scheduled_for: date
    status: ReviewStatus
    priority: int = Field(ge=1, le=100)
    reason: str
    rule_version: str = "1.0.0"


class FeedbackAdaptInput(BaseModel):
    is_correct: bool
    mastery_level: str = Field(min_length=2, max_length=40)
    error_type: ErrorType = ErrorType.NONE
    attempt_number: int = Field(default=1, ge=1)
    hint_level_used: int = Field(default=0, ge=0, le=5)
    skill_name: str = Field(min_length=2, max_length=240)
    original_feedback: str | None = Field(default=None, max_length=5000)
    preferred_language_complexity: str = Field(default="STANDARD", max_length=30)


class FeedbackAdaptResult(BaseModel):
    feedback_type: FeedbackType
    content: str
    next_action: ProgressionAction
    explanation: str
    requires_teacher_review: bool
    rule_version: str = "1.0.0"


class IndividualDifficultyInput(BaseModel):
    mastery_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    recent_performance: float = Field(ge=0, le=1)
    average_hint_level: float = Field(default=0, ge=0, le=5)
    prerequisite_mastery: float = Field(default=1, ge=0, le=1)
    previous_difficulty_score: float | None = Field(default=None, ge=0, le=1)
    max_change_per_cycle: float = Field(default=0.20, ge=0.01, le=0.50)


class IndividualDifficultyResult(BaseModel):
    difficulty_score: float = Field(ge=0, le=1)
    difficulty_level: DifficultyLevel
    confidence_score: float = Field(ge=0, le=1)
    change: float
    action: str
    reason: str
    requires_teacher_review: bool
    calculation_version: str = "1.0.0"


class ObservedDifficultyInput(BaseModel):
    predicted_difficulty: float = Field(ge=0, le=1)
    attempts_count: int = Field(ge=0)
    correct_count: int = Field(ge=0)
    average_attempts: float = Field(default=1, ge=1, le=20)
    average_hint_level: float = Field(default=0, ge=0, le=5)
    abandonment_rate: float = Field(default=0, ge=0, le=1)
    average_time_seconds: float = Field(default=0, ge=0)
    expected_time_seconds: float = Field(default=0, ge=0)
    minimum_sample_size: int = Field(default=10, ge=1, le=10000)
    review_difference_threshold: float = Field(default=0.20, ge=0.01, le=1)

    @field_validator("correct_count")
    @classmethod
    def correct_must_be_possible(cls, value: int, info: Any) -> int:
        attempts = info.data.get("attempts_count")
        if attempts is not None and value > attempts:
            raise ValueError("correct_count não pode superar attempts_count")
        return value


class ObservedDifficultyResult(BaseModel):
    predicted_difficulty: float
    observed_difficulty: float | None
    difference: float | None
    classification: DifficultyClassification
    sample_size: int
    confidence_score: float
    metrics: dict[str, float]
    requires_review: bool
    calculation_version: str = "1.0.0"


class ProgressionRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    description: str = Field(min_length=3, max_length=5000)
    scope_type: str = Field(min_length=2, max_length=40)
    scope_id: uuid.UUID | None = None
    conditions: dict[str, Any]
    result_action: ProgressionAction
    priority: int = Field(default=100, ge=1, le=10000)
    requires_teacher_approval: bool = False
    status: RuleStatus = RuleStatus.DRAFT
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class ProgressionRuleRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    version: str
    description: str
    scope_type: str
    scope_id: uuid.UUID | None
    conditions: dict[str, Any]
    result_action: str
    priority: int
    requires_teacher_approval: bool
    status: str
    created_at: datetime
    updated_at: datetime


class ProgressionEvaluationInput(BaseModel):
    mastery_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    evidences_count: int = Field(ge=0)
    prerequisites_met: bool
    high_level_hints_used: int = Field(default=0, ge=0)
    review_due: bool = False
    teacher_validated: bool = False
    recent_performance: float = Field(default=0, ge=0, le=1)


class ProgressionEvaluationResult(BaseModel):
    matched: bool
    action: ProgressionAction
    reason: str
    failed_conditions: list[str]
    requires_teacher_approval: bool
    approval_status: ApprovalStatus


class AccessibleVersionGenerateInput(BaseModel):
    source_resource_type: str = Field(min_length=2, max_length=60)
    source_resource_id: uuid.UUID
    title: str = Field(min_length=2, max_length=240)
    content: str = Field(min_length=2, max_length=100000)
    adaptation_type: AdaptationType
    learning_objective: str = Field(min_length=2, max_length=2000)
    expected_answer: str | None = Field(default=None, max_length=5000)
    assessment_criteria: list[str] = Field(default_factory=list, max_length=30)
    source_images_without_description: int = Field(default=0, ge=0)


class AccessibleVersionGenerateResult(BaseModel):
    title: str
    content: str
    adaptation_type: AdaptationType
    accessibility_metadata: dict[str, Any]
    pedagogical_snapshot: dict[str, Any]
    equivalence_status: EquivalenceStatus
    generation_method: GenerationMethod
    status: str
    warnings: list[str]


class AccessibleVersionRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    source_resource_type: str
    source_resource_id: uuid.UUID
    adaptation_type: str
    title: str
    content: str
    accessibility_metadata: dict[str, Any]
    pedagogical_snapshot: dict[str, Any]
    pedagogical_equivalence_status: str
    generation_method: str
    version: int
    status: str
    created_at: datetime
    updated_at: datetime


class SpacedReviewScheduleRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    status: str
    priority: int
    interval_days: int
    scheduled_for: date
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    mastery_score_at_schedule: float
    confidence_at_schedule: float
    rule_version: str
    created_at: datetime
    updated_at: datetime


class ReviewCompletionInput(BaseModel):
    result_score: float = Field(ge=0, le=1)
    mastery_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    hint_level_used: int = Field(default=0, ge=0, le=5)
    resource_id: uuid.UUID | None = None


class AdaptiveFeedbackRecordCreate(BaseModel):
    student_id: uuid.UUID
    attempt_id: uuid.UUID
    response_id: uuid.UUID | None = None
    learning_node_id: uuid.UUID | None = None
    adaptation: FeedbackAdaptInput


class AdaptiveFeedbackRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    student_id: uuid.UUID
    attempt_id: uuid.UUID
    response_id: uuid.UUID | None
    learning_node_id: uuid.UUID | None
    feedback_type: str
    error_type: str
    mastery_level: str
    content: str
    next_action: str
    rule_version: str
    generated_by: str
    review_status: str
    presented_at: datetime | None
    student_rating: int | None
    created_at: datetime


class StudentDifficultyProfileRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    difficulty_score: float
    difficulty_level: str
    confidence_score: float
    previous_score: float | None
    change_reason: str
    last_calculated_at: datetime
    calculation_version: str
    requires_review: bool
    created_at: datetime
    updated_at: datetime


class ResourceDifficultyMetricRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    learning_node_id: uuid.UUID | None
    predicted_difficulty: float
    observed_difficulty: float | None
    difficulty_difference: float | None
    difficulty_classification: str
    sample_size: int
    confidence_score: float
    metrics_snapshot: dict[str, Any]
    calculation_version: str
    last_calculated_at: datetime
    created_at: datetime
    updated_at: datetime


class ProgressionDecisionRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    student_id: uuid.UUID
    learning_path_id: uuid.UUID | None
    learning_node_id: uuid.UUID | None
    rule_id: uuid.UUID | None
    decision: str
    decision_reason: str
    input_snapshot: dict[str, Any]
    requires_teacher_approval: bool
    approval_status: str
    reviewed_by_user_id: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


class AccessibleVersionReviewInput(BaseModel):
    approved: bool
    pedagogical_equivalence_status: EquivalenceStatus
    review_notes: str = Field(min_length=2, max_length=5000)
