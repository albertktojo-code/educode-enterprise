from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RagContextStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    READY_WITH_WARNINGS = "ready_with_warnings"
    INSUFFICIENT = "insufficient"
    CONFLICTED = "conflicted"
    APPROVED = "approved"
    ARCHIVED = "archived"


class RagFactType(StrEnum):
    DEFINITION = "definition"
    PROCEDURE = "procedure"
    EXAMPLE = "example"
    MISCONCEPTION = "misconception"
    CONSTRAINT = "constraint"
    OTHER = "other"


class RagReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RagRuleCategory(StrEnum):
    PEDAGOGICAL = "pedagogical"
    NARRATIVE = "narrative"
    CONTINUITY = "continuity"
    CREATIVE = "creative"
    VISUAL = "visual"
    SAFETY = "safety"
    ACCESSIBILITY = "accessibility"


class RagRulePriority(StrEnum):
    REQUIRED = "required"
    HIGH = "high"
    NORMAL = "normal"


class RagConflictStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class RagSourceSafety(StrEnum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"
    MANUALLY_APPROVED = "manually_approved"


class RagContext(Base):
    __tablename__ = "rag_contexts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    generation_project_id: Mapped[UUID] = mapped_column(
        ForeignKey("generation_projects.id", ondelete="CASCADE"), index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    query: Mapped[str] = mapped_column(Text(), nullable=False)
    search_mode: Mapped[str] = mapped_column(String(30), default="hybrid", nullable=False)
    status: Mapped[RagContextStatus] = mapped_column(
        Enum(RagContextStatus, name="rag_context_status"),
        default=RagContextStatus.DRAFT,
        nullable=False,
    )
    context_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retrieval_configuration: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    structured_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assembled_context_text: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    readiness_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sources: Mapped[list["RagContextSource"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="context",
        order_by="RagContextSource.ranking_position",
        lazy="selectin",
    )
    facts: Mapped[list["RagContextFact"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="context",
        order_by="RagContextFact.order_index",
        lazy="selectin",
    )
    rules: Mapped[list["RagContextRule"]] = relationship(
        cascade="all, delete-orphan",
        back_populates="context",
        order_by="RagContextRule.order_index",
        lazy="selectin",
    )
    conflicts: Mapped[list["RagContextConflict"]] = relationship(
        cascade="all, delete-orphan", back_populates="context", lazy="selectin"
    )
    evaluations: Mapped[list["RagContextEvaluation"]] = relationship(
        cascade="all, delete-orphan", back_populates="context", lazy="selectin"
    )


class RagContextSource(Base):
    __tablename__ = "rag_context_sources"
    __table_args__ = (
        UniqueConstraint("rag_context_id", "chunk_id", name="uq_rag_context_chunk"),
        UniqueConstraint("rag_context_id", "citation_code", name="uq_rag_context_citation"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rag_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="RESTRICT"), index=True
    )
    citation_code: Mapped[str] = mapped_column(String(30), nullable=False)
    citation_label: Mapped[str] = mapped_column(String(220), nullable=False)
    ranking_position: Mapped[int] = mapped_column(Integer, nullable=False)
    source_order: Mapped[int] = mapped_column(Integer, nullable=False)
    inclusion_reason: Mapped[str] = mapped_column(Text(), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    safety_status: Mapped[RagSourceSafety] = mapped_column(
        Enum(RagSourceSafety, name="rag_source_safety"),
        default=RagSourceSafety.SAFE,
        nullable=False,
    )
    content_snapshot: Mapped[str] = mapped_column(Text(), nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    context: Mapped[RagContext] = relationship(back_populates="sources")


class RagContextFact(Base):
    __tablename__ = "rag_context_facts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rag_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="CASCADE"), index=True
    )
    statement: Mapped[str] = mapped_column(Text(), nullable=False)
    fact_type: Mapped[RagFactType] = mapped_column(
        Enum(RagFactType, name="rag_fact_type"), default=RagFactType.OTHER, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    citation_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    review_status: Mapped[RagReviewStatus] = mapped_column(
        Enum(RagReviewStatus, name="rag_review_status"),
        default=RagReviewStatus.PENDING,
        nullable=False,
    )
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    context: Mapped[RagContext] = relationship(back_populates="facts")


class RagContextRule(Base):
    __tablename__ = "rag_context_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rag_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[RagRuleCategory] = mapped_column(
        Enum(RagRuleCategory, name="rag_rule_category"), nullable=False
    )
    rule_text: Mapped[str] = mapped_column(Text(), nullable=False)
    priority: Mapped[RagRulePriority] = mapped_column(
        Enum(RagRulePriority, name="rag_rule_priority"),
        default=RagRulePriority.NORMAL,
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    context: Mapped[RagContext] = relationship(back_populates="rules")


class RagContextConflict(Base):
    __tablename__ = "rag_context_conflicts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rag_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="CASCADE"), index=True
    )
    statement_a: Mapped[str] = mapped_column(Text(), nullable=False)
    statement_b: Mapped[str] = mapped_column(Text(), nullable=False)
    citation_codes_a: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    citation_codes_b: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[RagConflictStatus] = mapped_column(
        Enum(RagConflictStatus, name="rag_conflict_status"),
        default=RagConflictStatus.OPEN,
        nullable=False,
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)

    context: Mapped[RagContext] = relationship(back_populates="conflicts")


class RagContextEvaluation(Base):
    __tablename__ = "rag_context_evaluations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    rag_context_id: Mapped[UUID] = mapped_column(
        ForeignKey("rag_contexts.id", ondelete="CASCADE"), index=True
    )
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, nullable=False)
    diversity_score: Mapped[float] = mapped_column(Float, nullable=False)
    traceability_score: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)
    safety_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    context: Mapped[RagContext] = relationship(back_populates="evaluations")
