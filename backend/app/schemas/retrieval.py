from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.retrieval import (
    RetrievalFeedbackRating,
    RetrievalIndexStatus,
    RetrievalSourceKind,
)


class SearchMode(StrEnum):
    SEMANTIC = "semantic"
    TEXT = "text"
    HYBRID = "hybrid"


class IndexConfig(BaseModel):
    target_chars: int = Field(default=1000, ge=300, le=4000)
    overlap_chars: int = Field(default=160, ge=0, le=800)
    min_chars: int = Field(default=200, ge=50, le=1200)

    @model_validator(mode="after")
    def validate_sizes(self) -> "IndexConfig":
        if self.min_chars > self.target_chars:
            raise ValueError("O tamanho mínimo não pode superar o tamanho-alvo")
        if self.overlap_chars >= self.target_chars:
            raise ValueError("A sobreposição deve ser menor que o tamanho-alvo")
        return self


class IndexJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    created_by_user_id: UUID
    source_kind: RetrievalSourceKind
    document_id: UUID | None
    chapter_id: UUID | None
    learning_unit_id: UUID | None
    generation_source_id: UUID | None
    source_title: str
    status: RetrievalIndexStatus
    progress: int
    current_step: str | None
    error_message: str | None
    chunk_target_chars: int
    chunk_overlap_chars: int
    chunk_min_chars: int
    chunking_version: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    source_checksum: str | None
    indexing_revision: int
    active_chunk_count: int
    security_flag_count: int
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    index_job_id: UUID
    source_kind: RetrievalSourceKind
    document_id: UUID | None
    chapter_id: UUID | None
    learning_unit_id: UUID | None
    generation_source_id: UUID | None
    heading: str | None
    page_start: int | None
    page_end: int | None
    source_order: int
    chunk_index: int
    content: str
    character_count: int
    token_estimate: int
    security_flag: bool
    security_notes: str | None
    indexing_revision: int
    metadata_json: dict[str, object]


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=8, ge=1, le=30)
    candidate_k: int = Field(default=30, ge=5, le=100)
    document_id: UUID | None = None
    chapter_id: UUID | None = None
    learning_unit_id: UUID | None = None
    generation_source_id: UUID | None = None
    index_job_id: UUID | None = None
    confirmed_only: bool = True


class SearchResult(BaseModel):
    chunk_id: UUID
    index_job_id: UUID
    source_kind: RetrievalSourceKind
    heading: str | None
    document_id: UUID | None
    chapter_id: UUID | None
    learning_unit_id: UUID | None
    generation_source_id: UUID | None
    page_start: int | None
    page_end: int | None
    source_order: int
    chunk_index: int
    content: str
    vector_score: float | None
    text_score: float | None
    hybrid_score: float | None
    matched_terms: list[str]
    security_flag: bool
    explanation: str


class OrderedContextItem(BaseModel):
    chunk_id: UUID
    citation_label: str
    source_order: int
    content: str


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    total_candidates: int
    results: list[SearchResult]
    ordered_context: list[OrderedContextItem]


class FeedbackCreate(BaseModel):
    chunk_id: UUID
    query_text: str = Field(min_length=2, max_length=2000)
    search_mode: SearchMode
    rating: RetrievalFeedbackRating
    notes: str | None = Field(default=None, max_length=3000)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chunk_id: UUID
    query_text: str
    search_mode: str
    rating: RetrievalFeedbackRating
    notes: str | None
    created_at: datetime


class RetrievalStats(BaseModel):
    total_jobs: int
    indexed_jobs: int
    processing_jobs: int
    stale_jobs: int
    failed_jobs: int
    active_chunks: int
    flagged_chunks: int
    feedback_total: int
    relevant_feedback: int
    partial_feedback: int
    irrelevant_feedback: int
