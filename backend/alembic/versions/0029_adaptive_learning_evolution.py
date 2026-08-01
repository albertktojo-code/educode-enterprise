"""Adaptive evolution: hints, review, feedback, difficulty, progression and accessibility.

Revision ID: 0029_adaptive_learning_evolution
Revises: 0028_adaptive_learning
Create Date: 2026-07-27

Atenção: o instalador ajusta down_revision automaticamente quando o head da
Sprint 14 possuir outro identificador.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0029_adaptive_learning_evolution"
down_revision: str | None = "0028_adaptive_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "graduated_hints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("learning_node_id", sa.Uuid(), nullable=True),
        sa.Column("level", sa.String(40), nullable=False),
        sa.Column("level_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_format", sa.String(30), nullable=False, server_default="PLAIN_TEXT"),
        sa.Column("release_rule", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("penalty_rule", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "resource_type", "resource_id", "question_id", "level_order", "version",
            name="uq_graduated_hint_scope_level_version",
        ),
    )
    op.create_index("ix_graduated_hints_org_resource", "graduated_hints", ["organization_id", "resource_type", "resource_id"])
    op.create_index("ix_graduated_hints_learning_node_id", "graduated_hints", ["learning_node_id"])

    op.create_table(
        "hint_usages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("graduated_hint_id", sa.Uuid(), nullable=False),
        sa.Column("release_type", sa.String(40), nullable=False),
        sa.Column("release_reason", sa.Text(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("response_after_hint_id", sa.Uuid(), nullable=True),
        sa.Column("result_after_hint", sa.Float(), nullable=True),
        sa.Column("time_to_response_seconds", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.ForeignKeyConstraint(["graduated_hint_id"], ["graduated_hints.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hint_usages_student_attempt", "hint_usages", ["organization_id", "student_id", "attempt_id"])

    op.create_table(
        "spaced_review_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("learning_node_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mastery_score_at_schedule", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_at_schedule", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rule_version", sa.String(40), nullable=False, server_default="1.0.0"),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "student_id", "learning_node_id", name="uq_review_schedule_student_node"),
    )
    op.create_index("ix_review_schedule_due", "spaced_review_schedules", ["organization_id", "status", "scheduled_for"])

    op.create_table(
        "spaced_review_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("learning_node_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.Float(), nullable=True),
        sa.Column("previous_interval_days", sa.Integer(), nullable=False),
        sa.Column("new_interval_days", sa.Integer(), nullable=True),
        sa.Column("rule_applied", sa.String(80), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["spaced_review_schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_events_schedule", "spaced_review_events", ["organization_id", "schedule_id", "created_at"])

    op.create_table(
        "adaptive_feedbacks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=True),
        sa.Column("learning_node_id", sa.Uuid(), nullable=True),
        sa.Column("feedback_type", sa.String(50), nullable=False),
        sa.Column("error_type", sa.String(40), nullable=False),
        sa.Column("mastery_level", sa.String(40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("next_action", sa.String(60), nullable=False),
        sa.Column("rule_version", sa.String(40), nullable=False, server_default="1.0.0"),
        sa.Column("generated_by", sa.String(30), nullable=False, server_default="DETERMINISTIC"),
        sa.Column("review_status", sa.String(30), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("presented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("student_rating", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_feedback_attempt", "adaptive_feedbacks", ["organization_id", "attempt_id"])

    op.create_table(
        "student_difficulty_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("learning_node_id", sa.Uuid(), nullable=False),
        sa.Column("difficulty_score", sa.Float(), nullable=False),
        sa.Column("difficulty_level", sa.String(30), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("previous_score", sa.Float(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("calculation_version", sa.String(40), nullable=False, server_default="1.0.0"),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "student_id", "learning_node_id", name="uq_student_difficulty_node"),
    )

    op.create_table(
        "resource_difficulty_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("learning_node_id", sa.Uuid(), nullable=True),
        sa.Column("predicted_difficulty", sa.Float(), nullable=False),
        sa.Column("observed_difficulty", sa.Float(), nullable=True),
        sa.Column("difficulty_difference", sa.Float(), nullable=True),
        sa.Column("difficulty_classification", sa.String(40), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metrics_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("calculation_version", sa.String(40), nullable=False, server_default="1.0.0"),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "resource_type", "resource_id", "learning_node_id", name="uq_resource_difficulty_scope"),
    )
    op.create_index("ix_resource_difficulty_divergence", "resource_difficulty_metrics", ["organization_id", "difficulty_classification"])

    op.create_table(
        "progression_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope_type", sa.String(40), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=True),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_action", sa.String(50), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("requires_teacher_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", "version", name="uq_progression_rule_name_version"),
    )
    op.create_index("ix_progression_rules_scope", "progression_rules", ["organization_id", "scope_type", "scope_id", "status"])

    op.create_table(
        "progression_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=True),
        sa.Column("learning_node_id", sa.Uuid(), nullable=True),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("decision", sa.String(50), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requires_teacher_approval", sa.Boolean(), nullable=False),
        sa.Column("approval_status", sa.String(30), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["progression_rules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_progression_decisions_student", "progression_decisions", ["organization_id", "student_id", "created_at"])

    op.create_table(
        "accessible_resource_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_resource_type", sa.String(60), nullable=False),
        sa.Column("source_resource_id", sa.Uuid(), nullable=False),
        sa.Column("adaptation_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_reference", sa.String(500), nullable=True),
        sa.Column("accessibility_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("pedagogical_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("pedagogical_equivalence_status", sa.String(50), nullable=False),
        sa.Column("generation_method", sa.String(30), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="NEEDS_REVIEW"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "source_resource_type", "source_resource_id", "adaptation_type", "version",
            name="uq_accessible_resource_version",
        ),
    )
    op.create_index("ix_accessible_versions_source", "accessible_resource_versions", ["organization_id", "source_resource_type", "source_resource_id"])


def downgrade() -> None:
    op.drop_index("ix_accessible_versions_source", table_name="accessible_resource_versions")
    op.drop_table("accessible_resource_versions")
    op.drop_index("ix_progression_decisions_student", table_name="progression_decisions")
    op.drop_table("progression_decisions")
    op.drop_index("ix_progression_rules_scope", table_name="progression_rules")
    op.drop_table("progression_rules")
    op.drop_index("ix_resource_difficulty_divergence", table_name="resource_difficulty_metrics")
    op.drop_table("resource_difficulty_metrics")
    op.drop_table("student_difficulty_profiles")
    op.drop_index("ix_adaptive_feedback_attempt", table_name="adaptive_feedbacks")
    op.drop_table("adaptive_feedbacks")
    op.drop_index("ix_review_events_schedule", table_name="spaced_review_events")
    op.drop_table("spaced_review_events")
    op.drop_index("ix_review_schedule_due", table_name="spaced_review_schedules")
    op.drop_table("spaced_review_schedules")
    op.drop_index("ix_hint_usages_student_attempt", table_name="hint_usages")
    op.drop_table("hint_usages")
    op.drop_index("ix_graduated_hints_learning_node_id", table_name="graduated_hints")
    op.drop_index("ix_graduated_hints_org_resource", table_name="graduated_hints")
    op.drop_table("graduated_hints")
