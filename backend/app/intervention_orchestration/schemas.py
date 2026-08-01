from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ProposalCreate(BaseModel):
    use_ai: bool = True
    due_days: int = Field(default=7, ge=1, le=90)
    evaluation_days: int = Field(default=7, ge=1, le=90)
    teacher_note: str = Field(default="", max_length=4000)
    target_mastery: float = Field(default=0.75, ge=0.1, le=1.0)


class ProposalReview(BaseModel):
    decision: str
    review_notes: str = Field(default="", max_length=4000)
    edited_title: str | None = Field(default=None, min_length=3, max_length=240)
    edited_rationale: str | None = Field(
        default=None,
        min_length=3,
        max_length=10000,
    )
    edited_materials: list[dict[str, Any]] | None = Field(
        default=None,
        max_length=20,
    )
    due_days: int = Field(default=7, ge=1, le=90)
    evaluation_days: int = Field(default=7, ge=1, le=90)
    create_adaptive_path: bool = True

    @model_validator(mode="after")
    def normalize(self):
        self.decision = self.decision.lower()
        if self.decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        if self.decision == "rejected" and not self.review_notes.strip():
            raise ValueError("A rejeição exige uma justificativa.")
        if self.edited_materials is not None:
            allowed_types = {
                "comic_reread",
                "accessible_resource",
                "assignment",
                "teacher_feedback",
            }
            for index, item in enumerate(self.edited_materials):
                action_type = item.get("type")
                title = item.get("title")
                if action_type not in allowed_types:
                    raise ValueError(
                        f"Tipo de ação inválido na posição {index + 1}."
                    )
                if not isinstance(title, str) or len(title.strip()) < 3:
                    raise ValueError(
                        f"Título inválido na posição {index + 1}."
                    )
        return self


class InterventionTransition(BaseModel):
    target_status: str
    notes: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def normalize(self):
        self.target_status = self.target_status.lower()
        if self.target_status not in {"active", "completed", "canceled"}:
            raise ValueError("Invalid intervention target status")
        if self.target_status == "canceled" and not self.notes.strip():
            raise ValueError("O cancelamento exige uma justificativa.")
        return self


class InterventionComplete(BaseModel):
    result_summary: str = Field(min_length=3, max_length=10000)
    teacher_notes: str = Field(default="", max_length=5000)
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


class StudentAcknowledgement(BaseModel):
    note: str = Field(default="", max_length=2000)
