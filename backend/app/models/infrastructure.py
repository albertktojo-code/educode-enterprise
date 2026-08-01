from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB as JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InfrastructureCluster(Base):
    __tablename__ = "infrastructure_clusters"
    __table_args__ = (
        UniqueConstraint("organization_id", "environment", "name", name="uq_infra_cluster_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="kubernetes", nullable=False)
    region: Mapped[str] = mapped_column(String(80), default="local", nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    namespace: Mapped[str] = mapped_column(String(120), default="educode", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kubernetes_version: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    labels_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ClusterHealthSnapshot(Base):
    __tablename__ = "cluster_health_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[UUID] = mapped_column(ForeignKey("infrastructure_clusters.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    nodes_ready: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nodes_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pods_ready: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pods_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cpu_usage_percent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    memory_usage_percent: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)


class ObjectStorageTarget(Base):
    __tablename__ = "object_storage_targets"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_object_storage_target_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), default="local", index=True)
    bucket_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    region: Mapped[str] = mapped_column(String(80), default="us-east-1", nullable=False)
    prefix: Mapped[str] = mapped_column(String(240), default="educode", nullable=False)
    secret_reference: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    versioning_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    encryption_mode: Mapped[str] = mapped_column(String(40), default="provider_managed", nullable=False)
    object_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_test_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class StorageReplicationLink(Base):
    __tablename__ = "storage_replication_links"
    __table_args__ = (
        UniqueConstraint("source_target_id", "destination_target_id", name="uq_storage_replication_pair"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    source_target_id: Mapped[UUID] = mapped_column(ForeignKey("object_storage_targets.id", ondelete="CASCADE"), index=True)
    destination_target_id: Mapped[UUID] = mapped_column(ForeignKey("object_storage_targets.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(30), default="asynchronous", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="configured", index=True)
    schedule: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    lag_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_checkpoint: Mapped[str] = mapped_column(String(240), default="", nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_replicated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DisasterRecoveryPlan(Base):
    __tablename__ = "disaster_recovery_plans"
    __table_args__ = (
        UniqueConstraint("organization_id", "environment", "name", name="uq_dr_plan_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    primary_cluster_id: Mapped[UUID] = mapped_column(ForeignKey("infrastructure_clusters.id", ondelete="RESTRICT"), index=True)
    recovery_cluster_id: Mapped[UUID] = mapped_column(ForeignKey("infrastructure_clusters.id", ondelete="RESTRICT"), index=True)
    replication_link_id: Mapped[UUID | None] = mapped_column(ForeignKey("storage_replication_links.id", ondelete="SET NULL"), index=True)
    rpo_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    rto_minutes: Mapped[int] = mapped_column(Integer, default=240, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    runbook_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_exercised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DisasterRecoveryRun(Base):
    __tablename__ = "disaster_recovery_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("disaster_recovery_plans.id", ondelete="CASCADE"), index=True)
    initiated_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    run_type: Mapped[str] = mapped_column(String(30), default="drill", index=True)
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    current_step: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    checkpoint_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FailoverEvent(Base):
    __tablename__ = "failover_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("disaster_recovery_plans.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("disaster_recovery_runs.id", ondelete="SET NULL"), index=True)
    direction: Mapped[str] = mapped_column(String(30), default="failover", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="requested", index=True)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GitOpsApplication(Base):
    __tablename__ = "gitops_applications"
    __table_args__ = (
        UniqueConstraint("organization_id", "environment", "name", name="uq_gitops_application_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[UUID] = mapped_column(ForeignKey("infrastructure_clusters.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    repository_url: Mapped[str] = mapped_column(String(500), nullable=False)
    manifest_path: Mapped[str] = mapped_column(String(500), nullable=False)
    target_revision: Mapped[str] = mapped_column(String(120), default="main", nullable=False)
    namespace: Mapped[str] = mapped_column(String(120), default="educode", nullable=False)
    sync_policy: Mapped[str] = mapped_column(String(30), default="manual", nullable=False)
    sync_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    health_status: Mapped[str] = mapped_column(String(30), default="unknown", index=True)
    last_sync_revision: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AutoscalingPolicy(Base):
    __tablename__ = "autoscaling_policies"
    __table_args__ = (
        UniqueConstraint("organization_id", "environment", "component", name="uq_autoscaling_policy_scope"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    environment: Mapped[str] = mapped_column(String(40), index=True)
    component: Mapped[str] = mapped_column(String(100), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_replicas: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_replicas: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    target_cpu_percent: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    target_memory_percent: Mapped[int] = mapped_column(Integer, default=75, nullable=False)
    queue_depth_target: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    scale_down_stabilization_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
