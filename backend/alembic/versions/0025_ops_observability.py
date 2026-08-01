"""Sprint 13.1 - operação e observabilidade.

Revision ID: 0025_ops_observability
Revises: 0024_platform_hardening
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_ops_observability"
down_revision: str | None = "0024_platform_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "slo_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("slo_key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("metric_name", sa.String(160), nullable=False),
        sa.Column("comparator", sa.String(8), nullable=False, server_default=">="),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("minimum_samples", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slo_key", name="uq_slo_org_key"),
    )
    op.create_index("ix_slo_definitions_organization_id", "slo_definitions", ["organization_id"])
    op.create_index("ix_slo_definitions_slo_key", "slo_definitions", ["slo_key"])
    op.create_index("ix_slo_definitions_metric_name", "slo_definitions", ["metric_name"])
    op.create_index("ix_slo_definitions_severity", "slo_definitions", ["severity"])

    op.create_table(
        "operational_metric_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("metric_name", sa.String(160), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False, server_default="count"),
        sa.Column("labels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source", sa.String(80), nullable=False, server_default="educode"),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_snapshots_org", "operational_metric_snapshots", ["organization_id"])
    op.create_index("ix_metric_snapshots_name_time", "operational_metric_snapshots", ["metric_name", "measured_at"])
    op.create_index("ix_metric_snapshots_source", "operational_metric_snapshots", ["source"])

    op.create_table(
        "operational_alert_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(120), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("metric_name", sa.String(160), nullable=False),
        sa.Column("comparator", sa.String(8), nullable=False, server_default=">"),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("evaluation_window_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "rule_key", name="uq_alert_rule_org_key"),
    )
    op.create_index("ix_alert_rules_org", "operational_alert_rules", ["organization_id"])
    op.create_index("ix_alert_rules_metric", "operational_alert_rules", ["metric_name"])
    op.create_index("ix_alert_rules_severity", "operational_alert_rules", ["severity"])

    op.create_table(
        "operational_alert_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("metric_name", sa.String(160), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("acknowledged_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["operational_alert_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_events_org_status", "operational_alert_events", ["organization_id", "status"])
    op.create_index("ix_alert_events_metric", "operational_alert_events", ["metric_name"])
    op.create_index("ix_alert_events_severity", "operational_alert_events", ["severity"])
    op.create_index("ix_alert_events_opened", "operational_alert_events", ["opened_at"])

    op.create_table(
        "organization_quotas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("quota_key", sa.String(120), nullable=False),
        sa.Column("limit_value", sa.Float(), nullable=False),
        sa.Column("warning_percentage", sa.Float(), nullable=False, server_default="80"),
        sa.Column("critical_percentage", sa.Float(), nullable=False, server_default="95"),
        sa.Column("period", sa.String(30), nullable=False, server_default="monthly"),
        sa.Column("enforcement_mode", sa.String(30), nullable=False, server_default="warn"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "quota_key", name="uq_quota_org_key"),
    )
    op.create_index("ix_organization_quotas_org", "organization_quotas", ["organization_id"])
    op.create_index("ix_organization_quotas_key", "organization_quotas", ["quota_key"])

    op.create_table(
        "data_reconciliation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("run_type", sa.String(60), nullable=False, server_default="full"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repaired_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliation_org", "data_reconciliation_runs", ["organization_id"])
    op.create_index("ix_reconciliation_status", "data_reconciliation_runs", ["status"])
    op.create_index("ix_reconciliation_type", "data_reconciliation_runs", ["run_type"])

    op.create_table(
        "diagnostic_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="running"),
        sa.Column("checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("request_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagnostic_runs_org", "diagnostic_runs", ["organization_id"])
    op.create_index("ix_diagnostic_runs_status", "diagnostic_runs", ["status"])
    op.create_index("ix_diagnostic_runs_request", "diagnostic_runs", ["request_id"])


def downgrade() -> None:
    op.drop_table("diagnostic_runs")
    op.drop_table("data_reconciliation_runs")
    op.drop_table("organization_quotas")
    op.drop_table("operational_alert_events")
    op.drop_table("operational_alert_rules")
    op.drop_table("operational_metric_snapshots")
    op.drop_table("slo_definitions")
