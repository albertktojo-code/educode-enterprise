"""Núcleo de Avaliação Integrada.

Revision ID: 0020_integrated_assessment_core
Revises: 0019_statistical_lab_advanced
Create Date: 2026-07-22
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision = "0020_integrated_assessment_core"
down_revision = "0019_statistical_lab_advanced"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_EMPTY = sa.text("'{}'::json")
JSON_LIST = sa.text("'[]'::json")
NOW = sa.text("now()")

def upgrade() -> None:
    op.create_table("assessments",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("assessment_type", sa.String(60), server_default="assessment", nullable=False),
        sa.Column("source_type", sa.String(30), server_default="teacher", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("current_version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False), sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("approved_by_user_id", sa.Uuid()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False), sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"],ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"],["users.id"],ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"],["users.id"],ondelete="SET NULL"))
    for col in ("organization_id","created_by_user_id"): op.create_index(f"ix_assessments_{col}","assessments",[col])

    op.create_table("assessment_versions",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("assessment_id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),
        sa.Column("version_number",sa.Integer(),nullable=False),sa.Column("instructions",sa.Text(),server_default="",nullable=False),
        sa.Column("scoring_policy",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("delivery_defaults",sa.JSON(),server_default=JSON_EMPTY,nullable=False),
        sa.Column("source_metadata",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("content_checksum",sa.String(64),server_default="",nullable=False),
        sa.Column("is_locked",sa.Boolean(),server_default=sa.false(),nullable=False),sa.Column("published_at",sa.DateTime(timezone=True)),
        sa.Column("created_by_user_id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),
        sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("assessment_id","version_number",name="uq_assessment_version_number"),
        sa.ForeignKeyConstraint(["assessment_id"],["assessments.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"],ondelete="RESTRICT"))
    for col in ("assessment_id","organization_id","created_by_user_id"): op.create_index(f"ix_assessment_versions_{col}","assessment_versions",[col])

    op.create_table("question_bank_items",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("title",sa.String(240),server_default="",nullable=False),
        sa.Column("item_type",sa.String(40),nullable=False),sa.Column("prompt",sa.Text(),nullable=False),sa.Column("options",sa.JSON(),server_default=JSON_LIST,nullable=False),
        sa.Column("answer_key",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("explanation",sa.Text(),server_default="",nullable=False),
        sa.Column("points",sa.Float(),server_default="1",nullable=False),sa.Column("difficulty",sa.String(40),server_default="medium",nullable=False),
        sa.Column("curriculum_skill_codes",sa.JSON(),server_default=JSON_LIST,nullable=False),sa.Column("ct_pillar_codes",sa.JSON(),server_default=JSON_LIST,nullable=False),
        sa.Column("source_type",sa.String(30),server_default="teacher",nullable=False),sa.Column("source_metadata",sa.JSON(),server_default=JSON_EMPTY,nullable=False),
        sa.Column("ai_generation_metadata",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("requires_manual_grading",sa.Boolean(),server_default=sa.false(),nullable=False),
        sa.Column("status",sa.String(30),server_default="draft",nullable=False),sa.Column("version_number",sa.Integer(),server_default="1",nullable=False),
        sa.Column("content_checksum",sa.String(64),server_default="",nullable=False),sa.Column("external_reference",sa.String(240)),
        sa.Column("created_by_user_id",sa.Uuid(),nullable=False),sa.Column("reviewed_by_user_id",sa.Uuid()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"],ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"],["users.id"],ondelete="SET NULL"))
    for col in ("organization_id","external_reference","created_by_user_id"): op.create_index(f"ix_question_bank_items_{col}","question_bank_items",[col])

    op.create_table("assessment_version_items",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("assessment_version_id",sa.Uuid(),nullable=False),sa.Column("question_bank_item_id",sa.Uuid(),nullable=False),
        sa.Column("position",sa.Integer(),nullable=False),sa.Column("points_override",sa.Float()),sa.Column("item_snapshot",sa.JSON(),server_default=JSON_EMPTY,nullable=False),
        sa.Column("snapshot_checksum",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_version_id","position",name="uq_assessment_version_item_position"),
        sa.ForeignKeyConstraint(["assessment_version_id"],["assessment_versions.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_bank_item_id"],["question_bank_items.id"],ondelete="RESTRICT"))
    op.create_index("ix_assessment_version_items_assessment_version_id","assessment_version_items",["assessment_version_id"])
    op.create_index("ix_assessment_version_items_question_bank_item_id","assessment_version_items",["question_bank_item_id"])

    op.create_table("assessment_delivery_links",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("assessment_id",sa.Uuid(),nullable=False),
        sa.Column("assessment_version_id",sa.Uuid(),nullable=False),sa.Column("material_assignment_id",sa.Uuid(),nullable=False),sa.Column("created_by_user_id",sa.Uuid(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("material_assignment_id",name="uq_assessment_delivery_assignment"),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["assessment_id"],["assessments.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_version_id"],["assessment_versions.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["material_assignment_id"],["material_assignments.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"],ondelete="RESTRICT"))
    for col in ("organization_id","assessment_id","assessment_version_id","material_assignment_id"): op.create_index(f"ix_assessment_delivery_links_{col}","assessment_delivery_links",[col])

    op.create_table("assessment_outcome_evidence",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("assessment_version_id",sa.Uuid()),
        sa.Column("assignment_id",sa.Uuid(),nullable=False),sa.Column("attempt_id",sa.Uuid(),nullable=False),sa.Column("answer_id",sa.Uuid(),nullable=False),
        sa.Column("question_id",sa.Uuid(),nullable=False),sa.Column("student_id",sa.Uuid(),nullable=False),sa.Column("dimension_type",sa.String(30),nullable=False),
        sa.Column("dimension_code",sa.String(120),nullable=False),sa.Column("score_obtained",sa.Float(),server_default="0",nullable=False),sa.Column("score_possible",sa.Float(),server_default="0",nullable=False),
        sa.Column("evidence_weight",sa.Float(),server_default="1",nullable=False),sa.Column("calculation_version",sa.Integer(),server_default="1",nullable=False),
        sa.Column("source_snapshot",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("calculated_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),
        sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("answer_id","dimension_type","dimension_code",name="uq_assessment_outcome_answer_dimension"),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["assessment_version_id"],["assessment_versions.id"],ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignment_id"],["material_assignments.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["attempt_id"],["student_attempts.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["answer_id"],["student_answers.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["question_id"],["assignment_questions.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"],["users.id"],ondelete="CASCADE"))
    for col in ("organization_id","assessment_version_id","assignment_id","attempt_id","answer_id","question_id","student_id","dimension_code"): op.create_index(f"ix_assessment_outcome_evidence_{col}","assessment_outcome_evidence",[col])

    op.create_table("assessment_import_jobs",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("source_format",sa.String(30),nullable=False),
        sa.Column("file_name",sa.String(255),server_default="",nullable=False),sa.Column("status",sa.String(30),server_default="pending",nullable=False),
        sa.Column("field_mapping",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("rows_snapshot",sa.JSON(),server_default=JSON_LIST,nullable=False),
        sa.Column("validation_summary",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("imported_assessment_id",sa.Uuid()),
        sa.Column("created_by_user_id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),sa.Column("completed_at",sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["imported_assessment_id"],["assessments.id"],ondelete="SET NULL"),sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"],ondelete="RESTRICT"))
    for col in ("organization_id","created_by_user_id"): op.create_index(f"ix_assessment_import_jobs_{col}","assessment_import_jobs",[col])

    op.create_table("assessment_connectors",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("name",sa.String(160),nullable=False),
        sa.Column("connector_type",sa.String(40),nullable=False),sa.Column("status",sa.String(30),server_default="inactive",nullable=False),
        sa.Column("public_configuration",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("external_system_key",sa.String(120)),
        sa.Column("created_by_user_id",sa.Uuid(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["created_by_user_id"],["users.id"],ondelete="RESTRICT"))
    op.create_index("ix_assessment_connectors_organization_id","assessment_connectors",["organization_id"])

    op.create_table("assessment_audit_events",
        sa.Column("id",sa.Uuid(),nullable=False),sa.Column("organization_id",sa.Uuid(),nullable=False),sa.Column("assessment_id",sa.Uuid()),
        sa.Column("assessment_version_id",sa.Uuid()),sa.Column("assignment_id",sa.Uuid()),sa.Column("action",sa.String(80),nullable=False),
        sa.Column("details",sa.JSON(),server_default=JSON_EMPTY,nullable=False),sa.Column("performed_by_user_id",sa.Uuid(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=NOW,nullable=False),sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"],["organizations.id"],ondelete="CASCADE"),sa.ForeignKeyConstraint(["assessment_id"],["assessments.id"],ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assessment_version_id"],["assessment_versions.id"],ondelete="SET NULL"),sa.ForeignKeyConstraint(["assignment_id"],["material_assignments.id"],ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["performed_by_user_id"],["users.id"],ondelete="RESTRICT"))
    for col in ("organization_id","assessment_id","action","performed_by_user_id"): op.create_index(f"ix_assessment_audit_events_{col}","assessment_audit_events",[col])

def downgrade() -> None:
    for table in ("assessment_audit_events","assessment_connectors","assessment_import_jobs","assessment_outcome_evidence","assessment_delivery_links","assessment_version_items","question_bank_items","assessment_versions","assessments"):
        op.drop_table(table)
