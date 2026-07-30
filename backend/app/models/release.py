from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB as JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReleaseArtifact(Base):
    __tablename__ = "release_artifacts"
    __table_args__ = (
        UniqueConstraint("release_id", "artifact_type", "name", name="uq_release_artifact_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    release_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_releases.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    version: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    digest_sha256: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    image_digest: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    sbom_reference: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    signature_reference: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReleaseValidationRun(Base):
    __tablename__ = "release_validation_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    release_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_releases.id", ondelete="CASCADE"), index=True)
    validation_type: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    checks: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    blockers: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeploymentStep(Base):
    __tablename__ = "deployment_steps"
    __table_args__ = (
        UniqueConstraint("release_id", "step_order", name="uq_deployment_step_order"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    release_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_releases.id", ondelete="CASCADE"), index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_key: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DeploymentApproval(Base):
    __tablename__ = "deployment_approvals"
    __table_args__ = (
        UniqueConstraint("release_id", "approval_stage", name="uq_release_approval_stage"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    release_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_releases.id", ondelete="CASCADE"), index=True)
    approval_stage: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    decided_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    decision_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecoveryObjective(Base):
    __tablename__ = "recovery_objectives"
    __table_args__ = (
        UniqueConstraint("organization_id", "environment", "service_name", name="uq_recovery_objective_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    service_name: Mapped[str] = mapped_column(String(100), index=True)
    rpo_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    rto_minutes: Mapped[int] = mapped_column(Integer, default=240, nullable=False)
    backup_frequency_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    last_exercised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RestoreEntityJob(Base):
    __tablename__ = "restore_entity_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    backup_run_id: Mapped[UUID] = mapped_column(ForeignKey("backup_runs.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[UUID | None] = mapped_column(index=True)
    restore_mode: Mapped[str] = mapped_column(String(40), default="copy", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    dependency_plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    impact_preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SecretRotationRecord(Base):
    __tablename__ = "secret_rotation_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    secret_key: Mapped[str] = mapped_column(String(160), index=True)
    provider_type: Mapped[str] = mapped_column(String(60), default="environment", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True)
    rotated_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reason: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    fingerprint_before: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    fingerprint_after: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    next_rotation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MaintenanceWindow(Base):
    __tablename__ = "maintenance_windows"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    mode: Mapped[str] = mapped_column(String(30), default="maintenance", index=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    allow_admin_access: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WorkerDrainEvent(Base):
    __tablename__ = "worker_drain_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    release_id: Mapped[UUID | None] = mapped_column(ForeignKey("deployment_releases.id", ondelete="SET NULL"), index=True)
    queue_name: Mapped[str] = mapped_column(String(80), index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(30), default="drain", index=True)
    status: Mapped[str] = mapped_column(String(30), default="requested", index=True)
    active_jobs_at_request: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
