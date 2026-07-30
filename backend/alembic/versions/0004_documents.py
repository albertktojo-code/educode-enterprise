"""Document storage and PDF extraction.

Revision ID: 0004_documents
Revises: 0003_education_core
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_documents"
down_revision: str | None = "0003_education_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

document_status = postgresql.ENUM(
    "UPLOADED",
    "PROCESSING",
    "READY",
    "FAILED",
    name="document_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    document_status.create(bind, checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", document_status, server_default="UPLOADED", nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_error", sa.Text(), nullable=True),
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
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index(
        "ix_documents_organization_id",
        "documents",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_uploaded_by_id",
        "documents",
        ["uploaded_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_project_id",
        "documents",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_documents_checksum_sha256",
        "documents",
        ["checksum_sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_documents_checksum_sha256", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_index("ix_documents_uploaded_by_id", table_name="documents")
    op.drop_index("ix_documents_organization_id", table_name="documents")
    op.drop_table("documents")
    document_status.drop(op.get_bind(), checkfirst=True)
