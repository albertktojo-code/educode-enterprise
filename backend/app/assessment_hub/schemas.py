from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import AttemptStatus, InstrumentType, QuestionType, RecordStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=220)
    subject: str = Field(min_length=2, max_length=100)
    school_year: str | None = Field(default=None, max_length=60)
    source_type: str = Field(default="INTERNAL", max_length=40)


class QuestionRead(ORMModel):
    id: uuid.UUID
    code: str
    title: str
    subject: str
    school_year: str | None
    source_type: str
    status: str
    current_version: int
    created_at: datetime


class QuestionVersionCreate(BaseModel):
    question_type: QuestionType
    statement: str = Field(min_length=3)
    options: list[dict[str, Any]] = Field(default_factory=list)
    correct_answer: dict[str, Any] = Field(default_factory=dict)
    explanation: str | None = None
    rubric: dict[str, Any] = Field(default_factory=dict)
    predicted_difficulty: float = Field(default=0.5, ge=0, le=1)
    max_score: float = Field(default=1.0, gt=0, le=1000)
    accessibility: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_options(self) -> "QuestionVersionCreate":
        if self.question_type in {QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE} and len(self.options) < 2:
            raise ValueError("Questoes de escolha exigem pelo menos duas opcoes.")
        if self.question_type in {QuestionType.ESSAY, QuestionType.PROJECT} and not self.rubric:
            raise ValueError("Questoes discursivas ou de projeto exigem rubrica.")
        return self


class QuestionVersionRead(ORMModel):
    id: uuid.UUID
    question_id: uuid.UUID
    version: int
    question_type: str
    statement: str
    options: list[dict[str, Any]]
    correct_answer: dict[str, Any]
    explanation: str | None
    rubric: dict[str, Any]
    predicted_difficulty: float
    max_score: float
    accessibility: dict[str, Any]
    status: str
    created_at: datetime


class SkillLinkCreate(BaseModel):
    skill_type: str = Field(min_length=2, max_length=40)
    skill_code: str = Field(min_length=1, max_length=80)
    skill_name: str = Field(min_length=2, max_length=220)
    weight: float = Field(default=1.0, gt=0, le=10)
    is_primary: bool = False


class SkillLinkRead(ORMModel):
    id: uuid.UUID
    question_version_id: uuid.UUID
    skill_type: str
    skill_code: str
    skill_name: str
    weight: float
    is_primary: bool


class BlueprintCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=3, max_length=220)
    assessment_type: str = Field(min_length=2, max_length=50)
    description: str = Field(min_length=3)
    selection_rules: dict[str, Any] = Field(default_factory=dict)
    delivery_settings: dict[str, Any] = Field(default_factory=dict)
    scoring_settings: dict[str, Any] = Field(default_factory=dict)


class BlueprintRead(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    version: int
    assessment_type: str
    description: str
    selection_rules: dict[str, Any]
    delivery_settings: dict[str, Any]
    scoring_settings: dict[str, Any]
    status: str


class CandidateQuestion(BaseModel):
    question_version_id: uuid.UUID
    question_type: QuestionType
    difficulty: float = Field(ge=0, le=1)
    skill_codes: list[str] = Field(default_factory=list)
    max_score: float = Field(default=1.0, gt=0)


class AssemblySimulationInput(BaseModel):
    target_count: int = Field(ge=1, le=200)
    target_average_difficulty: float = Field(default=0.5, ge=0, le=1)
    required_skill_codes: list[str] = Field(default_factory=list)
    allowed_question_types: list[QuestionType] = Field(default_factory=list)
    seed: int = 15
    candidates: list[CandidateQuestion] = Field(min_length=1)


class AssemblySimulationResult(BaseModel):
    selected_question_ids: list[uuid.UUID]
    selected_count: int
    average_difficulty: float
    covered_skill_codes: list[str]
    missing_skill_codes: list[str]
    total_score: float
    deterministic_seed: int
    warnings: list[str]


class ExternalInstrumentCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=3, max_length=240)
    version: str = Field(min_length=1, max_length=60)
    instrument_type: InstrumentType
    authorship: str | None = None
    description: str = Field(min_length=3)
    source_reference: str | None = None
    license_status: str = Field(default="REQUIRES_PERMISSION", max_length=60)
    permission_reference: str | None = None
    administration_rules: dict[str, Any] = Field(default_factory=dict)
    scoring_rules: dict[str, Any] = Field(default_factory=dict)
    interpretation_rules: dict[str, Any] = Field(default_factory=dict)


class ExternalInstrumentRead(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    version: str
    instrument_type: str
    authorship: str | None
    description: str
    license_status: str
    status: str


class InstrumentDimensionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=2, max_length=220)
    description: str = Field(min_length=3)
    weight: float = Field(default=1.0, gt=0, le=100)
    minimum_score: float | None = None
    maximum_score: float | None = None
    interpretation: dict[str, Any] = Field(default_factory=dict)


class InstrumentDimensionRead(ORMModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    code: str
    name: str
    description: str
    weight: float
    minimum_score: float | None
    maximum_score: float | None
    interpretation: dict[str, Any]


class AttemptCreate(BaseModel):
    student_id: uuid.UUID
    classroom_id: uuid.UUID | None = None
    blueprint_id: uuid.UUID | None = None
    external_instrument_id: uuid.UUID | None = None
    attempt_number: int = Field(default=1, ge=1)
    question_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self) -> "AttemptCreate":
        if not self.blueprint_id and not self.external_instrument_id:
            raise ValueError("A tentativa deve estar vinculada a uma avaliacao ou instrumento externo.")
        return self


class AttemptRead(ORMModel):
    id: uuid.UUID
    student_id: uuid.UUID
    classroom_id: uuid.UUID | None
    blueprint_id: uuid.UUID | None
    external_instrument_id: uuid.UUID | None
    attempt_number: int
    status: str
    total_score: float | None
    maximum_score: float | None
    percentage_score: float | None
    requires_human_review: bool
    created_at: datetime


class ScoreRequest(BaseModel):
    question_type: QuestionType
    correct_answer: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    max_score: float = Field(default=1.0, gt=0)


class ScoreResult(BaseModel):
    score: float | None
    max_score: float
    is_correct: bool | None
    requires_human_review: bool
    correction_type: str
    explanation: str


class ResponseCreate(BaseModel):
    question_version_id: uuid.UUID
    response: dict[str, Any] = Field(default_factory=dict)


class ResponseRead(ORMModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    question_version_id: uuid.UUID
    response_payload: dict[str, Any]
    score: float | None
    maximum_score: float
    is_correct: bool | None
    correction_type: str | None
    feedback: str | None
    requires_human_review: bool


class ReviewCreate(BaseModel):
    proposed_score: float = Field(ge=0)
    justification: str = Field(min_length=3)
    feedback: str | None = None


class ItemObservation(BaseModel):
    correct: bool
    score_ratio: float = Field(ge=0, le=1)
    attempts: int = Field(default=1, ge=1)
    hints: int = Field(default=0, ge=0)
    duration_seconds: float = Field(default=0, ge=0)


class ItemAnalyticsInput(BaseModel):
    predicted_difficulty: float = Field(ge=0, le=1)
    observations: list[ItemObservation] = Field(min_length=1)


class ItemAnalyticsResult(BaseModel):
    sample_size: int
    accuracy_rate: float
    average_score_ratio: float
    observed_difficulty: float
    predicted_difficulty: float
    difficulty_difference: float
    classification: str
    average_attempts: float
    average_hints: float
    average_duration_seconds: float
    confidence: float


class DimensionScoreInput(BaseModel):
    dimension_code: str
    earned_score: float
    maximum_score: float = Field(gt=0)
    weight: float = Field(default=1.0, gt=0)


class DimensionSummaryInput(BaseModel):
    dimensions: list[DimensionScoreInput] = Field(min_length=1)


class DimensionSummaryResult(BaseModel):
    weighted_percentage: float
    dimension_scores: dict[str, dict[str, float]]
    scoring_version: str
