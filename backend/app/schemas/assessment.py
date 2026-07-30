from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.assessment import AssessmentSourceType, AssessmentStatus, QuestionBankStatus
from app.models.delivery import AssignmentType, QuestionType, RecipientType


class BankItemCreate(BaseModel):
    title: str = Field(default="", max_length=240)
    item_type: QuestionType
    prompt: str = Field(min_length=3, max_length=10000)
    options: list[dict[str, Any]] = Field(default_factory=list)
    answer_key: dict[str, Any] = Field(default_factory=dict)
    explanation: str = Field(default="", max_length=10000)
    points: float = Field(default=1.0, gt=0, le=1000)
    difficulty: str = Field(default="medium", max_length=40)
    curriculum_skill_codes: list[str] = Field(default_factory=list)
    ct_pillar_codes: list[str] = Field(default_factory=list)
    source_type: AssessmentSourceType = AssessmentSourceType.TEACHER
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    ai_generation_metadata: dict[str, Any] = Field(default_factory=dict)
    requires_manual_grading: bool = False
    external_reference: str | None = Field(default=None, max_length=240)


class BankItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: str
    item_type: str
    prompt: str
    options: list[dict[str, Any]]
    answer_key: dict[str, Any]
    explanation: str
    points: float
    difficulty: str
    curriculum_skill_codes: list[str]
    ct_pillar_codes: list[str]
    source_type: str
    source_metadata: dict[str, Any]
    ai_generation_metadata: dict[str, Any]
    requires_manual_grading: bool
    status: str
    version_number: int
    content_checksum: str
    external_reference: str | None
    created_by_user_id: UUID
    reviewed_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=10000)
    assessment_type: AssignmentType = AssignmentType.ASSESSMENT
    source_type: AssessmentSourceType = AssessmentSourceType.TEACHER
    instructions: str = Field(default="", max_length=10000)
    scoring_policy: dict[str, Any] = Field(default_factory=lambda: {"mode": "points", "maximum_score": 10})
    delivery_defaults: dict[str, Any] = Field(default_factory=dict)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    item_ids: list[UUID] = Field(default_factory=list)


class AssessmentVersionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_version_id: UUID
    question_bank_item_id: UUID
    position: int
    points_override: float | None
    item_snapshot: dict[str, Any]
    snapshot_checksum: str
    bank_item: BankItemRead


class AssessmentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    organization_id: UUID
    version_number: int
    instructions: str
    scoring_policy: dict[str, Any]
    delivery_defaults: dict[str, Any]
    source_metadata: dict[str, Any]
    content_checksum: str
    is_locked: bool
    published_at: datetime | None
    created_by_user_id: UUID
    created_at: datetime
    items: list[AssessmentVersionItemRead]


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: str
    description: str
    assessment_type: str
    source_type: str
    status: str
    current_version_number: int
    created_by_user_id: UUID
    reviewed_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    versions: list[AssessmentVersionRead] = Field(default_factory=list)


class AssessmentItemAdd(BaseModel):
    item_id: UUID
    position: int | None = Field(default=None, ge=1)
    points_override: float | None = Field(default=None, gt=0, le=1000)


class AssessmentReviewRequest(BaseModel):
    decision: str = Field(pattern="^(submit|approve|return|archive)$")
    notes: str = Field(default="", max_length=4000)


class RecipientPublishInput(BaseModel):
    recipient_type: RecipientType
    classroom_id: UUID | None = None
    user_id: UUID | None = None
    accommodations: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self) -> "RecipientPublishInput":
        if self.recipient_type == RecipientType.CLASSROOM and self.classroom_id is None:
            raise ValueError("classroom_id é obrigatório")
        if self.recipient_type == RecipientType.USER and self.user_id is None:
            raise ValueError("user_id é obrigatório")
        return self


class AssessmentPublishRequest(BaseModel):
    version_id: UUID
    recipients: list[RecipientPublishInput] = Field(min_length=1)
    title_override: str | None = Field(default=None, max_length=240)
    available_from: datetime | None = None
    due_at: datetime | None = None
    time_limit_minutes: int | None = Field(default=None, ge=1, le=1440)
    maximum_attempts: int = Field(default=1, ge=1, le=20)
    maximum_score: float = Field(default=10.0, gt=0, le=1000)
    feedback_policy: str = "after_submission"
    answer_key_policy: str = "after_due_date"
    randomize_questions: bool = False
    randomize_options: bool = False


class AiQuestionGenerationRequest(BaseModel):
    assessment_id: UUID
    quantity: int = Field(default=5, ge=1, le=30)
    topic: str = Field(min_length=2, max_length=240)
    difficulty: str = Field(default="medium", max_length=40)
    curriculum_skill_codes: list[str] = Field(default_factory=list)
    ct_pillar_codes: list[str] = Field(default_factory=list)
    source_context: dict[str, Any] = Field(default_factory=dict)


class ImportJobCreate(BaseModel):
    source_format: str = Field(pattern="^(csv|xlsx|json|qti|lti|xapi|scorm)$")
    file_name: str = Field(default="", max_length=255)
    field_mapping: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    source_format: str
    file_name: str
    status: str
    field_mapping: dict[str, Any]
    rows_snapshot: list[dict[str, Any]]
    validation_summary: dict[str, Any]
    imported_assessment_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime
    completed_at: datetime | None


class ImportExecuteRequest(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=5000)
    assessment_type: AssignmentType = AssignmentType.ASSESSMENT


class OutcomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_version_id: UUID | None
    assignment_id: UUID
    attempt_id: UUID
    answer_id: UUID
    question_id: UUID
    student_id: UUID
    dimension_type: str
    dimension_code: str
    score_obtained: float
    score_possible: float
    evidence_weight: float
    calculation_version: int
    source_snapshot: dict[str, Any]
    calculated_at: datetime


class RecalculateRequest(BaseModel):
    reason: str = Field(default="recalculation", max_length=500)


class QuestionAnnulmentRequest(BaseModel):
    is_annulled: bool = True
    reason: str = Field(min_length=3, max_length=2000)
    regrade_attempts: bool = True


class StatisticalDatasetFromAssessments(BaseModel):
    study_id: UUID
    title: str = Field(min_length=3, max_length=240)
    assessment_version_ids: list[UUID] = Field(min_length=1)
    attempt_policy: str = Field(default="first", pattern="^(first|latest|best|all)$")
    anonymized: bool = True
    include_item_level: bool = True


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    assessment_id: UUID | None
    assessment_version_id: UUID | None
    assignment_id: UUID | None
    action: str
    details: dict[str, Any]
    performed_by_user_id: UUID
    created_at: datetime
