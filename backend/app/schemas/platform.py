from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlatformVersionRead(BaseModel):
    application: str
    version: str
    build_identifier: str
    commit_sha: str
    environment: str
    migration_revision: str
    maintenance_mode: bool


class DependencyStatus(BaseModel):
    name: str
    status: Literal["healthy", "degraded", "unavailable"]
    latency_ms: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsRead(BaseModel):
    overall_status: Literal["healthy", "degraded", "unavailable"]
    version: PlatformVersionRead
    dependencies: list[DependencyStatus]
    storage: dict[str, Any]
    workers: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


class PreflightRead(BaseModel):
    ready: bool
    checks: list[DependencyStatus]
    warnings: list[str] = Field(default_factory=list)


class DeploymentCreate(BaseModel):
    version: str = Field(min_length=1, max_length=40)
    build_identifier: str = Field(default="local", max_length=120)
    commit_sha: str = Field(default="", max_length=64)
    release_notes: str = Field(default="", max_length=10000)


class DeploymentRead(ORMModel):
    id: UUID
    organization_id: UUID
    version: str
    build_identifier: str
    commit_sha: str
    environment: str
    migration_revision: str
    status: str
    release_notes: str
    deployed_by_user_id: UUID
    deployed_at: datetime
    created_at: datetime


class BackupCreate(BaseModel):
    backup_type: Literal["database", "full"] = "full"
    retention_days: int = Field(default=30, ge=1, le=3650)


class BackupRead(ORMModel):
    id: UUID
    organization_id: UUID
    requested_by_user_id: UUID
    backup_type: str
    status: str
    storage_path: str
    checksum_sha256: str
    size_bytes: int
    manifest: dict[str, Any]
    error_code: str
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class RestoreTestRead(ORMModel):
    id: UUID
    organization_id: UUID
    backup_run_id: UUID
    requested_by_user_id: UUID
    status: str
    validation_summary: dict[str, Any]
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    affected_service: str = Field(default="platform", max_length=100)
    impact: str = Field(default="", max_length=10000)


class IncidentUpdate(BaseModel):
    status: Literal["open", "investigating", "monitoring", "resolved", "closed"] | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    impact: str | None = Field(default=None, max_length=10000)
    root_cause: str | None = Field(default=None, max_length=10000)
    resolution: str | None = Field(default=None, max_length=10000)


class IncidentRead(ORMModel):
    id: UUID
    organization_id: UUID
    title: str
    severity: str
    status: str
    affected_service: str
    impact: str
    root_cause: str
    resolution: str
    opened_by_user_id: UUID
    resolved_by_user_id: UUID | None
    started_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RetentionPolicyWrite(BaseModel):
    data_type: str = Field(min_length=2, max_length=100)
    retention_days: int = Field(ge=1, le=36500)
    anonymize_after_days: int | None = Field(default=None, ge=1, le=36500)
    delete_after_days: int | None = Field(default=None, ge=1, le=36500)
    legal_basis: str = Field(default="", max_length=500)
    is_active: bool = True


class RetentionPolicyRead(ORMModel):
    id: UUID
    organization_id: UUID
    data_type: str
    retention_days: int
    anonymize_after_days: int | None
    delete_after_days: int | None
    legal_basis: str
    is_active: bool
    created_by_user_id: UUID
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class FeatureFlagWrite(BaseModel):
    flag_key: str = Field(pattern=r"^[a-z0-9_.-]+$", min_length=2, max_length=120)
    is_enabled: bool
    scope_type: Literal["platform", "organization", "user", "classroom"] = "organization"
    scope_id: UUID | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", max_length=500)


class FeatureFlagRead(ORMModel):
    id: UUID
    organization_id: UUID | None
    flag_key: str
    is_enabled: bool
    scope_type: str
    scope_id: UUID | None
    configuration: dict[str, Any]
    description: str
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class AuditEventRead(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID | None
    module_name: str
    action: str
    entity_type: str
    entity_id: UUID | None
    request_id: str
    ip_address: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str
    created_at: datetime


class SecurityEventRead(ORMModel):
    id: UUID
    organization_id: UUID | None
    user_id: UUID | None
    event_type: str
    severity: str
    request_id: str
    ip_address: str
    user_agent: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str
    created_at: datetime


class IntegrityFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "critical"]
    count: int
    description: str
    sample_ids: list[str] = Field(default_factory=list)


class IntegrityReport(BaseModel):
    status: Literal["healthy", "warnings", "critical"]
    checked_at: datetime
    findings: list[IntegrityFinding]
