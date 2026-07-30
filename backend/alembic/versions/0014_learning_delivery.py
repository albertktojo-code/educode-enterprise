"""Learning delivery, student attempts and basic progress tracking.

Revision ID: 0014_learning_delivery
Revises: 0013_teacher_studio_canvas
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_learning_delivery"
down_revision: str | None = "0013_teacher_studio_canvas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

assignment_status = postgresql.ENUM(
    "DRAFT", "SCHEDULED", "PUBLISHED", "CLOSED", "CANCELED", "ARCHIVED",
    name="assignment_status", create_type=False,
)
assignment_type = postgresql.ENUM(
    "READING", "READING_EXERCISE", "ACTIVITY", "QUIZ", "ASSESSMENT",
    "PRETEST", "POSTTEST", "REINFORCEMENT", "CHALLENGE",
    name="assignment_type", create_type=False,
)
recipient_type = postgresql.ENUM(
    "CLASSROOM", "USER", name="assignment_recipient_type", create_type=False
)
recipient_status = postgresql.ENUM(
    "ACTIVE", "REMOVED", name="assignment_recipient_status", create_type=False
)
feedback_policy = postgresql.ENUM(
    "IMMEDIATE", "AFTER_SUBMISSION", "AFTER_DUE_DATE", "MANUAL_RELEASE",
    name="feedback_policy", create_type=False,
)
answer_key_policy = postgresql.ENUM(
    "NEVER", "AFTER_SUBMISSION", "AFTER_DUE_DATE", "MANUAL_RELEASE",
    name="answer_key_policy", create_type=False,
)
question_type = postgresql.ENUM(
    "MULTIPLE_CHOICE", "TRUE_FALSE", "SHORT_TEXT", "NUMERIC", "MULTIPLE_SELECT",
    "ORDERING", "MATCHING", "ESSAY",
    name="assignment_question_type", create_type=False,
)
attempt_status = postgresql.ENUM(
    "IN_PROGRESS", "SUBMITTED", "GRADED", "REOPENED", "CANCELED",
    name="student_attempt_status", create_type=False,
)
notification_status = postgresql.ENUM(
    "UNREAD", "READ", "ARCHIVED", name="notification_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    enum_types = (
        assignment_status,
        assignment_type,
        recipient_type,
        recipient_status,
        feedback_policy,
        answer_key_policy,
        question_type,
        attempt_status,
        notification_status,
    )
    for enum_type in enum_types:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "material_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("assignment_type", assignment_type, nullable=False),
        sa.Column("status", assignment_status, nullable=False),
        sa.Column("material_snapshot", sa.JSON(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_limit_minutes", sa.Integer(), nullable=True),
        sa.Column("maximum_attempts", sa.Integer(), nullable=False),
        sa.Column("maximum_score", sa.Float(), nullable=False),
        sa.Column("minimum_score", sa.Float(), nullable=True),
        sa.Column("feedback_policy", feedback_policy, nullable=False),
        sa.Column("answer_key_policy", answer_key_policy, nullable=False),
        sa.Column("randomize_questions", sa.Boolean(), nullable=False),
        sa.Column("randomize_options", sa.Boolean(), nullable=False),
        sa.Column("allow_pause", sa.Boolean(), nullable=False),
        sa.Column("allow_late_submission", sa.Boolean(), nullable=False),
        sa.Column("late_penalty_percent", sa.Float(), nullable=False),
        sa.Column("show_result_immediately", sa.Boolean(), nullable=False),
        sa.Column("results_released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["pedagogical_packages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "package_id", "created_by_user_id"):
        op.create_index(f"ix_material_assignments_{column}", "material_assignments", [column])
    op.create_index(
        "ix_material_assignments_status_due",
        "material_assignments",
        ["status", "due_at"],
    )

    op.create_table(
        "assignment_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_type", recipient_type, nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("status", recipient_status, nullable=False),
        sa.Column("available_from_override", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at_override", sa.DateTime(timezone=True), nullable=True),
        sa.Column("maximum_attempts_override", sa.Integer(), nullable=True),
        sa.Column("time_limit_minutes_override", sa.Integer(), nullable=True),
        sa.Column("accommodations", sa.JSON(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(recipient_type = 'CLASSROOM' AND classroom_id IS NOT NULL AND user_id IS NULL) OR "
            "(recipient_type = 'USER' AND user_id IS NOT NULL AND classroom_id IS NULL)",
            name="ck_assignment_recipient_target",
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "classroom_id",
            "user_id",
            name="uq_assignment_recipient_target",
        ),
    )
    for column in ("assignment_id", "classroom_id", "user_id"):
        op.create_index(f"ix_assignment_recipients_{column}", "assignment_recipients", [column])

    op.create_table(
        "assignment_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("package_material_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("question_type", question_type, nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("answer_key", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=False),
        sa.Column("curriculum_skill_codes", sa.JSON(), nullable=False),
        sa.Column("ct_pillar_codes", sa.JSON(), nullable=False),
        sa.Column("source_references", sa.JSON(), nullable=False),
        sa.Column("manual_grading", sa.Boolean(), nullable=False),
        sa.Column("shuffle_options", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["package_material_id"],
            ["package_materials.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assignment_id", "position", name="uq_assignment_question_position"),
    )
    op.create_index(
        "ix_assignment_questions_assignment_id",
        "assignment_questions",
        ["assignment_id"],
    )
    op.create_index(
        "ix_assignment_questions_package_material_id",
        "assignment_questions",
        ["package_material_id"],
    )

    op.create_table(
        "student_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", attempt_status, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("grading_complete", sa.Boolean(), nullable=False),
        sa.Column("is_late", sa.Boolean(), nullable=False),
        sa.Column("late_penalty_applied", sa.Float(), nullable=False),
        sa.Column("time_limit_minutes_snapshot", sa.Integer(), nullable=True),
        sa.Column("maximum_attempts_snapshot", sa.Integer(), nullable=False),
        sa.Column("randomization_state", sa.JSON(), nullable=False),
        sa.Column("autosave_revision", sa.Integer(), nullable=False),
        sa.Column("reopened_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reopened_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reopened_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assignment_id",
            "student_id",
            "attempt_number",
            name="uq_student_assignment_attempt",
        ),
    )
    for column in ("organization_id", "assignment_id", "student_id", "reopened_by_user_id"):
        op.create_index(f"ix_student_attempts_{column}", "student_attempts", [column])
    op.create_index(
        "ix_student_attempts_student_status",
        "student_attempts",
        ["student_id", "status"],
    )

    op.create_table(
        "student_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("answer_payload", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("awarded_score", sa.Float(), nullable=False),
        sa.Column("response_time_seconds", sa.Integer(), nullable=False),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("corrected_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["attempt_id"], ["student_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["assignment_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["corrected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question_answer"),
    )
    for column in ("attempt_id", "question_id", "corrected_by_user_id"):
        op.create_index(f"ix_student_answers_{column}", "student_answers", [column])

    op.create_table(
        "learning_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=True),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attempt_id"], ["student_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["assignment_questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    event_index_columns = (
        "organization_id",
        "student_id",
        "assignment_id",
        "attempt_id",
        "question_id",
        "event_type",
        "occurred_at",
    )
    for column in event_index_columns:
        op.create_index(f"ix_learning_events_{column}", "learning_events", [column])

    op.create_table(
        "user_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("notification_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("action_path", sa.String(length=500), nullable=True),
        sa.Column("status", notification_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "user_id", "assignment_id"):
        op.create_index(f"ix_user_notifications_{column}", "user_notifications", [column])
    op.create_index(
        "ix_user_notifications_user_status",
        "user_notifications",
        ["user_id", "status"],
    )


def downgrade() -> None:
    for table in (
        "user_notifications",
        "learning_events",
        "student_answers",
        "student_attempts",
        "assignment_questions",
        "assignment_recipients",
        "material_assignments",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for enum_type in (
        notification_status,
        attempt_status,
        question_type,
        answer_key_policy,
        feedback_policy,
        recipient_status,
        recipient_type,
        assignment_type,
        assignment_status,
    ):
        enum_type.drop(bind, checkfirst=True)
