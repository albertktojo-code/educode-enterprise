"""Sprint 15 assessment hub.

Revision ID: 0031_assessment_hub
Revises: 0030_adaptive_insights
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0031_assessment_hub"
down_revision: str | None = "0030_adaptive_insights"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "assessment_hub_question_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("school_year", sa.String(60), nullable=True),
        sa.Column("source_type", sa.String(40), nullable=False, server_default="INTERNAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_assessment_question_code"),
    )
    op.create_index("ix_assessment_questions_catalog", "assessment_hub_question_items", ["organization_id", "status", "subject", "school_year"])

    op.create_table(
        "assessment_hub_question_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("question_type", sa.String(40), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("correct_answer", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("rubric", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("predicted_difficulty", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("accessibility", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "question_id", "version", name="uq_assessment_question_version"),
    )
    op.create_index("ix_assessment_question_versions_status", "assessment_hub_question_versions", ["organization_id", "status", "question_type"])

    op.create_table(
        "assessment_hub_question_skills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("skill_type", sa.String(40), nullable=False),
        sa.Column("skill_code", sa.String(80), nullable=False),
        sa.Column("skill_name", sa.String(220), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "question_version_id", "skill_type", "skill_code", name="uq_assessment_question_skill"),
    )
    op.create_index("ix_assessment_question_skills_code", "assessment_hub_question_skills", ["organization_id", "skill_type", "skill_code"])

    op.create_table(
        "assessment_hub_blueprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("assessment_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("selection_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("delivery_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scoring_settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("published_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_assessment_blueprint_version"),
    )
    op.create_index("ix_assessment_blueprints_status", "assessment_hub_blueprints", ["organization_id", "status", "assessment_type"])

    op.create_table(
        "assessment_hub_external_instruments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("version", sa.String(60), nullable=False),
        sa.Column("instrument_type", sa.String(60), nullable=False),
        sa.Column("authorship", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("license_status", sa.String(60), nullable=False, server_default="REQUIRES_PERMISSION"),
        sa.Column("permission_reference", sa.Text(), nullable=True),
        sa.Column("administration_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scoring_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("interpretation_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_assessment_external_instrument"),
    )
    op.create_index("ix_assessment_external_instruments_type", "assessment_hub_external_instruments", ["organization_id", "instrument_type", "status"])

    op.create_table(
        "assessment_hub_instrument_dimensions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("minimum_score", sa.Float(), nullable=True),
        sa.Column("maximum_score", sa.Float(), nullable=True),
        sa.Column("interpretation", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "instrument_id", "code", name="uq_assessment_instrument_dimension"),
    )

    op.create_table(
        "assessment_hub_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("blueprint_id", sa.Uuid(), nullable=True),
        sa.Column("external_instrument_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="CREATED"),
        sa.Column("question_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("maximum_score", sa.Float(), nullable=True),
        sa.Column("percentage_score", sa.Float(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_attempts_student", "assessment_hub_attempts", ["organization_id", "student_id", "status", "started_at"])
    op.create_index("ix_assessment_attempts_blueprint", "assessment_hub_attempts", ["organization_id", "blueprint_id", "status"])

    op.create_table(
        "assessment_hub_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_version_id", sa.Uuid(), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("maximum_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("correction_type", sa.String(30), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("corrected_by_user_id", sa.Uuid(), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "attempt_id", "question_version_id", name="uq_assessment_attempt_response"),
    )
    op.create_index("ix_assessment_responses_review", "assessment_hub_responses", ["organization_id", "requires_human_review", "correction_type"])

    op.create_table(
        "assessment_hub_score_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("previous_score", sa.Float(), nullable=True),
        sa.Column("proposed_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assessment_score_reviews_status", "assessment_hub_score_reviews", ["organization_id", "status", "created_at"])

    op.create_table(
        "assessment_hub_result_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("maximum_score", sa.Float(), nullable=False),
        sa.Column("percentage_score", sa.Float(), nullable=False),
        sa.Column("dimension_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("skill_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("descriptive_interpretation", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scoring_version", sa.String(60), nullable=False, server_default="1.0.0"),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "attempt_id", name="uq_assessment_result_attempt"),
    )
    op.create_index("ix_assessment_results_student", "assessment_hub_result_summaries", ["organization_id", "student_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_assessment_results_student", table_name="assessment_hub_result_summaries")
    op.drop_table("assessment_hub_result_summaries")
    op.drop_index("ix_assessment_score_reviews_status", table_name="assessment_hub_score_reviews")
    op.drop_table("assessment_hub_score_reviews")
    op.drop_index("ix_assessment_responses_review", table_name="assessment_hub_responses")
    op.drop_table("assessment_hub_responses")
    op.drop_index("ix_assessment_attempts_blueprint", table_name="assessment_hub_attempts")
    op.drop_index("ix_assessment_attempts_student", table_name="assessment_hub_attempts")
    op.drop_table("assessment_hub_attempts")
    op.drop_table("assessment_hub_instrument_dimensions")
    op.drop_index("ix_assessment_external_instruments_type", table_name="assessment_hub_external_instruments")
    op.drop_table("assessment_hub_external_instruments")
    op.drop_index("ix_assessment_blueprints_status", table_name="assessment_hub_blueprints")
    op.drop_table("assessment_hub_blueprints")
    op.drop_index("ix_assessment_question_skills_code", table_name="assessment_hub_question_skills")
    op.drop_table("assessment_hub_question_skills")
    op.drop_index("ix_assessment_question_versions_status", table_name="assessment_hub_question_versions")
    op.drop_table("assessment_hub_question_versions")
    op.drop_index("ix_assessment_questions_catalog", table_name="assessment_hub_question_items")
    op.drop_table("assessment_hub_question_items")
