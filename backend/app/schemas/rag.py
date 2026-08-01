from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.rag import (
    RagConflictStatus,
    RagContextStatus,
    RagFactType,
    RagReviewStatus,
    RagRuleCategory,
    RagRulePriority,
    RagSourceSafety,
)
from app.schemas.retrieval import SearchMode


class RagContextAssemble(BaseModel):
    generation_project_id: UUID
    title: str = Field(min_length=3, max_length=240)
    query: str = Field(min_length=2, max_length=2000)
    search_mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=8, ge=2, le=30)
    candidate_k: int = Field(default=30, ge=5, le=100)
    document_id: UUID | None = None
    chapter_id: UUID | None = None
    learning_unit_id: UUID | None = None
    generation_source_id: UUID | None = None
    index_job_id: UUID | None = None
    include_suspicious_sources: bool = False
    notes: str | None = Field(default=None, max_length=5000)


class RagContextUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=240)
    notes: str | None = Field(default=None, max_length=5000)
    status: RagContextStatus | None = None


class RagSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chunk_id: UUID
    citation_code: str
    citation_label: str
    ranking_position: int
    source_order: int
    inclusion_reason: str
    is_mandatory: bool
    is_included: bool
    safety_status: RagSourceSafety
    content_snapshot: str
    page_start: int | None
    page_end: int | None
    created_at: datetime


class RagSourceUpdate(BaseModel):
    is_included: bool | None = None
    is_mandatory: bool | None = None
    safety_status: RagSourceSafety | None = None


class RagFactCreate(BaseModel):
    statement: str = Field(min_length=3, max_length=5000)
    fact_type: RagFactType = RagFactType.OTHER
    confidence: float = Field(default=0.8, ge=0, le=1)
    citation_codes: list[str] = Field(default_factory=list)
    is_mandatory: bool = True


class RagFactUpdate(BaseModel):
    statement: str | None = Field(default=None, min_length=3, max_length=5000)
    fact_type: RagFactType | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    citation_codes: list[str] | None = None
    review_status: RagReviewStatus | None = None
    is_mandatory: bool | None = None


class RagFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    statement: str
    fact_type: RagFactType
    confidence: float
    citation_codes: list[str]
    review_status: RagReviewStatus
    is_mandatory: bool
    order_index: int
    created_at: datetime


class RagRuleCreate(BaseModel):
    category: RagRuleCategory
    rule_text: str = Field(min_length=3, max_length=5000)
    priority: RagRulePriority = RagRulePriority.NORMAL


class RagRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: RagRuleCategory
    rule_text: str
    priority: RagRulePriority
    order_index: int


class RagConflictRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    statement_a: str
    statement_b: str
    citation_codes_a: list[str]
    citation_codes_b: list[str]
    description: str
    status: RagConflictStatus
    resolution_notes: str | None


class RagConflictUpdate(BaseModel):
    status: RagConflictStatus
    resolution_notes: str | None = Field(default=None, max_length=5000)


class RagEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    relevance_score: float
    coverage_score: float
    diversity_score: float
    traceability_score: float
    consistency_score: float
    safety_score: float
    overall_score: float
    details: dict[str, object]
    created_at: datetime


class RagContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    generation_project_id: UUID
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    title: str
    query: str
    search_mode: str
    status: RagContextStatus
    context_version: int
    retrieval_configuration: dict[str, object]
    structured_context: dict[str, object]
    assembled_context_text: str
    quality_score: float
    token_estimate: int
    readiness_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    sources: list[RagSourceRead]
    facts: list[RagFactRead]
    rules: list[RagRuleRead]
    conflicts: list[RagConflictRead]
    evaluations: list[RagEvaluationRead]


class RagContextSummary(BaseModel):
    id: UUID
    generation_project_id: UUID
    title: str
    query: str
    search_mode: str
    status: RagContextStatus
    context_version: int
    quality_score: float
    source_count: int
    fact_count: int
    open_conflict_count: int
    updated_at: datetime


class RagTraceabilityItem(BaseModel):
    fact_id: UUID
    statement: str
    citations: list[RagSourceRead]


class RagTraceabilityResponse(BaseModel):
    context_id: UUID
    items: list[RagTraceabilityItem]
