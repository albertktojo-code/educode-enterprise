from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import DeliverySourceType, NavigationMode, PublicationStatus, SessionStatus, TargetType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PublicationItem(BaseModel):
    question_version_id: uuid.UUID
    position: int = Field(ge=0)
    section: str | None = Field(default=None, max_length=100)
    required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=3, max_length=220)
    version: int = Field(default=1, ge=1)
    source_type: DeliverySourceType
    source_id: uuid.UUID
    item_snapshot: list[PublicationItem] = Field(min_length=1, max_length=500)
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int = Field(default=60, ge=1, le=1440)
    max_attempts: int = Field(default=1, ge=1, le=20)
    navigation_mode: NavigationMode = NavigationMode.FREE
    shuffle_questions: bool = False
    shuffle_options: bool = False
    allow_resume: bool = True
    autosave_seconds: int = Field(default=15, ge=5, le=300)
    delivery_rules: dict[str, Any] = Field(default_factory=dict)
    access_settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_window_and_items(self) -> "PublicationCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("A data final deve ser posterior a data inicial.")
        positions = [item.position for item in self.item_snapshot]
        if len(positions) != len(set(positions)):
            raise ValueError("As posicoes dos itens devem ser unicas.")
        identifiers = [item.question_version_id for item in self.item_snapshot]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Uma versao de questao nao pode ser repetida na mesma publicacao.")
        return self


class PublicationRead(ORMModel):
    id: uuid.UUID
    code: str
    title: str
    version: int
    source_type: str
    source_id: uuid.UUID
    status: str
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    max_attempts: int
    navigation_mode: str
    shuffle_questions: bool
    allow_resume: bool
    autosave_seconds: int
    item_snapshot: list[dict[str, Any]]


class TargetCreate(BaseModel):
    target_type: TargetType
    target_id: uuid.UUID
    available_from: datetime | None = None
    available_until: datetime | None = None
    extra_attempts: int = Field(default=0, ge=0, le=20)
    custom_duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @model_validator(mode="after")
    def validate_window(self) -> "TargetCreate":
        if self.available_from and self.available_until and self.available_until <= self.available_from:
            raise ValueError("A janela do publico-alvo e invalida.")
        return self


class TargetRead(ORMModel):
    id: uuid.UUID
    publication_id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    available_from: datetime | None
    available_until: datetime | None
    extra_attempts: int
    custom_duration_minutes: int | None
    status: str


class AccommodationCreate(BaseModel):
    student_id: uuid.UUID
    extra_time_percent: int = Field(default=0, ge=0, le=300)
    extra_time_minutes: int = Field(default=0, ge=0, le=600)
    accessible_version_required: bool = False
    screen_reader_mode: bool = False
    high_contrast: bool = False
    reduced_motion: bool = False
    keyboard_only: bool = False
    simplified_language: bool = False
    custom_settings: dict[str, Any] = Field(default_factory=dict)


class AccommodationRead(ORMModel):
    id: uuid.UUID
    publication_id: uuid.UUID
    student_id: uuid.UUID
    extra_time_percent: int
    extra_time_minutes: int
    accessible_version_required: bool
    screen_reader_mode: bool
    high_contrast: bool
    reduced_motion: bool
    keyboard_only: bool
    simplified_language: bool
    custom_settings: dict[str, Any]
    status: str


class SessionStart(BaseModel):
    publication_id: uuid.UUID
    student_id: uuid.UUID
    target_id: uuid.UUID | None = None
    device_context: dict[str, Any] = Field(default_factory=dict)


class SessionRead(ORMModel):
    id: uuid.UUID
    publication_id: uuid.UUID
    student_id: uuid.UUID
    assessment_hub_attempt_id: uuid.UUID
    session_number: int
    status: str
    started_at: datetime | None
    last_activity_at: datetime | None
    expires_at: datetime | None
    submitted_at: datetime | None
    remaining_seconds: int
    current_item_position: int
    resume_count: int
    reconnect_count: int
    focus_loss_count: int
    integrity_status: str
    delivery_snapshot: dict[str, Any]
    accessibility_snapshot: dict[str, Any]


class SessionItemRead(ORMModel):
    id: uuid.UUID
    session_id: uuid.UUID
    question_version_id: uuid.UUID
    position: int
    original_position: int
    option_order: list[str]
    status: str
    flagged_for_review: bool


class SessionDetail(BaseModel):
    session: SessionRead
    items: list[SessionItemRead]


class AutosaveCreate(BaseModel):
    session_item_id: uuid.UUID
    sequence_number: int = Field(ge=1)
    response: dict[str, Any] = Field(default_factory=dict)
    client_timestamp: datetime | None = None
    checksum: str | None = Field(default=None, min_length=64, max_length=64)


class AutosaveRead(ORMModel):
    id: uuid.UUID
    session_id: uuid.UUID
    session_item_id: uuid.UUID
    sequence_number: int
    response_payload: dict[str, Any]
    checksum: str
    status: str
    received_at: datetime


class NavigationRequest(BaseModel):
    target_position: int = Field(ge=0)
    flag_current_for_review: bool = False


class SessionEventCreate(BaseModel):
    event_type: str = Field(min_length=2, max_length=50)
    severity: Literal["INFO", "WARNING", "REVIEW"] = "INFO"
    source: Literal["CLIENT", "SERVER", "TEACHER"] = "CLIENT"
    client_sequence: int | None = Field(default=None, ge=1)
    occurred_at: datetime
    description: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeacherAction(BaseModel):
    action: Literal["PAUSE", "RESUME", "EXTEND", "CANCEL", "REOPEN"]
    reason: str = Field(min_length=3, max_length=1000)
    extra_minutes: int = Field(default=0, ge=0, le=600)


class AvailabilityRead(BaseModel):
    publication: PublicationRead
    effective_status: str
    attempts_used: int
    attempts_allowed: int
    can_start: bool
    reason: str | None = None


class MonitoringSummary(BaseModel):
    publication_id: uuid.UUID
    total_sessions: int
    status_counts: dict[str, int]
    active_sessions: int
    submitted_sessions: int
    attention_sessions: int
    average_progress: float
    last_updated_at: datetime
