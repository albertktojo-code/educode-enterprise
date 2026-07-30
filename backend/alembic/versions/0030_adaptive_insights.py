"""Intervention intelligence, material efficacy, model simulation and experiments.

Revision ID: 0030_adaptive_insights
Revises: 0029_adaptive_learning_evolution
Create Date: 2026-07-27

The installer replaces down_revision with the actual current Alembic head.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_adaptive_insights"
down_revision: str | None = "0029_adaptive_learning_evolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "intervention_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("learning_node_id", sa.Uuid(), nullable=False),
        sa.Column("intervention_type", sa.String(80), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("mastery_before", sa.Float(), nullable=False),
        sa.Column("mastery_after", sa.Float(), nullable=False),
        sa.Column("mastery_gain", sa.Float(), nullable=False),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="1"),
        sa.Column("hints_average", sa.Float(), nullable=False, server_default="0"),
        sa.Column("attempts_average", sa.Float(), nullable=False, server_default="1"),
        sa.Column("outcome", sa.String(30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_intervention_outcomes_student_node", "intervention_outcomes", ["organization_id", "student_id", "learning_node_id", "occurred_at"])
    op.create_index("ix_intervention_outcomes_material", "intervention_outcomes", ["organization_id", "material_id", "intervention_type"])

    op.create_table(
        "material_effectiveness_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("completion_rate", sa.Float(), nullable=False),
        sa.Column("accuracy_rate", sa.Float(), nullable=True),
        sa.Column("average_gain", sa.Float(), nullable=True),
        sa.Column("median_gain", sa.Float(), nullable=True),
        sa.Column("average_attempts", sa.Float(), nullable=False),
        sa.Column("average_hints", sa.Float(), nullable=False),
        sa.Column("average_duration_seconds", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("metrics_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("calculation_version", sa.String(60), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "resource_type", "resource_id", "calculation_version", name="uq_material_effectiveness_version"),
    )
    op.create_index("ix_material_effectiveness_classification", "material_effectiveness_metrics", ["organization_id", "classification", "sample_size"])

    op.create_table(
        "adaptive_insight_model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("version", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope_type", sa.String(40), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=True),
        sa.Column("algorithm_type", sa.String(80), nullable=False),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", "version", name="uq_adaptive_insight_model_name_version"),
    )
    op.create_index("ix_adaptive_insight_models_scope", "adaptive_insight_model_versions", ["organization_id", "scope_type", "scope_id", "status"])

    op.create_table(
        "recommendation_simulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=True),
        sa.Column("profiles_count", sa.Integer(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_simulations_org_created", "recommendation_simulations", ["organization_id", "created_at"])

    op.create_table(
        "controlled_experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("primary_metric", sa.String(80), nullable=False),
        sa.Column("metric_direction", sa.String(30), nullable=False),
        sa.Column("assignment_strategy", sa.String(40), nullable=False),
        sa.Column("strategies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_per_strategy", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_controlled_experiments_status", "controlled_experiments", ["organization_id", "status", "created_at"])

    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_key", sa.String(30), nullable=False),
        sa.Column("assignment_strategy", sa.String(40), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "experiment_id", "participant_id", name="uq_experiment_participant"),
    )
    op.create_index("ix_experiment_assignments_strategy", "experiment_assignments", ["organization_id", "experiment_id", "strategy_key"])

    op.create_table(
        "experiment_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("strategy_key", sa.String(30), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiment_observations_strategy", "experiment_observations", ["organization_id", "experiment_id", "strategy_key"])


def downgrade() -> None:
    op.drop_index("ix_experiment_observations_strategy", table_name="experiment_observations")
    op.drop_table("experiment_observations")
    op.drop_index("ix_experiment_assignments_strategy", table_name="experiment_assignments")
    op.drop_table("experiment_assignments")
    op.drop_index("ix_controlled_experiments_status", table_name="controlled_experiments")
    op.drop_table("controlled_experiments")
    op.drop_index("ix_recommendation_simulations_org_created", table_name="recommendation_simulations")
    op.drop_table("recommendation_simulations")
    op.drop_index("ix_adaptive_insight_models_scope", table_name="adaptive_insight_model_versions")
    op.drop_table("adaptive_insight_model_versions")
    op.drop_index("ix_material_effectiveness_classification", table_name="material_effectiveness_metrics")
    op.drop_table("material_effectiveness_metrics")
    op.drop_index("ix_intervention_outcomes_material", table_name="intervention_outcomes")
    op.drop_index("ix_intervention_outcomes_student_node", table_name="intervention_outcomes")
    op.drop_table("intervention_outcomes")
