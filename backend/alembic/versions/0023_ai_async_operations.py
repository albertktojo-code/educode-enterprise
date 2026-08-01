"""AI async operations and workers.

Revision ID: 0023_ai_async_operations
Revises: 0022_ai_fabric_advanced_flow
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0023_ai_async_operations"
down_revision = "0022_ai_fabric_advanced_flow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_OBJECT = sa.text("'{}'::json")
NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(80), nullable=False),
        sa.Column("queue_name", sa.String(40), nullable=False),
        sa.Column("module_name", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80)),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("ai_flow_id", sa.String(64)),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="50", nullable=False),
        sa.Column("progress_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_step", sa.String(160), server_default="Aguardando", nullable=False),
        sa.Column("total_steps", sa.Integer(), server_default="1", nullable=False),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("result_reference", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("error_code", sa.String(100), server_default="", nullable=False),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True)),
        sa.Column("queued_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_background_job_org_idempotency"
        ),
    )
    for column in (
        "organization_id",
        "requested_by_user_id",
        "job_type",
        "queue_name",
        "module_name",
        "entity_type",
        "entity_id",
        "ai_flow_id",
        "status",
    ):
        op.create_index(f"ix_background_jobs_{column}", "background_jobs", [column])

    op.create_table(
        "background_job_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("worker_name", sa.String(160), server_default="", nullable=False),
        sa.Column("status", sa.String(32), server_default="processing", nullable=False),
        sa.Column("error_code", sa.String(100), server_default="", nullable=False),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_job_attempt_number"),
    )
    for column in ("organization_id", "job_id", "status"):
        op.create_index(f"ix_background_job_attempts_{column}", "background_job_attempts", [column])

    op.create_table(
        "background_job_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_data", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"], ondelete="CASCADE"),
    )
    for column in ("organization_id", "job_id", "event_type", "created_at"):
        op.create_index(f"ix_background_job_events_{column}", "background_job_events", [column])

    op.create_table(
        "job_dependencies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("depends_on_job_id", sa.Uuid(), nullable=False),
        sa.Column("required_status", sa.String(32), server_default="completed", nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_job_id"], ["background_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "depends_on_job_id", name="uq_job_dependency_pair"),
    )
    for column in ("organization_id", "job_id", "depends_on_job_id"):
        op.create_index(f"ix_job_dependencies_{column}", "job_dependencies", [column])

    op.create_table(
        "job_notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("action_path", sa.String(500)),
        sa.Column("status", sa.String(30), server_default="unread", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"], ondelete="CASCADE"),
    )
    for column in ("organization_id", "user_id", "job_id", "status"):
        op.create_index(f"ix_job_notifications_{column}", "job_notifications", [column])

    op.create_table(
        "provider_circuit_states",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(20), server_default="closed", nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failure_threshold", sa.Integer(), server_default="5", nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("next_probe_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text(), server_default="", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_providers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organization_id", "provider_id", name="uq_provider_circuit_org_provider"
        ),
    )
    for column in ("organization_id", "provider_id", "state"):
        op.create_index(f"ix_provider_circuit_states_{column}", "provider_circuit_states", [column])

    op.create_table(
        "semantic_cache_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("module_name", sa.String(80), nullable=False),
        sa.Column("action_name", sa.String(100), nullable=False),
        sa.Column("cache_key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("result_id", sa.Uuid()),
        sa.Column("approved_only", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("hit_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_id"], ["ai_generation_results.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "cache_key", name="uq_semantic_cache_org_key"),
    )
    for column in ("organization_id", "module_name", "action_name", "result_id"):
        op.create_index(f"ix_semantic_cache_entries_{column}", "semantic_cache_entries", [column])

    op.create_table(
        "resource_reservations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("reserved_units", sa.Float(), server_default="0", nullable=False),
        sa.Column("reserved_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("actual_units", sa.Float(), server_default="0", nullable=False),
        sa.Column("actual_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="reserved", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["background_jobs.id"], ondelete="CASCADE"),
    )
    for column in ("organization_id", "job_id", "resource_type", "status"):
        op.create_index(f"ix_resource_reservations_{column}", "resource_reservations", [column])

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("worker_name", sa.String(160), nullable=False),
        sa.Column("queue_name", sa.String(40), nullable=False),
        sa.Column("hostname", sa.String(160), server_default="", nullable=False),
        sa.Column("process_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_job_id", sa.Uuid()),
        sa.Column("status", sa.String(30), server_default="idle", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.UniqueConstraint("worker_name", name="uq_worker_heartbeat_name"),
    )
    for column in ("queue_name", "current_job_id", "status", "last_seen_at"):
        op.create_index(f"ix_worker_heartbeats_{column}", "worker_heartbeats", [column])


def downgrade() -> None:
    for table in (
        "worker_heartbeats",
        "resource_reservations",
        "semantic_cache_entries",
        "provider_circuit_states",
        "job_notifications",
        "job_dependencies",
        "background_job_events",
        "background_job_attempts",
        "background_jobs",
    ):
        op.drop_table(table)
