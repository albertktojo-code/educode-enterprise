"""Sprint 15.5 - assessment analytics and institutional reports.

Revision ID: 0035_assessment_analytics
Revises: 0034_review_feedback
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0035_assessment_analytics"
down_revision: str | None = "0034_review_feedback"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "assessment_analytics_models",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("configuration", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("privacy_rules", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metric_definitions", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("published_by_user_id", UUID),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_assessment_analytics_model_version"),
    )
    op.create_index("ix_assessment_analytics_models_status", "assessment_analytics_models", ["organization_id", "status", "is_default"])

    op.create_table(
        "assessment_analytics_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("analytics_model_id", UUID, nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_id", UUID),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("requested_by_user_id", UUID, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column("filters", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("input_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_assessment_analytics_runs_status", "assessment_analytics_runs", ["organization_id", "status", "created_at"])
    op.create_index("ix_assessment_analytics_runs_scope", "assessment_analytics_runs", ["organization_id", "scope_type", "scope_id"])

    op.create_table(
        "assessment_item_metrics",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("analytics_run_id", UUID, nullable=False),
        sa.Column("assessment_id", UUID),
        sa.Column("question_version_id", UUID, nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("predicted_difficulty", sa.Float()),
        sa.Column("observed_difficulty", sa.Float()),
        sa.Column("difficulty_delta", sa.Float()),
        sa.Column("facility_index", sa.Float()),
        sa.Column("discrimination_index", sa.Float()),
        sa.Column("point_biserial", sa.Float()),
        sa.Column("omission_rate", sa.Float()),
        sa.Column("average_response_time_seconds", sa.Float()),
        sa.Column("average_attempts", sa.Float()),
        sa.Column("hint_usage_rate", sa.Float()),
        sa.Column("review_rate", sa.Float()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("flags", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("calculation_details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "analytics_run_id", "question_version_id", name="uq_assessment_item_metric_run"),
    )
    op.create_index("ix_assessment_item_metrics_question", "assessment_item_metrics", ["organization_id", "question_version_id", "calculated_at"])

    op.create_table(
        "assessment_distractor_metrics",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("item_metric_id", UUID, nullable=False),
        sa.Column("option_code", sa.String(80), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selection_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selection_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("upper_group_rate", sa.Float()),
        sa.Column("lower_group_rate", sa.Float()),
        sa.Column("discrimination_signal", sa.Float()),
        sa.Column("non_functioning", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("flags", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "item_metric_id", "option_code", name="uq_assessment_distractor_option"),
    )
    op.create_index("ix_assessment_distractor_item", "assessment_distractor_metrics", ["organization_id", "item_metric_id"])

    op.create_table(
        "assessment_skill_metrics",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("analytics_run_id", UUID, nullable=False),
        sa.Column("skill_type", sa.String(30), nullable=False),
        sa.Column("skill_code", sa.String(100), nullable=False),
        sa.Column("skill_name", sa.String(220), nullable=False),
        sa.Column("cohort_key", sa.String(160), nullable=False, server_default="ALL"),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("items_count", sa.Integer(), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mastery_rate", sa.Float()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("trend", sa.String(30)),
        sa.Column("gap_indicators", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "analytics_run_id", "skill_type", "skill_code", "cohort_key", name="uq_assessment_skill_metric"),
    )
    op.create_index("ix_assessment_skill_metrics_skill", "assessment_skill_metrics", ["organization_id", "skill_type", "skill_code"])

    op.create_table(
        "assessment_cohort_metrics",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("analytics_run_id", UUID, nullable=False),
        sa.Column("cohort_type", sa.String(30), nullable=False),
        sa.Column("cohort_id", UUID, nullable=False),
        sa.Column("cohort_name", sa.String(220), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("median_score", sa.Float()),
        sa.Column("standard_deviation", sa.Float()),
        sa.Column("average_duration_seconds", sa.Float()),
        sa.Column("review_pending_rate", sa.Float()),
        sa.Column("accessibility_usage_rate", sa.Float()),
        sa.Column("privacy_suppressed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "analytics_run_id", "cohort_type", "cohort_id", name="uq_assessment_cohort_metric"),
    )
    op.create_index("ix_assessment_cohort_metrics_cohort", "assessment_cohort_metrics", ["organization_id", "cohort_type", "cohort_id"])

    op.create_table(
        "assessment_report_definitions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("audience", sa.String(30), nullable=False, server_default="TEACHER"),
        sa.Column("sections", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("filters", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("privacy_rules", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "code", name="uq_assessment_report_definition_code"),
    )
    op.create_index("ix_assessment_report_definitions_status", "assessment_report_definitions", ["organization_id", "status", "audience"])

    op.create_table(
        "assessment_report_exports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("report_definition_id", UUID, nullable=False),
        sa.Column("analytics_run_id", UUID),
        sa.Column("requested_by_user_id", UUID, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("format", sa.String(20), nullable=False, server_default="CSV"),
        sa.Column("parameters", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("storage_reference", sa.Text()),
        sa.Column("checksum", sa.String(64)),
        sa.Column("row_count", sa.Integer()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_assessment_report_exports_status", "assessment_report_exports", ["organization_id", "status", "created_at"])
    op.create_index("ix_assessment_report_exports_definition", "assessment_report_exports", ["organization_id", "report_definition_id"])


def downgrade() -> None:
    for table in (
        "assessment_report_exports",
        "assessment_report_definitions",
        "assessment_cohort_metrics",
        "assessment_skill_metrics",
        "assessment_distractor_metrics",
        "assessment_item_metrics",
        "assessment_analytics_runs",
        "assessment_analytics_models",
    ):
        op.drop_table(table)
