"""Learning Analytics, alertas explicáveis e intervenções pedagógicas.

Revision ID: 0016_learning_analytics
Revises: 0015_storyboard_preview
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016_learning_analytics"
down_revision: str | None = "0015_storyboard_preview"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

alert_severity = postgresql.ENUM(
    "INFO", "ATTENTION", "PRIORITY", name="learning_alert_severity", create_type=False
)
alert_status = postgresql.ENUM(
    "OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED",
    name="learning_alert_status", create_type=False,
)
intervention_type = postgresql.ENUM(
    "REINFORCEMENT", "EXTRA_ATTEMPT", "INDIVIDUAL_FEEDBACK", "ADAPTED_ACTIVITY",
    "EXTENDED_DEADLINE", "ADVANCED_CHALLENGE", "FOLLOW_UP",
    name="learning_intervention_type", create_type=False,
)
intervention_status = postgresql.ENUM(
    "PLANNED", "ACTIVE", "COMPLETED", "CANCELED",
    name="learning_intervention_status", create_type=False,
)
analytics_job_status = postgresql.ENUM(
    "PENDING", "PROCESSING", "COMPLETED", "FAILED",
    name="analytics_job_status", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    enum_types = (
        alert_severity,
        alert_status,
        intervention_type,
        intervention_status,
        analytics_job_status,
    )
    for enum_type in enum_types:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "student_skill_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("skill_code", sa.String(length=80), server_default="", nullable=False),
        sa.Column("ct_pillar_code", sa.String(length=80), server_default="", nullable=False),
        sa.Column("proficiency_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "student_id", "subject_id", "skill_code", "ct_pillar_code",
            name="uq_student_skill_metric_dimension",
        ),
    )
    for column in ("organization_id", "student_id", "subject_id", "skill_code", "ct_pillar_code"):
        op.create_index(f"ix_student_skill_metrics_{column}", "student_skill_metrics", [column])

    op.create_table(
        "classroom_skill_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("skill_code", sa.String(length=80), server_default="", nullable=False),
        sa.Column("ct_pillar_code", sa.String(length=80), server_default="", nullable=False),
        sa.Column("average_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("median_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("student_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "classroom_id", "skill_code", "ct_pillar_code",
            name="uq_classroom_skill_metric_dimension",
        ),
    )
    for column in ("organization_id", "classroom_id", "skill_code", "ct_pillar_code"):
        op.create_index(f"ix_classroom_skill_metrics_{column}", "classroom_skill_metrics", [column])

    op.create_table(
        "assignment_item_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_question_id", sa.Uuid(), nullable=False),
        sa.Column("response_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("omission_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("difficulty_index", sa.Float(), nullable=True),
        sa.Column("discrimination_index", sa.Float(), nullable=True),
        sa.Column("average_response_time", sa.Float(), nullable=True),
        sa.Column("average_awarded_score", sa.Float(), nullable=True),
        sa.Column("distractor_distribution", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_question_id"], ["assignment_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_question_id"),
    )
    for column in ("organization_id", "assignment_id", "assignment_question_id"):
        op.create_index(f"ix_assignment_item_metrics_{column}", "assignment_item_metrics", [column])

    op.create_table(
        "student_progress_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("skill_code", sa.String(length=80), server_default="", nullable=False),
        sa.Column("ct_pillar_code", sa.String(length=80), server_default="", nullable=False),
        sa.Column("proficiency_score", sa.Float(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "student_id", "subject_id", "skill_code", "ct_pillar_code", "recorded_at"):
        op.create_index(f"ix_student_progress_snapshots_{column}", "student_progress_snapshots", [column])

    op.create_table(
        "learning_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("alert_type", sa.String(length=80), nullable=False),
        sa.Column("severity", alert_severity, nullable=False),
        sa.Column("status", alert_status, server_default="OPEN", nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "classroom_id", "student_id", "assignment_id", "alert_type"):
        op.create_index(f"ix_learning_alerts_{column}", "learning_alerts", [column])

    op.create_table(
        "learning_interventions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("teacher_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("alert_id", sa.Uuid(), nullable=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("intervention_type", intervention_type, nullable=False),
        sa.Column("status", intervention_status, server_default="PLANNED", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("expected_outcome", sa.Text(), server_default="", nullable=False),
        sa.Column("result_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["alert_id"], ["learning_alerts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "teacher_id", "classroom_id", "student_id", "alert_id", "assignment_id"):
        op.create_index(f"ix_learning_interventions_{column}", "learning_interventions", [column])

    op.create_table(
        "analytics_refresh_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", analytics_job_status, server_default="PENDING", nullable=False),
        sa.Column("attempt_policy", sa.String(length=30), server_default="best", nullable=False),
        sa.Column("filters", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("result_summary", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_refresh_jobs_organization_id", "analytics_refresh_jobs", ["organization_id"])
    op.create_index("ix_analytics_refresh_jobs_requested_by_user_id", "analytics_refresh_jobs", ["requested_by_user_id"])


def downgrade() -> None:
    op.drop_table("analytics_refresh_jobs")
    op.drop_table("learning_interventions")
    op.drop_table("learning_alerts")
    op.drop_table("student_progress_snapshots")
    op.drop_table("assignment_item_metrics")
    op.drop_table("classroom_skill_metrics")
    op.drop_table("student_skill_metrics")

    bind = op.get_bind()
    for enum_type in (
        analytics_job_status,
        intervention_status,
        intervention_type,
        alert_status,
        alert_severity,
    ):
        enum_type.drop(bind, checkfirst=True)
