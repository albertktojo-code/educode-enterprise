"""Platform hardening, governance and recovery.

Revision ID: 0024_platform_hardening
Revises: 0023_ai_async_operations
Create Date: 2026-07-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0024_platform_hardening"
down_revision = "0023_ai_async_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_OBJECT = sa.text("'{}'::json")
NOW = sa.text("now()")


def _indexes(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "deployment_releases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("build_identifier", sa.String(120), server_default="local", nullable=False),
        sa.Column("commit_sha", sa.String(64), server_default="", nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("migration_revision", sa.String(32), server_default="", nullable=False),
        sa.Column("status", sa.String(30), server_default="deployed", nullable=False),
        sa.Column("release_notes", sa.Text(), server_default="", nullable=False),
        sa.Column("deployed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deployed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "version", "build_identifier", name="uq_release_org_version_build"),
    )
    _indexes("deployment_releases", ("organization_id", "version", "environment", "status", "deployed_by_user_id"))

    op.create_table(
        "backup_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("backup_type", sa.String(30), server_default="full", nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("storage_path", sa.String(1000), server_default="", nullable=False),
        sa.Column("checksum_sha256", sa.String(64), server_default="", nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("manifest", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("error_code", sa.String(100), server_default="", nullable=False),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    _indexes("backup_runs", ("organization_id", "requested_by_user_id", "backup_type", "status"))

    op.create_table(
        "restore_tests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("backup_run_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("validation_summary", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["backup_run_id"], ["backup_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    _indexes("restore_tests", ("organization_id", "backup_run_id", "requested_by_user_id", "status"))

    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid()),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), server_default="info", nullable=False),
        sa.Column("request_id", sa.String(64), server_default="", nullable=False),
        sa.Column("ip_address", sa.String(64), server_default="", nullable=False),
        sa.Column("user_agent", sa.String(500), server_default="", nullable=False),
        sa.Column("details", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("previous_hash", sa.String(64), server_default="", nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    _indexes("security_events", ("organization_id", "user_id", "event_type", "severity", "request_id", "created_at"))

    op.create_table(
        "system_incidents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("severity", sa.String(20), server_default="medium", nullable=False),
        sa.Column("status", sa.String(30), server_default="open", nullable=False),
        sa.Column("affected_service", sa.String(100), server_default="platform", nullable=False),
        sa.Column("impact", sa.Text(), server_default="", nullable=False),
        sa.Column("root_cause", sa.Text(), server_default="", nullable=False),
        sa.Column("resolution", sa.Text(), server_default="", nullable=False),
        sa.Column("opened_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_by_user_id", sa.Uuid()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    _indexes("system_incidents", ("organization_id", "severity", "status", "affected_service", "opened_by_user_id", "resolved_by_user_id"))

    op.create_table(
        "data_retention_policies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("data_type", sa.String(100), nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default="365", nullable=False),
        sa.Column("anonymize_after_days", sa.Integer()),
        sa.Column("delete_after_days", sa.Integer()),
        sa.Column("legal_basis", sa.String(500), server_default="", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "data_type", name="uq_retention_org_data_type"),
    )
    _indexes("data_retention_policies", ("organization_id", "data_type"))

    op.create_table(
        "service_health_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid()),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("details", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
    )
    _indexes("service_health_snapshots", ("organization_id", "service_name", "status", "checked_at"))

    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid()),
        sa.Column("flag_key", sa.String(120), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("scope_type", sa.String(30), server_default="organization", nullable=False),
        sa.Column("scope_id", sa.Uuid()),
        sa.Column("configuration", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "flag_key", "scope_type", "scope_id", name="uq_feature_flag_scope", postgresql_nulls_not_distinct=True),
    )
    _indexes("feature_flags", ("organization_id", "flag_key", "scope_id"))

    op.create_table(
        "system_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("module_name", sa.String(100), nullable=False),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(100), server_default="", nullable=False),
        sa.Column("entity_id", sa.Uuid()),
        sa.Column("request_id", sa.String(64), server_default="", nullable=False),
        sa.Column("ip_address", sa.String(64), server_default="", nullable=False),
        sa.Column("details", sa.JSON(), server_default=JSON_OBJECT, nullable=False),
        sa.Column("previous_hash", sa.String(64), server_default="", nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    _indexes("system_audit_events", ("organization_id", "user_id", "module_name", "action", "entity_type", "entity_id", "request_id", "created_at"))


def downgrade() -> None:
    for table in (
        "system_audit_events",
        "feature_flags",
        "service_health_snapshots",
        "data_retention_policies",
        "system_incidents",
        "security_events",
        "restore_tests",
        "backup_runs",
        "deployment_releases",
    ):
        op.drop_table(table)
