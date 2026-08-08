"""student portfolio curation and reflections

Revision ID: 0057_student_portfolio
Revises: 0056_anime_audiovisual
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0057_student_portfolio"
down_revision: str | None = "0056_anime_audiovisual"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_portfolio_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_user_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("title_snapshot", sa.String(length=240), nullable=False),
        sa.Column("assignment_type_snapshot", sa.String(length=40), nullable=False),
        sa.Column("percentage_snapshot", sa.Float(), nullable=False),
        sa.Column("reflection", sa.Text(), server_default="", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("completed_at_snapshot", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "char_length(reflection) <= 2000", name="ck_student_portfolio_reflection_length"
        ),
        sa.CheckConstraint("revision >= 1", name="ck_student_portfolio_revision"),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["material_assignments.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["attempt_id"], ["student_attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "student_user_id",
            "assignment_id",
            name="uq_student_portfolio_assignment",
        ),
    )
    op.create_index(
        "ix_student_portfolio_owner_created",
        "student_portfolio_entries",
        ["organization_id", "student_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_portfolio_owner_created", table_name="student_portfolio_entries")
    op.drop_table("student_portfolio_entries")
