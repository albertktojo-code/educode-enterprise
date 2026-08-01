from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field, model_validator


class EffectivenessRefreshRequest(BaseModel):
    period_start: date
    period_end: date
    evaluate_due: bool = True
    classroom_id: uuid.UUID | None = None
    window_code: str | None = None

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end deve ser posterior a period_start")
        if (self.period_end - self.period_start).days > 730:
            raise ValueError("O período não pode exceder 730 dias")
        if self.window_code and self.window_code not in {
            "immediate",
            "d7",
            "d15",
            "d30",
            "d60",
        }:
            raise ValueError("Janela longitudinal inválida")
        return self


class CheckpointEvaluationRequest(BaseModel):
    force: bool = False
    observed_progress_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    observed_score_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )


class ScheduleCheckpointsRequest(BaseModel):
    replace_pending: bool = False


class EffectivenessExportRequest(BaseModel):
    period_start: date
    period_end: date
    window_code: str | None = None
    dimension_type: str | None = Field(default=None, max_length=40)
