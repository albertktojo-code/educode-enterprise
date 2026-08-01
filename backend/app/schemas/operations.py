from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    job_type: str = Field(min_length=2, max_length=80)
    module_name: str = Field(min_length=2, max_length=80)
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: UUID | None = None
    ai_flow_id: str | None = Field(default=None, max_length=64)
    priority: int = Field(default=50, ge=0, le=100)
    total_steps: int = Field(default=1, ge=1, le=1000)
    max_retries: int = Field(default=3, ge=0, le=10)
    idempotency_key: str | None = Field(default=None, max_length=180)
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    estimated_cost: float = Field(default=0.0, ge=0)
    depends_on_job_ids: list[UUID] = Field(default_factory=list)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    requested_by_user_id: UUID
    job_type: str
    queue_name: str
    module_name: str
    entity_type: str | None
    entity_id: UUID | None
    ai_flow_id: str | None
    status: str
    priority: int
    progress_percent: int
    current_step: str
    total_steps: int
    idempotency_key: str
    input_snapshot: dict[str, Any]
    result_reference: dict[str, Any]
    retry_count: int
    max_retries: int
    error_code: str
    error_message: str
    cancel_requested: bool
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    event_type: str
    event_data: dict[str, Any]
    created_at: datetime


class JobNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    notification_type: str
    title: str
    message: str
    action_path: str | None
    status: str
    created_at: datetime
    read_at: datetime | None


class WorkerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    worker_name: str
    queue_name: str
    hostname: str
    process_id: int
    current_job_id: UUID | None
    status: str
    started_at: datetime
    last_seen_at: datetime


class OperationOverview(BaseModel):
    redis_available: bool
    worker_count: int
    active_workers: int
    queue_counts: dict[str, int]
    status_counts: dict[str, int]
    failed_last_24h: int
    average_completion_seconds: float
    circuit_open_count: int


class CircuitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_id: UUID
    state: str
    consecutive_failures: int
    failure_threshold: int
    opened_at: datetime | None
    next_probe_at: datetime | None
    last_error: str
    updated_at: datetime


class CircuitUpdate(BaseModel):
    state: str = Field(pattern="^(closed|open|half_open)$")
    consecutive_failures: int | None = Field(default=None, ge=0)
    last_error: str | None = Field(default=None, max_length=4000)
