"""Release management, recovery objectives and controlled deployment.

Revision ID: 0026_release_recovery
Revises: 0025_ops_observability
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0026_release_recovery"
down_revision: str | None = "0025_ops_observability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "release_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("version", sa.String(80), nullable=False, server_default=""),
        sa.Column("digest_sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("image_digest", sa.String(200), nullable=False, server_default=""),
        sa.Column("storage_reference", sa.String(1000), nullable=False, server_default=""),
        sa.Column("sbom_reference", sa.String(1000), nullable=False, server_default=""),
        sa.Column("signature_reference", sa.String(1000), nullable=False, server_default=""),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["deployment_releases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "artifact_type", "name", name="uq_release_artifact_name"),
    )
    op.create_index("ix_release_artifacts_org", "release_artifacts", ["organization_id"])
    op.create_index("ix_release_artifacts_release", "release_artifacts", ["release_id"])
    op.create_index("ix_release_artifacts_type", "release_artifacts", ["artifact_type"])

    op.create_table(
        "release_validation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("validation_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("blockers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["deployment_releases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_release_validation_org", "release_validation_runs", ["organization_id"])
    op.create_index("ix_release_validation_release", "release_validation_runs", ["release_id"])
    op.create_index("ix_release_validation_status", "release_validation_runs", ["status"])
    op.create_index("ix_release_validation_type", "release_validation_runs", ["validation_type"])

    op.create_table(
        "deployment_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_key", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["deployment_releases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "step_order", name="uq_deployment_step_order"),
    )
    op.create_index("ix_deployment_steps_org", "deployment_steps", ["organization_id"])
    op.create_index("ix_deployment_steps_release", "deployment_steps", ["release_id"])
    op.create_index("ix_deployment_steps_key", "deployment_steps", ["step_key"])
    op.create_index("ix_deployment_steps_status", "deployment_steps", ["status"])

    op.create_table(
        "deployment_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("approval_stage", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["deployment_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "approval_stage", name="uq_release_approval_stage"),
    )
    op.create_index("ix_deployment_approvals_org", "deployment_approvals", ["organization_id"])
    op.create_index("ix_deployment_approvals_release", "deployment_approvals", ["release_id"])
    op.create_index("ix_deployment_approvals_stage", "deployment_approvals", ["approval_stage"])
    op.create_index("ix_deployment_approvals_status", "deployment_approvals", ["status"])

    op.create_table(
        "recovery_objectives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("rpo_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("rto_minutes", sa.Integer(), nullable=False, server_default="240"),
        sa.Column("backup_frequency_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("last_exercised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "environment", "service_name", name="uq_recovery_objective_scope"),
    )
    op.create_index("ix_recovery_objectives_org", "recovery_objectives", ["organization_id"])
    op.create_index("ix_recovery_objectives_env", "recovery_objectives", ["environment"])
    op.create_index("ix_recovery_objectives_service", "recovery_objectives", ["service_name"])

    op.create_table(
        "restore_entity_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("backup_run_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("restore_mode", sa.String(40), nullable=False, server_default="copy"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("dependency_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("impact_preview", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["backup_run_id"], ["backup_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_restore_entity_org", "restore_entity_jobs", ["organization_id"])
    op.create_index("ix_restore_entity_backup", "restore_entity_jobs", ["backup_run_id"])
    op.create_index("ix_restore_entity_type", "restore_entity_jobs", ["entity_type"])
    op.create_index("ix_restore_entity_status", "restore_entity_jobs", ["status"])

    op.create_table(
        "secret_rotation_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("secret_key", sa.String(160), nullable=False),
        sa.Column("provider_type", sa.String(60), nullable=False, server_default="environment"),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("rotated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False, server_default=""),
        sa.Column("fingerprint_before", sa.String(64), nullable=False, server_default=""),
        sa.Column("fingerprint_after", sa.String(64), nullable=False, server_default=""),
        sa.Column("next_rotation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rotated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_secret_rotations_org", "secret_rotation_records", ["organization_id"])
    op.create_index("ix_secret_rotations_env", "secret_rotation_records", ["environment"])
    op.create_index("ix_secret_rotations_key", "secret_rotation_records", ["secret_key"])
    op.create_index("ix_secret_rotations_status", "secret_rotation_records", ["status"])

    op.create_table(
        "maintenance_windows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("mode", sa.String(30), nullable=False, server_default="maintenance"),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("allow_admin_access", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_maintenance_windows_org", "maintenance_windows", ["organization_id"])
    op.create_index("ix_maintenance_windows_env", "maintenance_windows", ["environment"])
    op.create_index("ix_maintenance_windows_mode", "maintenance_windows", ["mode"])
    op.create_index("ix_maintenance_windows_status", "maintenance_windows", ["status"])

    op.create_table(
        "worker_drain_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("release_id", sa.Uuid(), nullable=True),
        sa.Column("queue_name", sa.String(80), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(30), nullable=False, server_default="drain"),
        sa.Column("status", sa.String(30), nullable=False, server_default="requested"),
        sa.Column("active_jobs_at_request", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["deployment_releases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_drain_org", "worker_drain_events", ["organization_id"])
    op.create_index("ix_worker_drain_release", "worker_drain_events", ["release_id"])
    op.create_index("ix_worker_drain_queue", "worker_drain_events", ["queue_name"])
    op.create_index("ix_worker_drain_status", "worker_drain_events", ["status"])


def downgrade() -> None:
    op.drop_table("worker_drain_events")
    op.drop_table("maintenance_windows")
    op.drop_table("secret_rotation_records")
    op.drop_table("restore_entity_jobs")
    op.drop_table("recovery_objectives")
    op.drop_table("deployment_approvals")
    op.drop_table("deployment_steps")
    op.drop_table("release_validation_runs")
    op.drop_table("release_artifacts")
