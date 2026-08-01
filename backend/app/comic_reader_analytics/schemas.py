from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .policies import ALLOWED_EVENT_TYPES


class ReaderEventCreate(BaseModel):
    client_event_id: str = Field(min_length=8, max_length=80)
    release_id: uuid.UUID
    presentation_session_id: uuid.UUID | None = None
    session_key: str = Field(min_length=8, max_length=80)
    event_type: str
    page_number: int | None = Field(default=None, ge=1)
    panel_number: int | None = Field(default=None, ge=1)
    duration_ms: int = Field(default=0, ge=0, le=1_800_000)
    sequence: int = Field(default=0, ge=0)
    properties: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def normalize(self):
        self.event_type = self.event_type.upper()
        if self.event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError("Invalid reader analytics event type")
        if len(json.dumps(self.properties, default=str, ensure_ascii=False)) > 8192:
            raise ValueError("Reader analytics event properties exceed 8 KiB")
        return self


class ReaderEventBatch(BaseModel):
    events: list[ReaderEventCreate] = Field(min_length=1, max_length=100)


class AnalyticsRefreshRequest(BaseModel):
    period_start: date = Field(default_factory=lambda: date.today() - timedelta(days=30))
    period_end: date = Field(default_factory=date.today)
    release_id: uuid.UUID | None = None
    classroom_id: uuid.UUID | None = None
    generate_alerts: bool = True

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        if (self.period_end - self.period_start).days > 366:
            raise ValueError("Analytics period cannot exceed 366 days")
        return self


class AlertGenerationRequest(BaseModel):
    period_start: date = Field(default_factory=lambda: date.today() - timedelta(days=30))
    period_end: date = Field(default_factory=date.today)
    release_id: uuid.UUID | None = None
    minimum_active_seconds: int = Field(default=120, ge=30, le=7200)
    maximum_progress_percent: float = Field(default=35.0, ge=0, le=100)
    minimum_sessions: int = Field(default=2, ge=1, le=20)
