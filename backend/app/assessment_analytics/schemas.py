from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import AnalyticsModelStatus, AnalyticsRunStatus, ExportStatus, MetricScope, ReportStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AnalyticsModelCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=3, max_length=220)
    description: str = Field(min_length=5)
    version: int = Field(default=1, ge=1)
    configuration: dict[str, Any] = Field(default_factory=dict)
    privacy_rules: dict[str, Any] = Field(default_factory=lambda: {"minimum_group_size": 5})
    metric_definitions: list[dict[str, Any]] = Field(default_factory=list)
    is_default: bool = False


class AnalyticsModelRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    version: int
    status: AnalyticsModelStatus
    description: str
    configuration: dict[str, Any]
    privacy_rules: dict[str, Any]
    metric_definitions: list[dict[str, Any]]
    configuration_hash: str
    is_default: bool
    created_at: datetime


class AnalyticsRunCreate(BaseModel):
    analytics_model_id: uuid.UUID
    scope_type: MetricScope
    scope_id: uuid.UUID | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    filters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_period(self) -> "AnalyticsRunCreate":
        if self.period_start and self.period_end and self.period_end < self.period_start:
            raise ValueError("period_end deve ser posterior a period_start")
        return self


class AnalyticsRunRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    analytics_model_id: uuid.UUID
    scope_type: MetricScope
    scope_id: uuid.UUID | None
    status: AnalyticsRunStatus
    period_start: datetime | None
    period_end: datetime | None
    filters: dict[str, Any]
    output_summary: dict[str, Any]
    records_processed: int
    created_at: datetime


class ItemAnalysisRequest(BaseModel):
    predicted_difficulty: float | None = Field(default=None, ge=0, le=1)
    item_scores: list[int] = Field(min_length=1)
    total_scores: list[float] = Field(min_length=1)
    omitted: int = Field(default=0, ge=0)
    upper_correct: int = Field(default=0, ge=0)
    upper_total: int = Field(default=0, ge=0)
    lower_correct: int = Field(default=0, ge=0)
    lower_total: int = Field(default=0, ge=0)
    minimum_sample: int = Field(default=20, ge=2)

    @model_validator(mode="after")
    def validate_vectors(self) -> "ItemAnalysisRequest":
        if len(self.item_scores) != len(self.total_scores):
            raise ValueError("item_scores e total_scores devem ter o mesmo tamanho")
        if any(item not in (0, 1) for item in self.item_scores):
            raise ValueError("item_scores devem conter apenas 0 ou 1")
        if self.omitted > len(self.item_scores):
            raise ValueError("omitted nao pode exceder a amostra")
        return self


class ItemAnalysisResult(BaseModel):
    sample_size: int
    facility_index: float | None
    observed_difficulty: float | None
    difficulty_delta: float | None
    discrimination_index: float | None
    point_biserial: float | None
    omission_rate: float
    flags: list[str]


class DistractorAnalysisRequest(BaseModel):
    selections: list[str | None] = Field(min_length=1)
    correct_option: str = Field(min_length=1, max_length=80)
    minimum_functioning_rate: float = Field(default=0.05, ge=0, le=1)


class ReliabilityRequest(BaseModel):
    score_matrix: list[list[float]] = Field(min_length=2)


class PrivacyCheckRequest(BaseModel):
    sample_size: int = Field(ge=0)
    minimum_group_size: int = Field(default=5, ge=2)


class ReportDefinitionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=3, max_length=220)
    description: str = Field(min_length=5)
    audience: str = Field(default="TEACHER", max_length=30)
    sections: list[dict[str, Any]] = Field(min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    privacy_rules: dict[str, Any] = Field(default_factory=lambda: {"minimum_group_size": 5})


class ReportDefinitionRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str
    status: ReportStatus
    audience: str
    sections: list[dict[str, Any]]
    filters: dict[str, Any]
    privacy_rules: dict[str, Any]
    created_at: datetime


class ReportExportCreate(BaseModel):
    report_definition_id: uuid.UUID
    analytics_run_id: uuid.UUID | None = None
    format: str = Field(default="CSV", pattern=r"^(CSV|JSON|XLSX|PDF)$")
    parameters: dict[str, Any] = Field(default_factory=dict)


class ReportExportRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    report_definition_id: uuid.UUID
    analytics_run_id: uuid.UUID | None
    status: ExportStatus
    format: str
    parameters: dict[str, Any]
    storage_reference: str | None
    checksum: str | None
    row_count: int | None
    created_at: datetime
