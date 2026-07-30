"""Sprint 15.4 - correction, rubrics, review and feedback.

Revision ID: 0034_review_feedback
Revises: 0033_instrument_governance
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0034_review_feedback"
down_revision: str | None = "0033_instrument_governance"
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
        "assessment_review_rubrics",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope_type", sa.String(40), nullable=False, server_default="QUESTION"),
        sa.Column("scope_id", UUID),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("updated_by_user_id", UUID),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "code", name="uq_review_rubric_code"),
    )
    op.create_index("ix_review_rubrics_status", "assessment_review_rubrics", ["organization_id", "status", "scope_type"])

    op.create_table(
        "assessment_review_rubric_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("rubric_id", UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("maximum_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("criteria", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("score_rules", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("feedback_templates", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("skill_mappings", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("accessibility_settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("published_by_user_id", UUID),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "rubric_id", "version", name="uq_review_rubric_version"),
    )
    op.create_index("ix_review_rubric_versions_status", "assessment_review_rubric_versions", ["organization_id", "status", "rubric_id"])

    op.create_table(
        "assessment_review_assignments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("attempt_id", UUID, nullable=False),
        sa.Column("response_id", UUID, nullable=False),
        sa.Column("question_version_id", UUID, nullable=False),
        sa.Column("rubric_version_id", UUID),
        sa.Column("reviewer_user_id", UUID, nullable=False),
        sa.Column("assigned_by_user_id", UUID, nullable=False),
        sa.Column("review_round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("review_mode", sa.String(30), nullable=False, server_default="SINGLE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("blinded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("context_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "response_id", "reviewer_user_id", "review_round", name="uq_review_assignment_round"),
    )
    op.create_index("ix_review_assignments_queue", "assessment_review_assignments", ["organization_id", "reviewer_user_id", "status", "priority"])
    op.create_index("ix_review_assignments_response", "assessment_review_assignments", ["organization_id", "response_id", "status"])

    op.create_table(
        "assessment_review_criterion_scores",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("assignment_id", UUID, nullable=False),
        sa.Column("criterion_code", sa.String(80), nullable=False),
        sa.Column("criterion_name", sa.String(220), nullable=False),
        sa.Column("awarded_score", sa.Float(), nullable=False),
        sa.Column("maximum_score", sa.Float(), nullable=False),
        sa.Column("level_code", sa.String(80)),
        sa.Column("evidence", sa.Text()),
        sa.Column("comment", sa.Text()),
        sa.Column("skill_scores", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("correction_source", sa.String(30), nullable=False, server_default="HUMAN"),
        sa.Column("reviewer_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "assignment_id", "criterion_code", name="uq_review_criterion_score"),
    )
    op.create_index("ix_review_criterion_scores_assignment", "assessment_review_criterion_scores", ["organization_id", "assignment_id"])

    op.create_table(
        "assessment_review_feedbacks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("assignment_id", UUID),
        sa.Column("attempt_id", UUID, nullable=False),
        sa.Column("response_id", UUID),
        sa.Column("student_id", UUID, nullable=False),
        sa.Column("audience", sa.String(30), nullable=False, server_default="STUDENT"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("feedback_type", sa.String(50), nullable=False, server_default="FORMATIVE"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("strengths", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("improvement_points", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("next_steps", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("question_feedback", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("skill_feedback", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("accessible_variants", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("published_by_user_id", UUID),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_review_feedback_response", "assessment_review_feedbacks", ["organization_id", "response_id", "status", "audience"])
    op.create_index("ix_review_feedback_attempt", "assessment_review_feedbacks", ["organization_id", "attempt_id", "status"])

    op.create_table(
        "assessment_review_appeals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("attempt_id", UUID, nullable=False),
        sa.Column("response_id", UUID),
        sa.Column("student_id", UUID, nullable=False),
        sa.Column("submitted_by_user_id", UUID, nullable=False),
        sa.Column("reason_code", sa.String(50), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("attachments", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("assigned_reviewer_user_id", UUID),
        sa.Column("decision", sa.String(40)),
        sa.Column("decision_justification", sa.Text()),
        sa.Column("decided_by_user_id", UUID),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_review_appeals_queue", "assessment_review_appeals", ["organization_id", "status", "created_at"])
    op.create_index("ix_review_appeals_student", "assessment_review_appeals", ["organization_id", "student_id", "attempt_id"])

    op.create_table(
        "assessment_review_regrades",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("appeal_id", UUID),
        sa.Column("attempt_id", UUID, nullable=False),
        sa.Column("response_id", UUID, nullable=False),
        sa.Column("requested_by_user_id", UUID, nullable=False),
        sa.Column("previous_score", sa.Float()),
        sa.Column("proposed_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Float()),
        sa.Column("maximum_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("applied_by_user_id", UUID),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("score_snapshot_before", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("score_snapshot_after", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
    )
    op.create_index("ix_review_regrades_response", "assessment_review_regrades", ["organization_id", "response_id", "status"])
    op.create_index("ix_review_regrades_attempt", "assessment_review_regrades", ["organization_id", "attempt_id", "created_at"])

    op.create_table(
        "assessment_review_audit_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_user_id", UUID, nullable=False),
        sa.Column("previous_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("new_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("justification", sa.Text()),
        sa.Column("request_id", sa.String(100)),
        *timestamps(),
    )
    op.create_index("ix_review_audit_entity", "assessment_review_audit_events", ["organization_id", "entity_type", "entity_id", "created_at"])
    op.create_index("ix_review_audit_event", "assessment_review_audit_events", ["organization_id", "event_type", "created_at"])


def downgrade() -> None:
    for table in (
        "assessment_review_audit_events",
        "assessment_review_regrades",
        "assessment_review_appeals",
        "assessment_review_feedbacks",
        "assessment_review_criterion_scores",
        "assessment_review_assignments",
        "assessment_review_rubric_versions",
        "assessment_review_rubrics",
    ):
        op.drop_table(table)
