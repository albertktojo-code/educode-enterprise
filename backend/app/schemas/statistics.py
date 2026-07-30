from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.statistics import AnalysisStatus, DatasetStatus, ReportType, StudyStatus


class StudyCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    research_question: str = ""
    null_hypothesis: str = ""
    alternative_hypothesis: str = ""
    study_design: str = "pre_post"
    significance_level: float = Field(default=0.05, gt=0, lt=1)
    pedagogical_threshold: float | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class StudyRead(StudyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    status: StudyStatus
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class DatasetCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    assignment_ids: list[UUID] = Field(default_factory=list)
    classroom_ids: list[UUID] = Field(default_factory=list)
    attempt_policy: Literal["first", "latest", "best", "all"] = "first"
    anonymized: bool = True
    manual_rows: list[dict[str, Any]] = Field(default_factory=list)
    variable_dictionary: list[dict[str, Any]] = Field(default_factory=list)


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_id: UUID
    title: str
    status: DatasetStatus
    snapshot_at: datetime
    filters: dict[str, Any]
    attempt_policy: str
    participant_count: int
    row_count: int
    dataset_checksum: str
    quality_summary: dict[str, Any]
    variable_dictionary: list[dict[str, Any]]
    anonymized: bool
    created_at: datetime


class AnalysisCreate(BaseModel):
    dataset_id: UUID
    title: str = Field(min_length=3, max_length=240)
    analysis_type: Literal[
        "descriptive", "paired_t", "independent_t", "welch_t", "wilcoxon",
        "mann_whitney", "anova", "kruskal_wallis", "pearson", "spearman",
        "cronbach_alpha", "chi_square", "friedman", "mcnemar",
        "fisher_exact", "likert_summary"
    ]
    parameters: dict[str, Any] = Field(default_factory=dict)


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_id: UUID
    dataset_id: UUID
    title: str
    analysis_type: str
    parameters: dict[str, Any]
    assumptions: dict[str, Any]
    descriptive_results: dict[str, Any]
    test_results: dict[str, Any]
    effect_size: dict[str, Any]
    confidence_intervals: dict[str, Any]
    interpretation_teacher: str
    interpretation_researcher: str
    limitations: list[str]
    software_versions: dict[str, str]
    parent_analysis_id: UUID | None
    version_number: int
    configuration_checksum: str
    result_signature: str
    review_status: str
    status: AnalysisStatus
    executed_at: datetime | None
    created_at: datetime


class ChartCreate(BaseModel):
    chart_type: Literal["bar", "line", "scatter", "histogram", "boxplot", "paired"]
    title: str
    description: str = ""
    x_key: str | None = None
    y_key: str | None = None
    group_key: str | None = None
    include_in_report: bool = True


class ChartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    analysis_id: UUID
    chart_type: str
    title: str
    description: str
    configuration: dict[str, Any]
    data_snapshot: list[dict[str, Any]]
    alt_text: str
    display_order: int
    include_in_report: bool


class ReportCreate(BaseModel):
    report_type: ReportType = ReportType.STATISTICAL
    title: str
    include_charts: bool = True
    include_assumptions: bool = True
    include_limitations: bool = True


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    study_id: UUID
    analysis_id: UUID
    report_type: ReportType
    title: str
    content_html: str
    sections: list[dict[str, Any]]
    version_number: int
    review_status: str
    created_at: datetime


class TestRecommendationRequest(BaseModel):
    goal: Literal["pre_post", "two_groups", "three_groups", "association", "scale"]
    same_participants: bool = False
    variable_type: Literal["numeric", "ordinal", "categorical", "likert"] = "numeric"
    group_count: int = 1


class TestRecommendationRead(BaseModel):
    recommended_test: str
    alternative_test: str | None
    rationale: str
    required_columns: list[str]


class AnalysisVersionCreate(BaseModel):
    title: str | None = None
    parameters: dict[str, Any] | None = None
    change_summary: str = "Nova execução com parâmetros revisados."


class SensitivityRequest(BaseModel):
    scenario_keys: list[Literal[
        "complete_cases", "without_iqr_outliers", "winsorized_5", "alternative_method"
    ]] = Field(default_factory=lambda: ["complete_cases", "without_iqr_outliers"])
    alternative_analysis_type: str | None = None


class SensitivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    base_analysis_id: UUID
    dataset_id: UUID
    title: str
    scenario_key: str
    scenario_parameters: dict[str, Any]
    analysis_type: str
    result: dict[str, Any]
    conclusion_changed: bool
    created_at: datetime


class MethodComparisonRequest(BaseModel):
    methods: list[str] = Field(min_length=2, max_length=4)


class MethodComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    base_analysis_id: UUID
    dataset_id: UUID
    methods: list[str]
    results: dict[str, Any]
    recommendation: str
    conclusions_consistent: bool
    created_at: datetime


class SampleSizePlanCreate(BaseModel):
    study_id: UUID | None = None
    title: str = Field(min_length=3, max_length=240)
    design: Literal["paired", "independent", "correlation", "proportion"]
    significance_level: float = Field(default=0.05, gt=0, lt=1)
    power: float = Field(default=0.80, gt=0.5, lt=1)
    expected_effect_size: float = Field(gt=0)
    group_ratio: float = Field(default=1.0, gt=0)
    parameters: dict[str, Any] = Field(default_factory=dict)


class SampleSizePlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organization_id: UUID
    study_id: UUID | None
    title: str
    design: str
    significance_level: float
    power: float
    expected_effect_size: float
    group_ratio: float
    parameters: dict[str, Any]
    result: dict[str, Any]
    created_at: datetime


class ReviewCommentCreate(BaseModel):
    entity_type: Literal["analysis", "report"]
    entity_id: UUID
    section_key: str | None = Field(default=None, max_length=120)
    body: str = Field(min_length=3, max_length=4000)


class ReviewCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    entity_type: str
    entity_id: UUID
    section_key: str | None
    body: str
    status: str
    created_by_user_id: UUID
    resolved_by_user_id: UUID | None
    created_at: datetime
    resolved_at: datetime | None


class ReportRevisionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    content_html: str | None = None
    sections: list[dict[str, Any]] | None = None
    change_summary: str = Field(min_length=3, max_length=1000)


class ReportRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    report_id: UUID
    version_number: int
    content_html: str
    sections: list[dict[str, Any]]
    change_summary: str
    created_by_user_id: UUID
    created_at: datetime


class ReviewStatusUpdate(BaseModel):
    status: Literal["draft", "in_review", "reviewed", "approved", "archived"]


class ScriptExportRead(BaseModel):
    language: Literal["python", "r"]
    filename: str
    dataset_checksum: str
    content: str


class PValueAdjustmentRequest(BaseModel):
    p_values: list[float] = Field(min_length=1, max_length=500)
    method: Literal["holm", "bonferroni", "benjamini_hochberg"] = "holm"


class PValueAdjustmentRead(BaseModel):
    method: str
    original_p_values: list[float]
    adjusted_p_values: list[float]
