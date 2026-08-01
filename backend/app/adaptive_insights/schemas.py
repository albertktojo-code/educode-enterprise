from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    AssignmentStrategy,
    ExperimentStatus,
    InterventionOutcome,
    MetricDirection,
    ModelScope,
    RecommendationAction,
    RecordStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)




class InterventionOutcomeCreate(BaseModel):
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    intervention_type: str = Field(min_length=2, max_length=80)
    material_id: uuid.UUID | None = None
    mastery_before: float = Field(ge=0, le=1)
    mastery_after: float = Field(ge=0, le=1)
    completion_rate: float = Field(ge=0, le=1, default=1)
    hints_average: float = Field(ge=0, le=5, default=0)
    attempts_average: float = Field(ge=0, default=1)
    occurred_at: datetime
    source_snapshot: dict[str, Any] = Field(default_factory=dict)


class InterventionOutcomeRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    intervention_type: str
    material_id: uuid.UUID | None
    mastery_before: float
    mastery_after: float
    mastery_gain: float
    completion_rate: float
    hints_average: float
    attempts_average: float
    outcome: str
    occurred_at: datetime
    source_snapshot: dict[str, Any]
    created_at: datetime


class MaterialEffectivenessMetricRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    sample_size: int
    completion_rate: float
    accuracy_rate: float | None
    average_gain: float | None
    median_gain: float | None
    average_attempts: float
    average_hints: float
    average_duration_seconds: float
    confidence_score: float
    classification: str
    calculation_version: str
    calculated_at: datetime


class InterventionHistoryItem(BaseModel):
    intervention_type: str = Field(min_length=2, max_length=80)
    material_id: uuid.UUID | None = None
    mastery_before: float = Field(ge=0, le=1)
    mastery_after: float = Field(ge=0, le=1)
    completion_rate: float = Field(ge=0, le=1, default=1)
    hint_level_average: float = Field(ge=0, le=5, default=0)
    attempts_average: float = Field(ge=0, default=1)
    days_ago: int = Field(ge=0, default=0)


class InterventionRecommendationInput(BaseModel):
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    current_mastery: float = Field(ge=0, le=1)
    current_confidence: float = Field(ge=0, le=1)
    history: list[InterventionHistoryItem] = Field(default_factory=list, max_length=100)
    candidate_interventions: list[str] = Field(min_length=1, max_length=20)


class RecommendationCandidate(BaseModel):
    intervention_type: str
    score: float = Field(ge=0, le=1)
    historical_uses: int = Field(ge=0)
    average_gain: float
    rationale: list[str]


class InterventionRecommendationResult(BaseModel):
    action: RecommendationAction
    recommended_intervention: str | None
    confidence: float = Field(ge=0, le=1)
    candidates: list[RecommendationCandidate]
    requires_teacher_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    model_version: str = "intervention-history-v1"


class MaterialObservation(BaseModel):
    student_id: uuid.UUID | None = None
    completed: bool
    score_before: float | None = Field(default=None, ge=0, le=1)
    score_after: float | None = Field(default=None, ge=0, le=1)
    correct: bool | None = None
    attempts: int = Field(default=1, ge=0)
    hints_used: int = Field(default=0, ge=0)
    duration_seconds: int = Field(default=0, ge=0)


class MaterialEffectivenessInput(BaseModel):
    resource_type: str = Field(min_length=2, max_length=60)
    resource_id: uuid.UUID
    observations: list[MaterialObservation] = Field(min_length=1, max_length=10000)


class MaterialEffectivenessResult(BaseModel):
    sample_size: int
    completion_rate: float
    accuracy_rate: float | None
    average_gain: float | None
    median_gain: float | None
    average_attempts: float
    average_hints: float
    average_duration_seconds: float
    confidence: float
    classification: str
    warnings: list[str]
    calculation_version: str = "descriptive-effectiveness-v1"


class AdaptiveModelCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
    description: str = Field(min_length=5, max_length=2000)
    scope_type: ModelScope = ModelScope.ORGANIZATION
    scope_id: uuid.UUID | None = None
    algorithm_type: str = Field(default="DETERMINISTIC_RULES", max_length=80)
    configuration: dict[str, Any]
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = RecordStatus.DRAFT


class AdaptiveModelRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    version: str
    description: str
    scope_type: str
    scope_id: uuid.UUID | None
    algorithm_type: str
    configuration: dict[str, Any]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    configuration_hash: str
    status: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SimulationProfile(BaseModel):
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    mastery_score: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    evidences_count: int = Field(ge=0)
    intervention_failures: int = Field(ge=0, default=0)
    overdue_reviews: int = Field(ge=0, default=0)


class RecommendationSimulationInput(BaseModel):
    model_id: uuid.UUID | None = None
    model_configuration: dict[str, Any] | None = None
    profiles: list[SimulationProfile] = Field(min_length=1, max_length=5000)
    persist_result: bool = False

    @model_validator(mode="after")
    def validate_model_source(self) -> "RecommendationSimulationInput":
        if self.model_id is None and self.model_configuration is None:
            raise ValueError("Informe model_id ou model_configuration.")
        return self


class SimulatedDecision(BaseModel):
    student_id: uuid.UUID
    learning_node_id: uuid.UUID
    action: RecommendationAction
    reason: str
    score: float


class RecommendationSimulationResult(BaseModel):
    profiles_count: int
    decisions: list[SimulatedDecision]
    action_distribution: dict[str, int]
    warnings: list[str]
    is_simulation: bool = True


class ExperimentStrategy(BaseModel):
    key: str = Field(pattern=r"^[A-Z0-9_-]{1,30}$")
    name: str = Field(min_length=2, max_length=120)
    model_id: uuid.UUID | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class ControlledExperimentCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=5, max_length=2000)
    hypothesis: str = Field(min_length=5, max_length=2000)
    primary_metric: str = Field(min_length=2, max_length=80)
    metric_direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER
    assignment_strategy: AssignmentStrategy = AssignmentStrategy.DETERMINISTIC_HASH
    strategies: list[ExperimentStrategy] = Field(min_length=2, max_length=6)
    minimum_sample_per_strategy: int = Field(default=20, ge=2, le=100000)
    status: ExperimentStatus = ExperimentStatus.DRAFT

    @model_validator(mode="after")
    def unique_strategy_keys(self) -> "ControlledExperimentCreate":
        keys = [item.key for item in self.strategies]
        if len(keys) != len(set(keys)):
            raise ValueError("As chaves das estratégias devem ser únicas.")
        return self


class ControlledExperimentRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str
    hypothesis: str
    primary_metric: str
    metric_direction: str
    assignment_strategy: str
    strategies: list[dict[str, Any]]
    minimum_sample_per_strategy: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExperimentAssignmentInput(BaseModel):
    participant_id: uuid.UUID


class ExperimentAssignmentResult(BaseModel):
    experiment_id: uuid.UUID
    participant_id: uuid.UUID
    strategy_key: str
    assignment_strategy: AssignmentStrategy


class ExperimentObservationCreate(BaseModel):
    participant_id: uuid.UUID
    strategy_key: str = Field(pattern=r"^[A-Z0-9_-]{1,30}$")
    metric_value: float
    completed: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyComparison(BaseModel):
    strategy_key: str
    sample_size: int
    mean: float | None
    median: float | None
    minimum: float | None
    maximum: float | None
    completion_rate: float


class ExperimentComparisonResult(BaseModel):
    experiment_id: uuid.UUID
    primary_metric: str
    metric_direction: MetricDirection
    strategies: list[StrategyComparison]
    leading_strategy: str | None
    sufficient_sample: bool
    warnings: list[str]
    analysis_type: str = "DESCRIPTIVE_CONTROLLED_COMPARISON"


class InstitutionalPathSnapshot(BaseModel):
    path_id: uuid.UUID
    path_name: str
    assigned_students: int = Field(ge=0)
    active_students: int = Field(ge=0)
    completed_students: int = Field(ge=0)
    average_progress: float = Field(ge=0, le=1)
    overdue_reviews: int = Field(ge=0)
    interventions_count: int = Field(ge=0)
    average_mastery: float = Field(ge=0, le=1)


class InstitutionalPathDashboardInput(BaseModel):
    paths: list[InstitutionalPathSnapshot] = Field(default_factory=list, max_length=10000)


class InstitutionalPathDashboardResult(BaseModel):
    paths_count: int
    assigned_students: int
    active_students: int
    completed_students: int
    completion_rate: float
    average_progress: float
    average_mastery: float
    overdue_reviews: int
    interventions_count: int
    attention_paths: list[uuid.UUID]
