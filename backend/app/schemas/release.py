from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReleaseArtifactWrite(BaseModel):
    artifact_type: Literal["backend_image", "frontend_image", "worker_image", "sbom", "archive", "manifest"]
    name: str = Field(min_length=1, max_length=240)
    version: str = Field(default="", max_length=80)
    digest_sha256: str = Field(default="", pattern=r"^$|^[a-fA-F0-9]{64}$")
    image_digest: str = Field(default="", max_length=200)
    storage_reference: str = Field(default="", max_length=1000)
    sbom_reference: str = Field(default="", max_length=1000)
    signature_reference: str = Field(default="", max_length=1000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ReleaseArtifactRead(ORMModel):
    id: UUID
    organization_id: UUID
    release_id: UUID
    artifact_type: str
    name: str
    version: str
    digest_sha256: str
    image_digest: str
    storage_reference: str
    sbom_reference: str
    signature_reference: str
    metadata_json: dict[str, Any]
    created_at: datetime


class ReleaseValidationRead(ORMModel):
    id: UUID
    organization_id: UUID
    release_id: UUID
    validation_type: str
    status: str
    checks: dict[str, Any]
    warnings: list[dict[str, Any]]
    blockers: list[dict[str, Any]]
    summary: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DeploymentStepRead(ORMModel):
    id: UUID
    organization_id: UUID
    release_id: UUID
    step_order: int
    step_key: str
    title: str
    status: str
    is_blocking: bool
    details: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DeploymentApprovalWrite(BaseModel):
    approval_stage: Literal["technical", "security", "business", "production"]
    decision: Literal["approved", "rejected"]
    notes: str = Field(default="", max_length=10000)


class DeploymentApprovalRead(ORMModel):
    id: UUID
    organization_id: UUID
    release_id: UUID
    approval_stage: str
    status: str
    requested_by_user_id: UUID
    decided_by_user_id: UUID | None
    decision_notes: str
    requested_at: datetime
    decided_at: datetime | None


class RecoveryObjectiveWrite(BaseModel):
    environment: Literal["development", "test", "homologation", "staging", "production"]
    service_name: str = Field(min_length=2, max_length=100)
    rpo_minutes: int = Field(default=1440, ge=1, le=525600)
    rto_minutes: int = Field(default=240, ge=1, le=525600)
    backup_frequency_minutes: int = Field(default=1440, ge=1, le=525600)
    notes: str = Field(default="", max_length=10000)


class RecoveryObjectiveRead(ORMModel):
    id: UUID
    organization_id: UUID
    environment: str
    service_name: str
    rpo_minutes: int
    rto_minutes: int
    backup_frequency_minutes: int
    last_exercised_at: datetime | None
    notes: str
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class RestoreEntityWrite(BaseModel):
    backup_run_id: UUID
    entity_type: Literal["organization", "project", "comic", "assessment", "asset_collection", "document", "report", "character"]
    entity_id: UUID | None = None
    restore_mode: Literal["copy", "new_version", "replace"] = "copy"


class RestoreEntityRead(ORMModel):
    id: UUID
    organization_id: UUID
    backup_run_id: UUID
    requested_by_user_id: UUID
    entity_type: str
    entity_id: UUID | None
    restore_mode: str
    status: str
    dependency_plan: dict[str, Any]
    impact_preview: dict[str, Any]
    result_summary: dict[str, Any]
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class SecretRotationWrite(BaseModel):
    environment: Literal["development", "test", "homologation", "staging", "production"]
    secret_key: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,159}$")
    provider_type: Literal["environment", "docker_secret", "external_vault"] = "environment"
    reason: str = Field(default="", max_length=500)
    next_rotation_at: datetime | None = None


class SecretRotationRead(ORMModel):
    id: UUID
    organization_id: UUID | None
    environment: str
    secret_key: str
    provider_type: str
    status: str
    rotated_by_user_id: UUID
    reason: str
    fingerprint_before: str
    fingerprint_after: str
    next_rotation_at: datetime | None
    rotated_at: datetime | None
    created_at: datetime


class MaintenanceWindowWrite(BaseModel):
    environment: Literal["development", "test", "homologation", "staging", "production"]
    mode: Literal["read_only", "maintenance"] = "maintenance"
    title: str = Field(min_length=3, max_length=240)
    message: str = Field(default="", max_length=10000)
    starts_at: datetime
    ends_at: datetime
    allow_admin_access: bool = True

    @model_validator(mode="after")
    def validate_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("O fim da manutenção deve ocorrer depois do início")
        return self


class MaintenanceWindowRead(ORMModel):
    id: UUID
    organization_id: UUID | None
    environment: str
    mode: str
    status: str
    title: str
    message: str
    starts_at: datetime
    ends_at: datetime
    allow_admin_access: bool
    created_by_user_id: UUID
    activated_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class WorkerDrainWrite(BaseModel):
    queue_name: Literal["ai", "documents", "analytics", "default", "observability", "all"]
    action: Literal["drain", "resume"] = "drain"
    timeout_seconds: int = Field(default=300, ge=30, le=3600)
    release_id: UUID | None = None


class WorkerDrainRead(ORMModel):
    id: UUID
    organization_id: UUID | None
    release_id: UUID | None
    queue_name: str
    requested_by_user_id: UUID
    action: str
    status: str
    active_jobs_at_request: int
    timeout_seconds: int
    details: dict[str, Any]
    requested_at: datetime
    completed_at: datetime | None


class ReleaseReadiness(BaseModel):
    release_id: UUID
    ready: bool
    score: float
    blockers: list[str]
    warnings: list[str]
    completed_steps: int
    total_steps: int
    approvals: dict[str, str]
    artifact_count: int
    backup_ready: bool
    migration_safe: bool

class MigrationValidationWrite(BaseModel):
    revision: str = Field(min_length=1, max_length=64)
    sql: str = Field(min_length=1, max_length=2_000_000)


class DeploymentStepUpdate(BaseModel):
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    details: dict[str, Any] = Field(default_factory=dict)


class MaintenanceStatusUpdate(BaseModel):
    status: Literal["scheduled", "active", "completed", "cancelled"]


class SecretInventoryItem(BaseModel):
    secret_key: str
    configured: bool
    provider_type: str
    fingerprint: str
    required_in_production: bool
