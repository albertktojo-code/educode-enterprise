from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIProviderStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"


class AIRequestStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AIReviewDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class AIProvider(Base):
    __tablename__ = "ai_providers"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_ai_provider_org_name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=AIProviderStatus.ACTIVE.value, nullable=False)
    public_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    secret_env_var: Mapped[str | None] = mapped_column(String(160), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    models: Mapped[list["AIModel"]] = relationship(back_populates="provider", cascade="all, delete-orphan", lazy="selectin")


class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("provider_id", "model_identifier", name="uq_ai_model_provider_identifier"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[UUID] = mapped_column(ForeignKey("ai_providers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(200), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    input_unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    output_unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    image_unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    provider: Mapped[AIProvider] = relationship(back_populates="models", lazy="selectin")


class AIPromptTemplate(Base):
    __tablename__ = "ai_prompt_templates"
    __table_args__ = (UniqueConstraint("organization_id", "purpose", "version", name="uq_ai_prompt_org_purpose_version"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    system_instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    required_variables: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    recommended_model_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIModulePolicy(Base):
    __tablename__ = "ai_module_policies"
    __table_args__ = (UniqueConstraint("organization_id", "module_name", name="uq_ai_policy_org_module"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    module_name: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allowed_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_model_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_request_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    monthly_cost_limit: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    allow_student_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_real_person_images: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fallback_mode: Mapped[str] = mapped_column(String(30), default="mock", nullable=False)
    policy_configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AIGenerationRequest(Base):
    __tablename__ = "ai_generation_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    flow_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    module_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    request_type: Mapped[str] = mapped_column(String(60), default="structured_text", nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[UUID | None] = mapped_column(nullable=True)
    provider_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_providers.id", ondelete="SET NULL"), nullable=True)
    model_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True)
    prompt_template_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_prompt_templates.id", ondelete="SET NULL"), nullable=True)
    rag_context_id: Mapped[UUID | None] = mapped_column(ForeignKey("rag_contexts.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=AIRequestStatus.PENDING.value, index=True, nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    safety_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    results: Mapped[list["AIGenerationResult"]] = relationship(back_populates="request", cascade="all, delete-orphan", lazy="selectin")


class AIGenerationResult(Base):
    __tablename__ = "ai_generation_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_requests.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    result_type: Mapped[str] = mapped_column(String(60), nullable=False)
    structured_content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    storage_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    validation_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    safety_results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    review_status: Mapped[str] = mapped_column(String(30), default=AIReviewDecision.PENDING.value, nullable=False)
    applied_to_module: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    application_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request: Mapped[AIGenerationRequest] = relationship(back_populates="results")


class AIUsageRecord(Base):
    __tablename__ = "ai_usage_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_requests.id", ondelete="CASCADE"), index=True)
    provider_name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(200), nullable=False)
    input_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIGenerationReview(Base):
    __tablename__ = "ai_generation_reviews"
    __table_args__ = (UniqueConstraint("result_id", "reviewed_by_user_id", name="uq_ai_review_result_user"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_results.id", ondelete="CASCADE"), index=True)
    reviewed_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    correctness_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pedagogical_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creativity_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIActivityEvent(Base):
    __tablename__ = "ai_activity_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    flow_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_generation_requests.id", ondelete="SET NULL"), index=True, nullable=True)
    module_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIModuleLink(Base):
    __tablename__ = "ai_module_links"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("ai_generation_requests.id", ondelete="CASCADE"), index=True)
    result_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_generation_results.id", ondelete="SET NULL"), index=True, nullable=True)
    module_name: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    target_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    target_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    relation_type: Mapped[str] = mapped_column(String(60), default="generated_output", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    link_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
