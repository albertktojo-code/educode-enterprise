from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMBEDDING_DIMENSION = 384


class RetrievalSourceKind(StrEnum):
    LEARNING_UNIT = "learning_unit"
    GENERATION_SOURCE = "generation_source"


class RetrievalIndexStatus(StrEnum):
    NOT_INDEXED = "not_indexed"
    PROCESSING = "processing"
    INDEXED = "indexed"
    STALE = "stale"
    FAILED = "failed"


class RetrievalFeedbackRating(StrEnum):
    RELEVANT = "relevant"
    PARTIAL = "partial"
    IRRELEVANT = "irrelevant"


class RetrievalIndexJob(Base):
    __tablename__ = "retrieval_index_jobs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_kind",
            "learning_unit_id",
            "generation_source_id",
            name="uq_retrieval_index_source",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    source_kind: Mapped[RetrievalSourceKind] = mapped_column(
        Enum(RetrievalSourceKind, name="retrieval_source_kind"), nullable=False
    )
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=True
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chapters.id", ondelete="CASCADE"), index=True, nullable=True
    )
    learning_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_units.id", ondelete="CASCADE"), index=True, nullable=True
    )
    generation_source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_sources.id", ondelete="CASCADE"), index=True, nullable=True
    )
    source_title: Mapped[str] = mapped_column(String(260), nullable=False)
    status: Mapped[RetrievalIndexStatus] = mapped_column(
        Enum(RetrievalIndexStatus, name="retrieval_index_status"),
        default=RetrievalIndexStatus.NOT_INDEXED,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    chunk_target_chars: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    chunk_overlap_chars: Mapped[int] = mapped_column(Integer, default=160, nullable=False)
    chunk_min_chars: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    chunking_version: Mapped[str] = mapped_column(
        String(80), default="hierarchical-v1", nullable=False
    )
    embedding_provider: Mapped[str] = mapped_column(String(80), default="mock", nullable=False)
    embedding_model: Mapped[str] = mapped_column(
        String(120), default="deterministic-hash-v1", nullable=False
    )
    embedding_dimension: Mapped[int] = mapped_column(
        Integer, default=EMBEDDING_DIMENSION, nullable=False
    )
    source_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indexing_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active_chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    security_flag_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "index_job_id", "indexing_revision", "chunk_index", name="uq_chunk_revision_index"
        ),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_document_chunks_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    index_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("retrieval_index_jobs.id", ondelete="CASCADE"), index=True
    )
    source_kind: Mapped[RetrievalSourceKind] = mapped_column(
        Enum(RetrievalSourceKind, name="retrieval_source_kind"), nullable=False
    )
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=True
    )
    chapter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("document_chapters.id", ondelete="CASCADE"), index=True, nullable=True
    )
    learning_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_units.id", ondelete="CASCADE"), index=True, nullable=True
    )
    generation_source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_sources.id", ondelete="CASCADE"), index=True, nullable=True
    )
    heading: Mapped[str | None] = mapped_column(String(300), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_order: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('portuguese', coalesce(content, ''))", persisted=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    security_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    security_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    chunking_version: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    indexing_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RetrievalFeedback(Base):
    __tablename__ = "retrieval_feedback"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    search_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    rating: Mapped[RetrievalFeedbackRating] = mapped_column(
        Enum(RetrievalFeedbackRating, name="retrieval_feedback_rating"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
