"""Document pages, chapters and OCR preparation.

Revision ID: 0005_document_structure
Revises: 0004_documents
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_document_structure"
down_revision: str | None = "0004_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

page_kind = postgresql.ENUM(
    "TEXTUAL",
    "SCANNED",
    "MIXED",
    "EMPTY",
    name="document_page_kind",
    create_type=False,
)
extraction_method = postgresql.ENUM(
    "NATIVE",
    "OCR",
    "NONE",
    name="text_extraction_method",
    create_type=False,
)
ocr_status = postgresql.ENUM(
    "NOT_REQUIRED",
    "REQUIRED",
    "COMPLETED",
    "FAILED",
    name="ocr_status",
    create_type=False,
)
chapter_detection_method = postgresql.ENUM(
    "PDF_TOC",
    "AUTOMATIC_HEADING",
    "MANUAL",
    name="chapter_detection_method",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    page_kind.create(bind, checkfirst=True)
    extraction_method.create(bind, checkfirst=True)
    ocr_status.create(bind, checkfirst=True)
    chapter_detection_method.create(bind, checkfirst=True)

    op.create_table(
        "document_pages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), server_default="", nullable=False),
        sa.Column("character_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("image_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("page_kind", page_kind, nullable=False),
        sa.Column("extraction_method", extraction_method, nullable=False),
        sa.Column("ocr_status", ocr_status, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "page_number",
            name="uq_document_page_number",
        ),
    )
    op.create_index(
        "ix_document_pages_document_id",
        "document_pages",
        ["document_id"],
        unique=False,
    )

    op.create_table(
        "document_chapters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=True),
        sa.Column("start_page", sa.Integer(), nullable=False),
        sa.Column("end_page", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("detection_method", chapter_detection_method, nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1", nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_chapters_document_id",
        "document_chapters",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chapters_document_id", table_name="document_chapters")
    op.drop_table("document_chapters")
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")
    chapter_detection_method.drop(op.get_bind(), checkfirst=True)
    ocr_status.drop(op.get_bind(), checkfirst=True)
    extraction_method.drop(op.get_bind(), checkfirst=True)
    page_kind.drop(op.get_bind(), checkfirst=True)
