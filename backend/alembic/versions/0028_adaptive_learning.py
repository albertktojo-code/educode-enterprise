"""Adaptive learning profiles, explainable recommendations and learning paths.

Revision ID: 0028_adaptive_learning
Revises: 0027_infra_continuity
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0028_adaptive_learning"
down_revision: str | None = "0027_infra_continuity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "adaptive_model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("rules_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("thresholds_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("minimum_evidence_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_adaptive_model_org_code_version"),
    )
    op.create_index("ix_adaptive_model_org", "adaptive_model_versions", ["organization_id"])
    op.create_index("ix_adaptive_model_code", "adaptive_model_versions", ["code"])
    op.create_index("ix_adaptive_model_status", "adaptive_model_versions", ["status"])

    op.create_table(
        "adaptive_learning_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("preferred_formats", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("accessibility_preferences", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("teacher_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("last_calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "student_id", name="uq_adaptive_profile_org_student"),
    )
    op.create_index("ix_adaptive_profile_org", "adaptive_learning_profiles", ["organization_id"])
    op.create_index("ix_adaptive_profile_student", "adaptive_learning_profiles", ["student_id"])
    op.create_index("ix_adaptive_profile_status", "adaptive_learning_profiles", ["status"])

    op.create_table(
        "skill_prerequisites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("dimension_type", sa.String(30), nullable=False),
        sa.Column("dimension_code", sa.String(120), nullable=False),
        sa.Column("prerequisite_type", sa.String(30), nullable=False),
        sa.Column("prerequisite_code", sa.String(120), nullable=False),
        sa.Column("relation_type", sa.String(40), nullable=False, server_default="required"),
        sa.Column("minimum_mastery", sa.Float(), nullable=False, server_default="0.65"),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "dimension_type", "dimension_code", "prerequisite_type", "prerequisite_code",
            name="uq_skill_prerequisite_relation",
        ),
    )
    op.create_index("ix_skill_prereq_org", "skill_prerequisites", ["organization_id"])
    op.create_index("ix_skill_prereq_dimension", "skill_prerequisites", ["dimension_type", "dimension_code"])
    op.create_index("ix_skill_prereq_code", "skill_prerequisites", ["prerequisite_code"])

    op.create_table(
        "adaptive_skill_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("dimension_type", sa.String(30), nullable=False),
        sa.Column("dimension_code", sa.String(120), nullable=False),
        sa.Column("mastery_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mastery_level", sa.String(40), nullable=False, server_default="not_assessed"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_level", sa.String(30), nullable=False, server_default="insufficient"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weighted_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weighted_possible", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trend", sa.String(30), nullable=False, server_default="stable"),
        sa.Column("evidence_snapshot", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("calculation_explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("first_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["adaptive_learning_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_version_id"], ["adaptive_model_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "student_id", "dimension_type", "dimension_code", name="uq_adaptive_skill_state_dimension"),
    )
    op.create_index("ix_adaptive_skill_org", "adaptive_skill_states", ["organization_id"])
    op.create_index("ix_adaptive_skill_student", "adaptive_skill_states", ["student_id"])
    op.create_index("ix_adaptive_skill_dimension", "adaptive_skill_states", ["dimension_type", "dimension_code"])
    op.create_index("ix_adaptive_skill_level", "adaptive_skill_states", ["mastery_level"])
    op.create_index("ix_adaptive_skill_model", "adaptive_skill_states", ["model_version_id"])

    op.create_table(
        "adaptive_student_groups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_dimension_type", sa.String(30), nullable=False, server_default="skill"),
        sa.Column("target_dimension_code", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("is_visible_to_students", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_group_org", "adaptive_student_groups", ["organization_id"])
    op.create_index("ix_adaptive_group_classroom", "adaptive_student_groups", ["classroom_id"])
    op.create_index("ix_adaptive_group_status", "adaptive_student_groups", ["status"])

    op.create_table(
        "adaptive_group_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("reason_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("added_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["adaptive_student_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "student_id", name="uq_adaptive_group_student"),
    )
    op.create_index("ix_adaptive_group_member_org", "adaptive_group_members", ["organization_id"])
    op.create_index("ix_adaptive_group_member_group", "adaptive_group_members", ["group_id"])
    op.create_index("ix_adaptive_group_member_student", "adaptive_group_members", ["student_id"])

    op.create_table(
        "adaptive_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("skill_state_id", sa.Uuid(), nullable=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("target_dimension_type", sa.String(30), nullable=False),
        sa.Column("target_dimension_code", sa.String(120), nullable=False),
        sa.Column("target_mastery", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_summary", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("proposed_materials", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by_ai", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["adaptive_student_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["skill_state_id"], ["adaptive_skill_states.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_version_id"], ["adaptive_model_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_rec_org", "adaptive_recommendations", ["organization_id"])
    op.create_index("ix_adaptive_rec_student", "adaptive_recommendations", ["student_id"])
    op.create_index("ix_adaptive_rec_status", "adaptive_recommendations", ["status"])
    op.create_index("ix_adaptive_rec_target", "adaptive_recommendations", ["target_dimension_code"])
    op.create_index("ix_adaptive_rec_model", "adaptive_recommendations", ["model_version_id"])

    op.create_table(
        "adaptive_recommendation_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("dimension_type", sa.String(30), nullable=False),
        sa.Column("dimension_code", sa.String(120), nullable=False),
        sa.Column("observed_score", sa.Float(), nullable=True),
        sa.Column("evidence_weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["adaptive_recommendations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_rec_evidence_org", "adaptive_recommendation_evidence", ["organization_id"])
    op.create_index("ix_adaptive_rec_evidence_rec", "adaptive_recommendation_evidence", ["recommendation_id"])

    op.create_table(
        "adaptive_learning_paths",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("recommendation_id", sa.Uuid(), nullable=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("path_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("target_dimension_type", sa.String(30), nullable=False),
        sa.Column("target_dimension_code", sa.String(120), nullable=False),
        sa.Column("target_mastery", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("minimum_evidence_count", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("settings_json", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["adaptive_student_groups.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["adaptive_recommendations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_version_id"], ["adaptive_model_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_path_org", "adaptive_learning_paths", ["organization_id"])
    op.create_index("ix_adaptive_path_student", "adaptive_learning_paths", ["student_id"])
    op.create_index("ix_adaptive_path_status", "adaptive_learning_paths", ["status"])
    op.create_index("ix_adaptive_path_target", "adaptive_learning_paths", ["target_dimension_code"])

    op.create_table(
        "adaptive_path_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("path_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("content_reference", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(30), nullable=False, server_default="locked"),
        sa.Column("advancement_rule", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["path_id"], ["adaptive_learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("path_id", "position", name="uq_adaptive_path_step_position"),
    )
    op.create_index("ix_adaptive_step_org", "adaptive_path_steps", ["organization_id"])
    op.create_index("ix_adaptive_step_path", "adaptive_path_steps", ["path_id"])
    op.create_index("ix_adaptive_step_assignment", "adaptive_path_steps", ["assignment_id"])
    op.create_index("ix_adaptive_step_status", "adaptive_path_steps", ["status"])

    op.create_table(
        "adaptive_review_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("path_id", sa.Uuid(), nullable=True),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("dimension_type", sa.String(30), nullable=False),
        sa.Column("dimension_code", sa.String(120), nullable=False),
        sa.Column("review_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["path_id"], ["adaptive_learning_paths.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["step_id"], ["adaptive_path_steps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_review_org", "adaptive_review_schedules", ["organization_id"])
    op.create_index("ix_adaptive_review_student", "adaptive_review_schedules", ["student_id"])
    op.create_index("ix_adaptive_review_path", "adaptive_review_schedules", ["path_id"])
    op.create_index("ix_adaptive_review_due", "adaptive_review_schedules", ["scheduled_for"])
    op.create_index("ix_adaptive_review_status", "adaptive_review_schedules", ["status"])

    op.create_table(
        "adaptive_path_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("path_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("dimension_type", sa.String(30), nullable=False),
        sa.Column("dimension_code", sa.String(120), nullable=False),
        sa.Column("mastery_before", sa.Float(), nullable=True),
        sa.Column("mastery_after", sa.Float(), nullable=True),
        sa.Column("mastery_delta", sa.Float(), nullable=True),
        sa.Column("evidence_before", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("interpretation", sa.Text(), nullable=False, server_default=""),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["path_id"], ["adaptive_learning_paths.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_outcome_org", "adaptive_path_outcomes", ["organization_id"])
    op.create_index("ix_adaptive_outcome_path", "adaptive_path_outcomes", ["path_id"])
    op.create_index("ix_adaptive_outcome_student", "adaptive_path_outcomes", ["student_id"])

    op.create_table(
        "adaptive_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("student_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adaptive_audit_org", "adaptive_audit_events", ["organization_id"])
    op.create_index("ix_adaptive_audit_actor", "adaptive_audit_events", ["actor_user_id"])
    op.create_index("ix_adaptive_audit_student", "adaptive_audit_events", ["student_id"])
    op.create_index("ix_adaptive_audit_action", "adaptive_audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("adaptive_audit_events")
    op.drop_table("adaptive_path_outcomes")
    op.drop_table("adaptive_review_schedules")
    op.drop_table("adaptive_path_steps")
    op.drop_table("adaptive_learning_paths")
    op.drop_table("adaptive_recommendation_evidence")
    op.drop_table("adaptive_recommendations")
    op.drop_table("adaptive_group_members")
    op.drop_table("adaptive_student_groups")
    op.drop_table("adaptive_skill_states")
    op.drop_table("skill_prerequisites")
    op.drop_table("adaptive_learning_profiles")
    op.drop_table("adaptive_model_versions")
