"""enrollment document checklist and immutable versions

Revision ID: 0060_enrollment_documents
Revises: 0059_school_admissions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0060_enrollment_documents"
down_revision: str | None = "0059_school_admissions"
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
        "enrollment_document_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("school_unit_id", sa.Uuid()),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "accepted_mime_types",
            postgresql.JSONB(),
            server_default=sa.text("'[\"application/pdf\", \"image/jpeg\", \"image/png\"]'::jsonb"),
            nullable=False,
        ),
        sa.Column("max_size_bytes", sa.Integer(), server_default="10485760", nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default="1825", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("max_size_bytes > 0", name="ck_enrollment_requirement_size"),
        sa.CheckConstraint("retention_days > 0", name="ck_enrollment_requirement_retention"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_unit_id"], ["school_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "school_unit_id",
            "code",
            name="uq_enrollment_document_requirement_scope",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_enrollment_document_requirements_org_active",
        "enrollment_document_requirements",
        ["organization_id", "is_active"],
    )

    op.create_table(
        "enrollment_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), server_default="submitted", nullable=False),
        sa.Column("current_version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.Text(), server_default="", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('submitted', 'under_review', 'approved', 'rejected', "
            "'illegible', 'expired', 'resubmission_requested')",
            name="ck_enrollment_document_status",
        ),
        sa.CheckConstraint("current_version_number > 0", name="ck_enrollment_document_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["application_id"], ["student_enrollment_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["enrollment_document_requirements.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "requirement_id", name="uq_enrollment_document_application_slot"
        ),
    )
    op.create_index(
        "ix_enrollment_documents_org_status",
        "enrollment_documents",
        ["organization_id", "status", "updated_at"],
    )

    op.create_table(
        "enrollment_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("version_number > 0", name="ck_enrollment_document_version_positive"),
        sa.CheckConstraint("size_bytes > 0", name="ck_enrollment_document_file_size"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["enrollment_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_enrollment_document_version"),
        sa.UniqueConstraint("storage_key", name="uq_enrollment_document_storage_key"),
    )
    op.create_index(
        "ix_enrollment_document_versions_org_document",
        "enrollment_document_versions",
        ["organization_id", "document_id", "version_number"],
    )

    op.create_table(
        "enrollment_document_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "decision IN ('under_review', 'approved', 'rejected', 'illegible', "
            "'expired', 'resubmission_requested')",
            name="ck_enrollment_document_review_decision",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["enrollment_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["enrollment_document_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enrollment_document_reviews_org_document",
        "enrollment_document_reviews",
        ["organization_id", "document_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_enrollment_document_reviews_org_document", table_name="enrollment_document_reviews"
    )
    op.drop_table("enrollment_document_reviews")
    op.drop_index(
        "ix_enrollment_document_versions_org_document",
        table_name="enrollment_document_versions",
    )
    op.drop_table("enrollment_document_versions")
    op.drop_index("ix_enrollment_documents_org_status", table_name="enrollment_documents")
    op.drop_table("enrollment_documents")
    op.drop_index(
        "ix_enrollment_document_requirements_org_active",
        table_name="enrollment_document_requirements",
    )
    op.drop_table("enrollment_document_requirements")
