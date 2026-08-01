from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ProjectMemoryUpsert(BaseModel):
    objectives: list[str] = Field(default_factory=list)
    audience_profile: dict[str, Any] = Field(default_factory=dict)
    tone_rules: dict[str, Any] = Field(default_factory=dict)
    canonical_characters: list[dict[str, Any]] = Field(default_factory=list)
    visual_rules: dict[str, Any] = Field(default_factory=dict)
    approved_decisions: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_changes: list[str] = Field(default_factory=list)
class ProjectMemoryRead(ProjectMemoryUpsert):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; organization_id: UUID; project_id: UUID; memory_version: int; updated_by_user_id: UUID; updated_at: datetime
class ReviewQueueUpdate(BaseModel):
    status: str = Field(pattern="^(pending|in_review|approved|rejected|changes_requested)$")
    assigned_to_user_id: UUID | None = None
class ReviewQueueRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; request_id: UUID; result_id: UUID; module_name: str; priority: int; status: str; quality_score: float; reasons: list[str]; assigned_to_user_id: UUID|None; due_at: datetime|None; created_at: datetime
class QualityEvaluationRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; result_id: UUID; structural_validity: float; pedagogical_alignment: float; source_coverage: float; age_appropriateness: float; narrative_consistency: float; safety_score: float; confidence_score: float; findings: list[dict[str,Any]]; evaluated_at: datetime
class ModelComparisonCreate(BaseModel):
    module_name: str; action_name: str; model_ids: list[UUID] = Field(min_length=2, max_length=5); input_data: dict[str,Any]
class ModelComparisonRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; flow_id: str; module_name: str; action_name: str; model_ids: list[str]; comparison_results: list[dict[str,Any]]; recommended_model_id: UUID|None; created_at: datetime
class CheckpointCreate(BaseModel):
    step_key: str = Field(min_length=1,max_length=100); step_order: int = Field(ge=0); payload_snapshot: dict[str,Any]=Field(default_factory=dict)
class CheckpointRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; request_id: UUID; step_key: str; step_order: int; status: str; payload_snapshot: dict[str,Any]; checksum: str; completed_at: datetime
class AccessibilityCreate(BaseModel):
    artifact_types: list[str] = Field(default_factory=lambda:["alt_text","simplified_text","screen_reader_summary"])
    locale: str = "pt-BR"
class AccessibilityRead(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: UUID; result_id: UUID; artifact_type: str; locale: str; content: dict[str,Any]; validated: bool; created_at: datetime
class ValueMetricsRead(BaseModel):
    total_results: int; approved: int; rejected: int; approval_rate: float; average_quality: float; average_human_rating: float; estimated_cost: float; by_module: dict[str,Any]
