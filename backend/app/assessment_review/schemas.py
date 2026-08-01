from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    AppealStatus,
    CorrectionSource,
    FeedbackAudience,
    FeedbackStatus,
    RegradeStatus,
    ReviewAssignmentStatus,
    ReviewMode,
    RubricStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RubricCriterion(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=220)
    description: str | None = None
    criterion_type: str = Field(default="SCALE", max_length=30)
    maximum_score: float = Field(gt=0, le=10000)
    levels: list[dict[str, Any]] = Field(default_factory=list)
    skill_mappings: list[dict[str, Any]] = Field(default_factory=list)


class RubricCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=220)
    description: str = Field(min_length=3)
    scope_type: str = Field(default="QUESTION", min_length=2, max_length=40)
    scope_id: uuid.UUID | None = None


class RubricRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str
    scope_type: str
    scope_id: uuid.UUID | None
    status: RubricStatus
    current_version: int
    created_at: datetime


class RubricVersionCreate(BaseModel):
    maximum_score: float = Field(gt=0, le=10000)
    criteria: list[RubricCriterion] = Field(min_length=1)
    score_rules: dict[str, Any] = Field(default_factory=dict)
    feedback_templates: dict[str, Any] = Field(default_factory=dict)
    skill_mappings: list[dict[str, Any]] = Field(default_factory=list)
    accessibility_settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_total(self) -> "RubricVersionCreate":
        total = sum(item.maximum_score for item in self.criteria)
        if abs(total - self.maximum_score) > 0.0001:
            raise ValueError("A soma dos criterios deve ser igual a maximum_score")
        codes = [item.code for item in self.criteria]
        if len(codes) != len(set(codes)):
            raise ValueError("Os codigos dos criterios devem ser unicos")
        return self


class RubricVersionRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    rubric_id: uuid.UUID
    version: int
    status: RubricStatus
    maximum_score: float
    criteria: list[dict[str, Any]]
    score_rules: dict[str, Any]
    feedback_templates: dict[str, Any]
    skill_mappings: list[dict[str, Any]]
    configuration_hash: str
    created_at: datetime


class RubricSimulationRequest(BaseModel):
    criteria: list[RubricCriterion]
    awarded_scores: dict[str, float]


class RubricSimulationResult(BaseModel):
    total_score: float
    maximum_score: float
    percentage: float
    breakdown: list[dict[str, Any]]


class AssignmentCreate(BaseModel):
    attempt_id: uuid.UUID
    response_id: uuid.UUID
    question_version_id: uuid.UUID
    rubric_version_id: uuid.UUID | None = None
    reviewer_user_id: uuid.UUID
    review_round: int = Field(default=1, ge=1, le=20)
    review_mode: ReviewMode = ReviewMode.SINGLE
    priority: int = Field(default=50, ge=0, le=100)
    due_at: datetime | None = None
    blinded: bool = False
    context_snapshot: dict[str, Any] = Field(default_factory=dict)


class AssignmentRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    attempt_id: uuid.UUID
    response_id: uuid.UUID
    question_version_id: uuid.UUID
    rubric_version_id: uuid.UUID | None
    reviewer_user_id: uuid.UUID
    review_round: int
    review_mode: ReviewMode
    status: ReviewAssignmentStatus
    priority: int
    due_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    blinded: bool
    context_snapshot: dict[str, Any]
    created_at: datetime


class CriterionScoreInput(BaseModel):
    criterion_code: str = Field(min_length=1, max_length=80)
    criterion_name: str = Field(min_length=2, max_length=220)
    awarded_score: float = Field(ge=0)
    maximum_score: float = Field(gt=0)
    level_code: str | None = Field(default=None, max_length=80)
    evidence: str | None = None
    comment: str | None = None
    skill_scores: dict[str, Any] = Field(default_factory=dict)
    correction_source: CorrectionSource = CorrectionSource.HUMAN

    @model_validator(mode="after")
    def validate_score(self) -> "CriterionScoreInput":
        if self.awarded_score > self.maximum_score:
            raise ValueError("awarded_score nao pode exceder maximum_score")
        return self


class ScoreSubmission(BaseModel):
    scores: list[CriterionScoreInput] = Field(min_length=1)
    completion_comment: str | None = None
    finalize: bool = False


class CriterionScoreRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    assignment_id: uuid.UUID
    criterion_code: str
    criterion_name: str
    awarded_score: float
    maximum_score: float
    level_code: str | None
    evidence: str | None
    comment: str | None
    skill_scores: dict[str, Any]
    correction_source: CorrectionSource
    reviewer_user_id: uuid.UUID


class FeedbackCreate(BaseModel):
    assignment_id: uuid.UUID | None = None
    attempt_id: uuid.UUID
    response_id: uuid.UUID | None = None
    student_id: uuid.UUID
    audience: FeedbackAudience = FeedbackAudience.STUDENT
    feedback_type: str = Field(default="FORMATIVE", max_length=50)
    summary: str = Field(min_length=3)
    strengths: list[str] = Field(default_factory=list)
    improvement_points: list[str] = Field(default_factory=list)
    next_steps: list[dict[str, Any]] = Field(default_factory=list)
    question_feedback: list[dict[str, Any]] = Field(default_factory=list)
    skill_feedback: list[dict[str, Any]] = Field(default_factory=list)
    accessible_variants: dict[str, Any] = Field(default_factory=dict)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)


class FeedbackRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    assignment_id: uuid.UUID | None
    attempt_id: uuid.UUID
    response_id: uuid.UUID | None
    student_id: uuid.UUID
    audience: FeedbackAudience
    status: FeedbackStatus
    feedback_type: str
    summary: str
    strengths: list[str]
    improvement_points: list[str]
    next_steps: list[dict[str, Any]]
    question_feedback: list[dict[str, Any]]
    skill_feedback: list[dict[str, Any]]
    accessible_variants: dict[str, Any]
    content_hash: str
    published_at: datetime | None
    created_at: datetime


class AppealCreate(BaseModel):
    attempt_id: uuid.UUID
    response_id: uuid.UUID | None = None
    student_id: uuid.UUID
    reason_code: str = Field(min_length=2, max_length=50)
    statement: str = Field(min_length=10)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class AppealDecision(BaseModel):
    decision: str = Field(pattern=r"^(ACCEPTED|PARTIALLY_ACCEPTED|REJECTED)$")
    justification: str = Field(min_length=5)
    final_score: float | None = Field(default=None, ge=0)


class AppealRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    attempt_id: uuid.UUID
    response_id: uuid.UUID | None
    student_id: uuid.UUID
    reason_code: str
    statement: str
    attachments: list[dict[str, Any]]
    status: AppealStatus
    assigned_reviewer_user_id: uuid.UUID | None
    decision: str | None
    decision_justification: str | None
    decided_at: datetime | None
    created_at: datetime


class RegradeCreate(BaseModel):
    appeal_id: uuid.UUID | None = None
    attempt_id: uuid.UUID
    response_id: uuid.UUID
    proposed_score: float = Field(ge=0)
    maximum_score: float = Field(gt=0)
    reason: str = Field(min_length=5)

    @model_validator(mode="after")
    def validate_score(self) -> "RegradeCreate":
        if self.proposed_score > self.maximum_score:
            raise ValueError("proposed_score nao pode exceder maximum_score")
        return self


class RegradeDecision(BaseModel):
    apply: bool
    final_score: float | None = Field(default=None, ge=0)
    justification: str = Field(min_length=5)


class RegradeRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    appeal_id: uuid.UUID | None
    attempt_id: uuid.UUID
    response_id: uuid.UUID
    previous_score: float | None
    proposed_score: float
    final_score: float | None
    maximum_score: float
    reason: str
    status: RegradeStatus
    applied_at: datetime | None
    created_at: datetime


class ReviewRequirementRequest(BaseModel):
    question_type: str
    automatic_confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_threshold: float = Field(default=0.85, ge=0, le=1)
    score_difference: float | None = None
    discrepancy_threshold: float = Field(default=0.2, ge=0)
    explicitly_requested: bool = False


class ReviewRequirementResult(BaseModel):
    requires_human_review: bool
    reasons: list[str]


class ReviewSummary(BaseModel):
    attempt_id: uuid.UUID
    assignments_total: int
    assignments_completed: int
    pending_appeals: int
    applied_regrades: int
    feedback_published: int
    requires_attention: bool
