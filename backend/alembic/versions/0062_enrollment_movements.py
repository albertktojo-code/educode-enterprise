"""enrollment renewals and transfer requests

Revision ID: 0062_enrollment_movements
Revises: 0061_enrollment_contracts
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0062_enrollment_movements"
down_revision: str | None = "0061_enrollment_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        "enrollment_renewal_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("target_classroom_id", sa.Uuid(), nullable=False),
        sa.Column("target_academic_year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), server_default="submitted", nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("review_note", sa.Text(), server_default="", nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("result_application_id", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'cancelled')",
            name="ck_enrollment_renewal_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["student_enrollments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_classroom_id"], ["classrooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["result_application_id"], ["student_enrollment_applications.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "enrollment_id", "target_academic_year", name="uq_enrollment_renewal_year"
        ),
    )
    op.create_index(
        "ix_enrollment_renewals_org_status",
        "enrollment_renewal_requests",
        ["organization_id", "status", "created_at"],
    )
    op.create_table(
        "enrollment_transfer_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("transfer_type", sa.String(20), nullable=False),
        sa.Column("destination_classroom_id", sa.Uuid()),
        sa.Column("destination_name", sa.String(180), server_default="", nullable=False),
        sa.Column("status", sa.String(20), server_default="submitted", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("review_note", sa.Text(), server_default="", nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("result_application_id", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint(
            "transfer_type IN ('internal', 'external')", name="ck_enrollment_transfer_type"
        ),
        sa.CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'cancelled')",
            name="ck_enrollment_transfer_status",
        ),
        sa.CheckConstraint(
            "(transfer_type = 'internal' AND destination_classroom_id IS NOT NULL) OR "
            "(transfer_type = 'external' AND destination_name <> '')",
            name="ck_enrollment_transfer_destination",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["student_enrollments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["destination_classroom_id"], ["classrooms.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["result_application_id"], ["student_enrollment_applications.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enrollment_transfers_org_status",
        "enrollment_transfer_requests",
        ["organization_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_enrollment_transfers_org_status", table_name="enrollment_transfer_requests")
    op.drop_table("enrollment_transfer_requests")
    op.drop_index("ix_enrollment_renewals_org_status", table_name="enrollment_renewal_requests")
    op.drop_table("enrollment_renewal_requests")
