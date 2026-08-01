from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AIProjectMemory(Base):
    __tablename__ = "ai_project_memories"
    __table_args__ = (UniqueConstraint("organization_id", "project_id", name="uq_ai_memory_org_project"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    memory_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    objectives: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    audience_profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    tone_rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    canonical_characters: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    visual_rules: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    approved_decisions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    forbidden_changes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AIReviewQueueItem(Base):
    __tablename__ = "ai_review_queue_items"
    __table_args__ = (UniqueConstraint("organization_id", "result_id", name="uq_ai_review_queue_org_result"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_requests.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_results.id", ondelete="CASCADE"), index=True)
    module_name: Mapped[str] = mapped_column(String(80), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    assigned_to_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AIQualityEvaluation(Base):
    __tablename__ = "ai_quality_evaluations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_results.id", ondelete="CASCADE"), index=True)
    structural_validity: Mapped[float] = mapped_column(Float, default=0.0)
    pedagogical_alignment: Mapped[float] = mapped_column(Float, default=0.0)
    source_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    age_appropriateness: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_consistency: Mapped[float] = mapped_column(Float, default=0.0)
    safety_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AIModelComparison(Base):
    __tablename__ = "ai_model_comparisons"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    flow_id: Mapped[str] = mapped_column(String(64), index=True)
    module_name: Mapped[str] = mapped_column(String(80), nullable=False)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    model_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    comparison_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    recommended_model_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_models.id", ondelete="SET NULL"))
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AIGenerationCheckpoint(Base):
    __tablename__ = "ai_generation_checkpoints"
    __table_args__ = (UniqueConstraint("request_id", "step_key", name="uq_ai_checkpoint_request_step"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_requests.id", ondelete="CASCADE"), index=True)
    step_key: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="completed", nullable=False)
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AIAccessibilityArtifact(Base):
    __tablename__ = "ai_accessibility_artifacts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_results.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(60), index=True)
    locale: Mapped[str] = mapped_column(String(20), default="pt-BR", nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
