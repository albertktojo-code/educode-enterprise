from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


EnvironmentName = Literal["development", "homologation", "staging", "production"]


class ClusterWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    environment: EnvironmentName
    provider: Literal["kubernetes", "openshift", "docker", "external"] = "kubernetes"
    region: str = Field(default="local", max_length=80)
    api_endpoint: str = Field(default="", max_length=500)
    namespace: str = Field(default="educode", min_length=1, max_length=120)
    is_primary: bool = False
    kubernetes_version: str = Field(default="", max_length=40)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    labels_json: dict[str, str] = Field(default_factory=dict)


class ClusterRead(ORMModel):
    id: UUID
    name: str
    environment: str
    provider: str
    region: str
    api_endpoint: str
    namespace: str
    status: str
    is_primary: bool
    kubernetes_version: str
    capabilities: dict[str, Any]
    labels_json: dict[str, str]
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ClusterHealthWrite(BaseModel):
    status: Literal["healthy", "degraded", "unavailable", "unknown"]
    nodes_ready: int = Field(default=0, ge=0)
    nodes_total: int = Field(default=0, ge=0)
    pods_ready: int = Field(default=0, ge=0)
    pods_total: int = Field(default=0, ge=0)
    cpu_usage_percent: float = Field(default=0, ge=0, le=100)
    memory_usage_percent: float = Field(default=0, ge=0, le=100)
    details: dict[str, Any] = Field(default_factory=dict)


class ClusterHealthRead(ORMModel):
    id: UUID
    cluster_id: UUID
    status: str
    nodes_ready: int
    nodes_total: int
    pods_ready: int
    pods_total: int
    cpu_usage_percent: float
    memory_usage_percent: float
    details: dict[str, Any]
    captured_at: datetime


class StorageTargetWrite(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    provider: Literal["local", "s3"] = "local"
    bucket_name: str = Field(default="", max_length=160)
    endpoint_url: str = Field(default="", max_length=500)
    region: str = Field(default="us-east-1", max_length=80)
    prefix: str = Field(default="educode", max_length=240)
    secret_reference: str = Field(default="", max_length=240)
    is_primary: bool = False
    versioning_enabled: bool = True
    encryption_mode: Literal["none", "provider_managed", "kms"] = "provider_managed"
    object_lock_enabled: bool = False
    configuration_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_provider_fields(self) -> "StorageTargetWrite":
        if self.provider == "s3" and not self.bucket_name:
            raise ValueError("bucket_name é obrigatório para armazenamento S3")
        return self


class StorageTargetRead(ORMModel):
    id: UUID
    name: str
    provider: str
    bucket_name: str
    endpoint_url: str
    region: str
    prefix: str
    secret_reference: str
    status: str
    is_primary: bool
    versioning_enabled: bool
    encryption_mode: str
    object_lock_enabled: bool
    configuration_json: dict[str, Any]
    last_tested_at: datetime | None
    last_test_result: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class StorageTestRead(BaseModel):
    target_id: UUID
    status: str
    latency_ms: float
    checks: dict[str, Any]
    warnings: list[str]


class ReplicationLinkWrite(BaseModel):
    source_target_id: UUID
    destination_target_id: UUID
    mode: Literal["asynchronous", "scheduled", "manual"] = "asynchronous"
    schedule: str = Field(default="", max_length=120)
    configuration_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def targets_must_differ(self) -> "ReplicationLinkWrite":
        if self.source_target_id == self.destination_target_id:
            raise ValueError("Origem e destino da replicação devem ser diferentes")
        return self


class ReplicationLinkRead(ORMModel):
    id: UUID
    source_target_id: UUID
    destination_target_id: UUID
    mode: str
    status: str
    schedule: str
    lag_seconds: int
    last_checkpoint: str
    configuration_json: dict[str, Any]
    last_replicated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DRPlanWrite(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    environment: EnvironmentName
    primary_cluster_id: UUID
    recovery_cluster_id: UUID
    replication_link_id: UUID | None = None
    rpo_minutes: int = Field(default=60, ge=1, le=525600)
    rto_minutes: int = Field(default=240, ge=1, le=525600)
    approval_required: bool = True
    runbook_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def clusters_must_differ(self) -> "DRPlanWrite":
        if self.primary_cluster_id == self.recovery_cluster_id:
            raise ValueError("Clusters primário e de recuperação devem ser diferentes")
        return self


class DRPlanRead(ORMModel):
    id: UUID
    name: str
    environment: str
    status: str
    primary_cluster_id: UUID
    recovery_cluster_id: UUID
    replication_link_id: UUID | None
    rpo_minutes: int
    rto_minutes: int
    approval_required: bool
    runbook_json: dict[str, Any]
    last_exercised_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DRReadiness(BaseModel):
    plan_id: UUID
    ready: bool
    score: float
    blockers: list[str]
    warnings: list[str]
    primary_status: str
    recovery_status: str
    replication_status: str


class DRRunCreate(BaseModel):
    run_type: Literal["drill", "failover", "failback"] = "drill"
    reason: str = Field(default="", max_length=2000)


class DRRunRead(ORMModel):
    id: UUID
    plan_id: UUID
    run_type: str
    status: str
    current_step: str
    checkpoint_json: dict[str, Any]
    metrics_json: dict[str, Any]
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class FailoverEventCreate(BaseModel):
    direction: Literal["failover", "failback"] = "failover"
    reason: str = Field(min_length=5, max_length=4000)


class FailoverEventDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    notes: str = Field(default="", max_length=4000)


class FailoverEventRead(ORMModel):
    id: UUID
    plan_id: UUID
    run_id: UUID | None
    direction: str
    status: str
    reason: str
    requested_by_user_id: UUID
    approved_by_user_id: UUID | None
    initiated_at: datetime | None
    completed_at: datetime | None
    details: dict[str, Any]
    created_at: datetime


class GitOpsApplicationWrite(BaseModel):
    cluster_id: UUID
    name: str = Field(min_length=2, max_length=160)
    environment: EnvironmentName
    repository_url: str = Field(min_length=5, max_length=500)
    manifest_path: str = Field(min_length=1, max_length=500)
    target_revision: str = Field(default="main", max_length=120)
    namespace: str = Field(default="educode", max_length=120)
    sync_policy: Literal["manual", "automated", "automated_prune"] = "manual"
    configuration_json: dict[str, Any] = Field(default_factory=dict)


class GitOpsApplicationRead(ORMModel):
    id: UUID
    cluster_id: UUID
    name: str
    environment: str
    repository_url: str
    manifest_path: str
    target_revision: str
    namespace: str
    sync_policy: str
    sync_status: str
    health_status: str
    last_sync_revision: str
    configuration_json: dict[str, Any]
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutoscalingPolicyWrite(BaseModel):
    environment: EnvironmentName
    component: Literal["backend", "frontend", "worker-ai", "worker-documents", "worker-analytics", "worker-default"]
    enabled: bool = True
    min_replicas: int = Field(default=1, ge=0, le=100)
    max_replicas: int = Field(default=5, ge=1, le=500)
    target_cpu_percent: int = Field(default=70, ge=10, le=100)
    target_memory_percent: int = Field(default=75, ge=10, le=100)
    queue_depth_target: int = Field(default=20, ge=1, le=100000)
    scale_down_stabilization_seconds: int = Field(default=300, ge=0, le=3600)
    configuration_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_replica_range(self) -> "AutoscalingPolicyWrite":
        if self.max_replicas < self.min_replicas:
            raise ValueError("max_replicas deve ser maior ou igual a min_replicas")
        return self


class AutoscalingPolicyRead(ORMModel):
    id: UUID
    environment: str
    component: str
    enabled: bool
    min_replicas: int
    max_replicas: int
    target_cpu_percent: int
    target_memory_percent: int
    queue_depth_target: int
    scale_down_stabilization_seconds: int
    configuration_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CapacityRecommendation(BaseModel):
    component: str
    current_replicas: int
    recommended_replicas: int
    reason: str
    signals: dict[str, float]


class InfrastructureOverview(BaseModel):
    clusters: int
    healthy_clusters: int
    storage_targets: int
    healthy_storage_targets: int
    replication_links: int
    dr_plans: int
    gitops_applications: int
    autoscaling_policies: int
    kubernetes_enabled: bool
    gitops_enabled: bool
    object_storage_provider: str
