from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AIProviderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    provider_type: str = Field(default="mock", pattern="^(mock|generic_http)$")
    public_configuration: dict[str, Any] = Field(default_factory=dict)
    secret_env_var: str | None = Field(default=None, max_length=160)
    base_url: str | None = Field(default=None, max_length=500)
    timeout_seconds: int = Field(default=60, ge=5, le=300)


class AIProviderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    provider_type: str
    status: str
    public_configuration: dict[str, Any]
    secret_env_var: str | None
    base_url: str | None
    timeout_seconds: int
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class AIModelCreate(BaseModel):
    provider_id: UUID
    name: str = Field(min_length=2, max_length=160)
    model_identifier: str = Field(min_length=1, max_length=200)
    capabilities: list[str] = Field(default_factory=lambda: ["structured_text"])
    configuration: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    input_unit_cost: float = Field(default=0.0, ge=0)
    output_unit_cost: float = Field(default=0.0, ge=0)
    image_unit_cost: float = Field(default=0.0, ge=0)


class AIModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    provider_id: UUID
    name: str
    model_identifier: str
    capabilities: list[str]
    configuration: dict[str, Any]
    is_default: bool
    is_active: bool
    input_unit_cost: float
    output_unit_cost: float
    image_unit_cost: float
    created_at: datetime


class AIPromptTemplateCreate(BaseModel):
    purpose: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=180)
    version: int = Field(default=1, ge=1)
    system_instructions: str = Field(default="", max_length=20000)
    template_content: str = Field(min_length=3, max_length=50000)
    required_variables: list[str] = Field(default_factory=list)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="draft", pattern="^(draft|approved|archived)$")
    recommended_model_id: UUID | None = None


class AIPromptTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    purpose: str
    name: str
    version: int
    system_instructions: str
    template_content: str
    required_variables: list[str]
    output_schema: dict[str, Any]
    status: str
    recommended_model_id: UUID | None
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    created_at: datetime


class AIModulePolicyUpsert(BaseModel):
    module_name: str = Field(min_length=2, max_length=80)
    enabled: bool = True
    allowed_actions: list[str] = Field(default_factory=list)
    allowed_model_ids: list[UUID] = Field(default_factory=list)
    human_approval_required: bool = True
    daily_request_limit: int = Field(default=100, ge=0, le=100000)
    monthly_cost_limit: float = Field(default=100.0, ge=0)
    allow_student_data: bool = False
    allow_real_person_images: bool = False
    fallback_mode: str = Field(default="mock", pattern="^(mock|fail|alternate)$")
    policy_configuration: dict[str, Any] = Field(default_factory=dict)


class AIModulePolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    module_name: str
    enabled: bool
    allowed_actions: list[str]
    allowed_model_ids: list[str]
    human_approval_required: bool
    daily_request_limit: int
    monthly_cost_limit: float
    allow_student_data: bool
    allow_real_person_images: bool
    fallback_mode: str
    policy_configuration: dict[str, Any]
    updated_by_user_id: UUID
    updated_at: datetime


class AIGenerationCreate(BaseModel):
    module_name: str = Field(min_length=2, max_length=80)
    action_name: str = Field(min_length=2, max_length=100)
    request_type: str = Field(default="structured_text", pattern="^(structured_text|text|image)$")
    target_type: str | None = Field(default=None, max_length=80)
    target_id: UUID | None = None
    provider_id: UUID | None = None
    model_id: UUID | None = None
    prompt_template_id: UUID | None = None
    rag_context_id: UUID | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    queue_immediately: bool = True

    @model_validator(mode="after")
    def validate_input(self) -> "AIGenerationCreate":
        if not self.input_data:
            raise ValueError("Informe dados de entrada para a geração")
        return self


class AIGenerationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID
    organization_id: UUID
    result_type: str
    structured_content: dict[str, Any]
    text_content: str
    storage_reference: str | None
    validation_results: dict[str, Any]
    safety_results: dict[str, Any]
    review_status: str
    applied_to_module: bool
    application_snapshot: dict[str, Any]
    content_checksum: str
    created_at: datetime


class AIGenerationRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: str
    organization_id: UUID
    requested_by_user_id: UUID
    module_name: str
    action_name: str
    request_type: str
    target_type: str | None
    target_id: UUID | None
    provider_id: UUID | None
    model_id: UUID | None
    prompt_template_id: UUID | None
    rag_context_id: UUID | None
    status: str
    input_snapshot: dict[str, Any]
    parameters: dict[str, Any]
    source_snapshot: dict[str, Any]
    validation_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    estimated_cost: float
    error_message: str
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    results: list[AIGenerationResultRead] = Field(default_factory=list)


class AIReviewCreate(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|changes_requested)$")
    correctness_rating: int | None = Field(default=None, ge=1, le=5)
    pedagogical_rating: int | None = Field(default=None, ge=1, le=5)
    creativity_rating: int | None = Field(default=None, ge=1, le=5)
    safety_rating: int | None = Field(default=None, ge=1, le=5)
    comments: str = Field(default="", max_length=10000)


class AIApplyResultRequest(BaseModel):
    target_type: str = Field(min_length=2, max_length=80)
    target_id: UUID | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class AIActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    flow_id: str
    organization_id: UUID
    request_id: UUID | None
    module_name: str
    event_type: str
    event_data: dict[str, Any]
    created_by_user_id: UUID | None
    created_at: datetime


class AIUsageSummary(BaseModel):
    request_count: int
    completed_count: int
    failed_count: int
    input_units: int
    output_units: int
    image_count: int
    estimated_cost: float
    by_module: dict[str, dict[str, float | int]]


class AICapabilityRead(BaseModel):
    module_name: str
    actions: list[str]
    human_approval_required: bool
    enabled: bool
    notes: str


class AIModuleLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    request_id: UUID
    result_id: UUID | None
    module_name: str
    target_type: str
    target_id: UUID
    relation_type: str
    status: str
    link_metadata: dict[str, Any]
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
