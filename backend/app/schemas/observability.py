from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SLOWrite(BaseModel):
    slo_key: str = Field(pattern=r"^[a-z0-9_.-]+$", min_length=2, max_length=120)
    name: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=10000)
    metric_name: str = Field(min_length=2, max_length=160)
    comparator: Literal[">", ">=", "<", "<=", "=="] = ">="
    target_value: float
    window_minutes: int = Field(default=60, ge=1, le=43200)
    minimum_samples: int = Field(default=1, ge=1, le=1000000)
    severity: Literal["info", "warning", "critical"] = "warning"
    is_active: bool = True


class SLORead(ORMModel):
    id: UUID
    organization_id: UUID
    slo_key: str
    name: str
    description: str
    metric_name: str
    comparator: str
    target_value: float
    window_minutes: int
    minimum_samples: int
    severity: str
    is_active: bool
    created_by_user_id: UUID
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class SLOEvaluation(BaseModel):
    slo_id: UUID
    slo_key: str
    name: str
    metric_name: str
    target_value: float
    observed_value: float | None
    comparator: str
    sample_count: int
    status: Literal["met", "violated", "insufficient_data"]
    error_budget_remaining_percent: float | None = None
    window_minutes: int


class MetricSnapshotRead(ORMModel):
    id: UUID
    organization_id: UUID | None
    metric_name: str
    metric_value: float
    unit: str
    labels: dict[str, Any]
    source: str
    measured_at: datetime


class MetricSeriesPoint(BaseModel):
    measured_at: datetime
    value: float


class MetricSeries(BaseModel):
    metric_name: str
    unit: str
    points: list[MetricSeriesPoint]


class AlertRuleWrite(BaseModel):
    rule_key: str = Field(pattern=r"^[a-z0-9_.-]+$", min_length=2, max_length=120)
    name: str = Field(min_length=3, max_length=240)
    metric_name: str = Field(min_length=2, max_length=160)
    comparator: Literal[">", ">=", "<", "<=", "=="] = ">"
    threshold_value: float
    evaluation_window_minutes: int = Field(default=5, ge=1, le=43200)
    severity: Literal["info", "warning", "critical"] = "warning"
    cooldown_minutes: int = Field(default=15, ge=1, le=10080)
    is_active: bool = True
    description: str = Field(default="", max_length=10000)


class AlertRuleRead(ORMModel):
    id: UUID
    organization_id: UUID
    rule_key: str
    name: str
    metric_name: str
    comparator: str
    threshold_value: float
    evaluation_window_minutes: int
    severity: str
    cooldown_minutes: int
    is_active: bool
    description: str
    created_by_user_id: UUID
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class AlertEventRead(ORMModel):
    id: UUID
    organization_id: UUID
    rule_id: UUID | None
    metric_name: str
    observed_value: float
    threshold_value: float
    severity: str
    status: str
    title: str
    description: str
    evidence: dict[str, Any]
    acknowledged_by_user_id: UUID | None
    resolved_by_user_id: UUID | None
    opened_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime


class AlertStatusWrite(BaseModel):
    status: Literal["acknowledged", "resolved", "dismissed"]


class QuotaWrite(BaseModel):
    quota_key: str = Field(pattern=r"^[a-z0-9_.-]+$", min_length=2, max_length=120)
    limit_value: float = Field(gt=0)
    warning_percentage: float = Field(default=80, ge=1, le=100)
    critical_percentage: float = Field(default=95, ge=1, le=100)
    period: Literal["instant", "daily", "monthly", "total"] = "monthly"
    enforcement_mode: Literal["observe", "warn", "block"] = "warn"
    is_active: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_percentages(self) -> "QuotaWrite":
        if self.warning_percentage > self.critical_percentage:
            raise ValueError("A faixa de aviso não pode superar a faixa crítica")
        return self


class QuotaRead(ORMModel):
    id: UUID
    organization_id: UUID
    quota_key: str
    limit_value: float
    warning_percentage: float
    critical_percentage: float
    period: str
    enforcement_mode: str
    is_active: bool
    configuration: dict[str, Any]
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class QuotaUsage(BaseModel):
    quota_key: str
    limit_value: float
    used_value: float
    usage_percentage: float
    status: Literal["normal", "warning", "critical", "exceeded"]
    enforcement_mode: str
    period: str


class ReconciliationCreate(BaseModel):
    run_type: Literal["full", "assessments", "jobs", "files", "analytics"] = "full"
    repair_safe_findings: bool = False


class ReconciliationRead(ORMModel):
    id: UUID
    organization_id: UUID
    requested_by_user_id: UUID
    run_type: str
    status: str
    findings_count: int
    repaired_count: int
    summary: dict[str, Any]
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DiagnosticRead(ORMModel):
    id: UUID
    organization_id: UUID
    requested_by_user_id: UUID
    status: str
    checks: dict[str, Any]
    warnings: list[str]
    duration_ms: int
    request_id: str
    created_at: datetime
    completed_at: datetime | None


class OperationalOverview(BaseModel):
    generated_at: datetime
    platform_status: str
    request_metrics: dict[str, float]
    jobs: dict[str, Any]
    workers: dict[str, Any]
    dependencies: dict[str, Any]
    incidents: dict[str, int]
    alerts: dict[str, int]
    quotas: list[QuotaUsage]
    slo_summary: dict[str, int]
