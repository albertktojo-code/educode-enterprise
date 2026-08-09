"""enrollment contract templates, immutable versions and acceptances

Revision ID: 0061_enrollment_contracts
Revises: 0060_enrollment_documents
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0061_enrollment_contracts"
down_revision: str | None = "0060_enrollment_documents"
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
        "enrollment_contract_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("school_unit_id", sa.Uuid()),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_unit_id"], ["school_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "school_unit_id",
            "code",
            name="uq_enrollment_contract_template_scope",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_enrollment_contract_templates_org_active",
        "enrollment_contract_templates",
        ["organization_id", "is_active"],
    )

    op.create_table(
        "enrollment_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), server_default="generated", nullable=False),
        sa.Column("current_version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("generated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("voided_by_user_id", sa.Uuid()),
        sa.Column("void_reason", sa.Text(), server_default="", nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('generated', 'accepted', 'voided')", name="ck_enrollment_contract_status"
        ),
        sa.CheckConstraint("current_version_number > 0", name="ck_enrollment_contract_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["application_id"], ["student_enrollment_applications.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"], ["enrollment_contract_templates.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["voided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_enrollment_contract_application"),
    )
    op.create_index(
        "ix_enrollment_contracts_org_status",
        "enrollment_contracts",
        ["organization_id", "status", "updated_at"],
    )

    op.create_table(
        "enrollment_contract_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("template_snapshot", sa.Text(), nullable=False),
        sa.Column("rendered_content", sa.Text(), nullable=False),
        sa.Column("variables_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version_number > 0", name="ck_enrollment_contract_version_positive"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["enrollment_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", "version_number", name="uq_enrollment_contract_version"),
    )
    op.create_index(
        "ix_enrollment_contract_versions_org_contract",
        "enrollment_contract_versions",
        ["organization_id", "contract_id", "version_number"],
    )

    op.create_table(
        "enrollment_contract_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("contract_version_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_profile_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("accepted_name", sa.String(180), nullable=False),
        sa.Column("acceptance_hash", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(64), server_default="", nullable=False),
        sa.Column(
            "accepted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["enrollment_contracts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["contract_version_id"], ["enrollment_contract_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["guardian_profile_id"], ["guardian_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", name="uq_enrollment_contract_acceptance"),
    )
    op.create_index(
        "ix_enrollment_contract_acceptances_org_guardian",
        "enrollment_contract_acceptances",
        ["organization_id", "guardian_profile_id", "accepted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_enrollment_contract_acceptances_org_guardian",
        table_name="enrollment_contract_acceptances",
    )
    op.drop_table("enrollment_contract_acceptances")
    op.drop_index(
        "ix_enrollment_contract_versions_org_contract", table_name="enrollment_contract_versions"
    )
    op.drop_table("enrollment_contract_versions")
    op.drop_index("ix_enrollment_contracts_org_status", table_name="enrollment_contracts")
    op.drop_table("enrollment_contracts")
    op.drop_index(
        "ix_enrollment_contract_templates_org_active", table_name="enrollment_contract_templates"
    )
    op.drop_table("enrollment_contract_templates")
