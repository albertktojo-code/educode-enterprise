"""student certificates

Revision ID: 0058_student_certificates
Revises: 0057_student_portfolio
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0058_student_certificates"
down_revision: str | None = "0057_student_portfolio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_certificates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_user_id", sa.Uuid(), nullable=False),
        sa.Column("issued_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("verification_code", sa.String(32), nullable=False),
        sa.Column("evidence_entry_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column(
            "issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by_user_id", sa.Uuid()),
        sa.Column("revocation_reason", sa.String(300), server_default="", nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verification_code", name="uq_student_certificate_code"),
    )
    op.create_index(
        "ix_student_certificates_owner",
        "student_certificates",
        ["organization_id", "student_user_id", "issued_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_certificates_owner", table_name="student_certificates")
    op.drop_table("student_certificates")
