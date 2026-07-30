"""Distributed infrastructure, object storage, GitOps and disaster recovery.

Revision ID: 0027_infra_continuity
Revises: 0026_release_recovery
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0027_infra_continuity"
down_revision: str | None = "0026_release_recovery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "infrastructure_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False, server_default="kubernetes"),
        sa.Column("region", sa.String(80), nullable=False, server_default="local"),
        sa.Column("api_endpoint", sa.String(500), nullable=False, server_default=""),
        sa.Column("namespace", sa.String(120), nullable=False, server_default="educode"),
        sa.Column("status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("kubernetes_version", sa.String(40), nullable=False, server_default=""),
        sa.Column("capabilities", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("labels_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "environment", "name", name="uq_infra_cluster_scope"),
    )
    op.create_index("ix_infra_clusters_org", "infrastructure_clusters", ["organization_id"])
    op.create_index("ix_infra_clusters_env", "infrastructure_clusters", ["environment"])
    op.create_index("ix_infra_clusters_status", "infrastructure_clusters", ["status"])
    op.create_index("ix_infra_clusters_creator", "infrastructure_clusters", ["created_by_user_id"])

    op.create_table(
        "cluster_health_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("nodes_ready", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nodes_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pods_ready", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pods_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cpu_usage_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("memory_usage_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["infrastructure_clusters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cluster_health_org", "cluster_health_snapshots", ["organization_id"])
    op.create_index("ix_cluster_health_cluster", "cluster_health_snapshots", ["cluster_id"])
    op.create_index("ix_cluster_health_status", "cluster_health_snapshots", ["status"])
    op.create_index("ix_cluster_health_time", "cluster_health_snapshots", ["captured_at"])

    op.create_table(
        "object_storage_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False, server_default="local"),
        sa.Column("bucket_name", sa.String(160), nullable=False, server_default=""),
        sa.Column("endpoint_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("region", sa.String(80), nullable=False, server_default="us-east-1"),
        sa.Column("prefix", sa.String(240), nullable=False, server_default="educode"),
        sa.Column("secret_reference", sa.String(240), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("versioning_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("encryption_mode", sa.String(40), nullable=False, server_default="provider_managed"),
        sa.Column("object_lock_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("configuration_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_result", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_object_storage_target_name"),
    )
    op.create_index("ix_object_storage_org", "object_storage_targets", ["organization_id"])
    op.create_index("ix_object_storage_provider", "object_storage_targets", ["provider"])
    op.create_index("ix_object_storage_status", "object_storage_targets", ["status"])
    op.create_index("ix_object_storage_creator", "object_storage_targets", ["created_by_user_id"])

    op.create_table(
        "storage_replication_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_target_id", sa.Uuid(), nullable=False),
        sa.Column("destination_target_id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False, server_default="asynchronous"),
        sa.Column("status", sa.String(30), nullable=False, server_default="configured"),
        sa.Column("schedule", sa.String(120), nullable=False, server_default=""),
        sa.Column("lag_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_checkpoint", sa.String(240), nullable=False, server_default=""),
        sa.Column("configuration_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_replicated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_target_id"], ["object_storage_targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["destination_target_id"], ["object_storage_targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_target_id", "destination_target_id", name="uq_storage_replication_pair"),
    )
    op.create_index("ix_storage_repl_org", "storage_replication_links", ["organization_id"])
    op.create_index("ix_storage_repl_source", "storage_replication_links", ["source_target_id"])
    op.create_index("ix_storage_repl_dest", "storage_replication_links", ["destination_target_id"])
    op.create_index("ix_storage_repl_status", "storage_replication_links", ["status"])
    op.create_index("ix_storage_repl_creator", "storage_replication_links", ["created_by_user_id"])

    op.create_table(
        "disaster_recovery_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("primary_cluster_id", sa.Uuid(), nullable=False),
        sa.Column("recovery_cluster_id", sa.Uuid(), nullable=False),
        sa.Column("replication_link_id", sa.Uuid(), nullable=True),
        sa.Column("rpo_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("rto_minutes", sa.Integer(), nullable=False, server_default="240"),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("runbook_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_exercised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_cluster_id"], ["infrastructure_clusters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recovery_cluster_id"], ["infrastructure_clusters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["replication_link_id"], ["storage_replication_links.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "environment", "name", name="uq_dr_plan_scope"),
    )
    op.create_index("ix_dr_plans_org", "disaster_recovery_plans", ["organization_id"])
    op.create_index("ix_dr_plans_env", "disaster_recovery_plans", ["environment"])
    op.create_index("ix_dr_plans_status", "disaster_recovery_plans", ["status"])
    op.create_index("ix_dr_plans_primary", "disaster_recovery_plans", ["primary_cluster_id"])
    op.create_index("ix_dr_plans_recovery", "disaster_recovery_plans", ["recovery_cluster_id"])
    op.create_index("ix_dr_plans_replication", "disaster_recovery_plans", ["replication_link_id"])
    op.create_index("ix_dr_plans_creator", "disaster_recovery_plans", ["created_by_user_id"])

    op.create_table(
        "disaster_recovery_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(30), nullable=False, server_default="drill"),
        sa.Column("status", sa.String(30), nullable=False, server_default="planned"),
        sa.Column("current_step", sa.String(160), nullable=False, server_default=""),
        sa.Column("checkpoint_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metrics_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["disaster_recovery_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dr_runs_org", "disaster_recovery_runs", ["organization_id"])
    op.create_index("ix_dr_runs_plan", "disaster_recovery_runs", ["plan_id"])
    op.create_index("ix_dr_runs_user", "disaster_recovery_runs", ["initiated_by_user_id"])
    op.create_index("ix_dr_runs_type", "disaster_recovery_runs", ["run_type"])
    op.create_index("ix_dr_runs_status", "disaster_recovery_runs", ["status"])

    op.create_table(
        "failover_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("direction", sa.String(30), nullable=False, server_default="failover"),
        sa.Column("status", sa.String(30), nullable=False, server_default="requested"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["disaster_recovery_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["disaster_recovery_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_failover_org", "failover_events", ["organization_id"])
    op.create_index("ix_failover_plan", "failover_events", ["plan_id"])
    op.create_index("ix_failover_run", "failover_events", ["run_id"])
    op.create_index("ix_failover_status", "failover_events", ["status"])

    op.create_table(
        "gitops_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("repository_url", sa.String(500), nullable=False),
        sa.Column("manifest_path", sa.String(500), nullable=False),
        sa.Column("target_revision", sa.String(120), nullable=False, server_default="main"),
        sa.Column("namespace", sa.String(120), nullable=False, server_default="educode"),
        sa.Column("sync_policy", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("sync_status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("health_status", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("last_sync_revision", sa.String(160), nullable=False, server_default=""),
        sa.Column("configuration_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["infrastructure_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "environment", "name", name="uq_gitops_application_scope"),
    )
    op.create_index("ix_gitops_org", "gitops_applications", ["organization_id"])
    op.create_index("ix_gitops_cluster", "gitops_applications", ["cluster_id"])
    op.create_index("ix_gitops_env", "gitops_applications", ["environment"])
    op.create_index("ix_gitops_sync", "gitops_applications", ["sync_status"])
    op.create_index("ix_gitops_health", "gitops_applications", ["health_status"])
    op.create_index("ix_gitops_creator", "gitops_applications", ["created_by_user_id"])

    op.create_table(
        "autoscaling_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("component", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_replicas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_replicas", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("target_cpu_percent", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("target_memory_percent", sa.Integer(), nullable=False, server_default="75"),
        sa.Column("queue_depth_target", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("scale_down_stabilization_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("configuration_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "environment", "component", name="uq_autoscaling_policy_scope"),
    )
    op.create_index("ix_autoscaling_org", "autoscaling_policies", ["organization_id"])
    op.create_index("ix_autoscaling_env", "autoscaling_policies", ["environment"])
    op.create_index("ix_autoscaling_component", "autoscaling_policies", ["component"])
    op.create_index("ix_autoscaling_creator", "autoscaling_policies", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_table("autoscaling_policies")
    op.drop_table("gitops_applications")
    op.drop_table("failover_events")
    op.drop_table("disaster_recovery_runs")
    op.drop_table("disaster_recovery_plans")
    op.drop_table("storage_replication_links")
    op.drop_table("object_storage_targets")
    op.drop_table("cluster_health_snapshots")
    op.drop_table("infrastructure_clusters")
