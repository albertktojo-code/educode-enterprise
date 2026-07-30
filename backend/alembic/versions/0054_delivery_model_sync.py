"""Sincroniza colunas ORM do delivery legado com o schema instalado.

Revision ID: 0054_delivery_model_sync
Revises: 0053_hq_learning_analytics
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0054_delivery_model_sync"
down_revision: str | None = "0053_hq_learning_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "material_assignments",
        sa.Column("assessment_version_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_material_assignments_assessment_version",
        "material_assignments",
        "assessment_versions",
        ["assessment_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_material_assignments_assessment_version_id",
        "material_assignments",
        ["assessment_version_id"],
    )

    op.add_column(
        "assignment_questions",
        sa.Column("question_bank_item_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "assignment_questions",
        sa.Column(
            "source_type",
            sa.String(30),
            nullable=False,
            server_default="teacher",
        ),
    )
    op.add_column(
        "assignment_questions",
        sa.Column(
            "source_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "assignment_questions",
        sa.Column(
            "item_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "assignment_questions",
        sa.Column(
            "item_snapshot_checksum",
            sa.String(64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "assignment_questions",
        sa.Column(
            "is_annulled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "assignment_questions",
        sa.Column("annulment_reason", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "fk_assignment_questions_question_bank_item",
        "assignment_questions",
        "question_bank_items",
        ["question_bank_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_assignment_questions_question_bank_item_id",
        "assignment_questions",
        ["question_bank_item_id"],
    )

    op.add_column(
        "student_attempts",
        sa.Column("assessment_version_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "student_attempts",
        sa.Column(
            "grading_revision",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "student_attempts",
        sa.Column(
            "recalculated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_student_attempts_assessment_version",
        "student_attempts",
        "assessment_versions",
        ["assessment_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_student_attempts_assessment_version_id",
        "student_attempts",
        ["assessment_version_id"],
    )

    for table_name, column_name in (
        ("assignment_questions", "source_type"),
        ("assignment_questions", "source_metadata"),
        ("assignment_questions", "item_version"),
        ("assignment_questions", "item_snapshot_checksum"),
        ("assignment_questions", "is_annulled"),
        ("student_attempts", "grading_revision"),
    ):
        op.alter_column(table_name, column_name, server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_student_attempts_assessment_version_id",
        table_name="student_attempts",
    )
    op.drop_constraint(
        "fk_student_attempts_assessment_version",
        "student_attempts",
        type_="foreignkey",
    )
    op.drop_column("student_attempts", "recalculated_at")
    op.drop_column("student_attempts", "grading_revision")
    op.drop_column("student_attempts", "assessment_version_id")

    op.drop_index(
        "ix_assignment_questions_question_bank_item_id",
        table_name="assignment_questions",
    )
    op.drop_constraint(
        "fk_assignment_questions_question_bank_item",
        "assignment_questions",
        type_="foreignkey",
    )
    op.drop_column("assignment_questions", "annulment_reason")
    op.drop_column("assignment_questions", "is_annulled")
    op.drop_column("assignment_questions", "item_snapshot_checksum")
    op.drop_column("assignment_questions", "item_version")
    op.drop_column("assignment_questions", "source_metadata")
    op.drop_column("assignment_questions", "source_type")
    op.drop_column("assignment_questions", "question_bank_item_id")

    op.drop_index(
        "ix_material_assignments_assessment_version_id",
        table_name="material_assignments",
    )
    op.drop_constraint(
        "fk_material_assignments_assessment_version",
        "material_assignments",
        type_="foreignkey",
    )
    op.drop_column("material_assignments", "assessment_version_id")
