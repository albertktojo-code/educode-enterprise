"""Hierarchical chunks, deterministic embeddings and hybrid retrieval.

Revision ID: 0008_vector_retrieval
Revises: 0007_creative_library
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_vector_retrieval"
down_revision: str | None = "0007_creative_library"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_kind = postgresql.ENUM(
    "LEARNING_UNIT", "GENERATION_SOURCE", name="retrieval_source_kind", create_type=False
)
index_status = postgresql.ENUM(
    "NOT_INDEXED",
    "PROCESSING",
    "INDEXED",
    "STALE",
    "FAILED",
    name="retrieval_index_status",
    create_type=False,
)
feedback_rating = postgresql.ENUM(
    "RELEVANT", "PARTIAL", "IRRELEVANT", name="retrieval_feedback_rating", create_type=False
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    for enum_type in (source_kind, index_status, feedback_rating):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "retrieval_index_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", source_kind, nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("learning_unit_id", sa.Uuid(), nullable=True),
        sa.Column("generation_source_id", sa.Uuid(), nullable=True),
        sa.Column("source_title", sa.String(length=260), nullable=False),
        sa.Column("status", index_status, server_default="NOT_INDEXED", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_step", sa.String(length=160), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_target_chars", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("chunk_overlap_chars", sa.Integer(), server_default="160", nullable=False),
        sa.Column("chunk_min_chars", sa.Integer(), server_default="200", nullable=False),
        sa.Column(
            "chunking_version",
            sa.String(length=80),
            server_default="hierarchical-v1",
            nullable=False,
        ),
        sa.Column(
            "embedding_provider", sa.String(length=80), server_default="mock", nullable=False
        ),
        sa.Column(
            "embedding_model",
            sa.String(length=120),
            server_default="deterministic-hash-v1",
            nullable=False,
        ),
        sa.Column("embedding_dimension", sa.Integer(), server_default="384", nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=True),
        sa.Column("indexing_revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active_chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("security_flag_count", sa.Integer(), server_default="0", nullable=False),
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
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["document_chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["generation_source_id"], ["generation_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "source_kind",
            "learning_unit_id",
            "generation_source_id",
            name="uq_retrieval_index_source",
        ),
    )
    for column in (
        "organization_id",
        "created_by_user_id",
        "document_id",
        "chapter_id",
        "learning_unit_id",
        "generation_source_id",
    ):
        op.create_index(f"ix_retrieval_index_jobs_{column}", "retrieval_index_jobs", [column])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("index_job_id", sa.Uuid(), nullable=False),
        sa.Column("source_kind", source_kind, nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("learning_unit_id", sa.Uuid(), nullable=True),
        sa.Column("generation_source_id", sa.Uuid(), nullable=True),
        sa.Column("heading", sa.String(length=300), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('portuguese', coalesce(content, ''))", persisted=True),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("security_flag", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("security_notes", sa.Text(), nullable=True),
        sa.Column("chunking_version", sa.String(length=80), nullable=False),
        sa.Column("embedding_provider", sa.String(length=80), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("indexing_revision", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["index_job_id"], ["retrieval_index_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["document_chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["generation_source_id"], ["generation_sources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "index_job_id", "indexing_revision", "chunk_index", name="uq_chunk_revision_index"
        ),
    )
    for column in (
        "organization_id",
        "index_job_id",
        "document_id",
        "chapter_id",
        "learning_unit_id",
        "generation_source_id",
        "content_checksum",
        "is_active",
    ):
        op.create_index(f"ix_document_chunks_{column}", "document_chunks", [column])
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "retrieval_feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("search_mode", sa.String(length=30), nullable=False),
        sa.Column("rating", feedback_rating, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "chunk_id", "user_id"):
        op.create_index(f"ix_retrieval_feedback_{column}", "retrieval_feedback", [column])


def downgrade() -> None:
    op.drop_table("retrieval_feedback")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.drop_table("document_chunks")
    op.drop_table("retrieval_index_jobs")
    bind = op.get_bind()
    for enum_type in (feedback_rating, index_status, source_kind):
        enum_type.drop(bind, checkfirst=True)
