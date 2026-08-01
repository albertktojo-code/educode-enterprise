from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    ANCHOR_TYPES,
    ASSIGNMENT_ROLES,
    CHECKLIST_CATEGORIES,
    DECISIONS,
    TARGET_TYPES,
)


class ReviewSessionCreate(BaseModel):
    comic_project_id: uuid.UUID
    comic_version_id: uuid.UUID | None = None
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=3000)
    due_at: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ReviewSessionRead(ReviewSessionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class AssignmentCreate(BaseModel):
    reviewer_user_id: uuid.UUID
    reviewer_role: str
    required: bool = True
    due_at: datetime | None = None

    @model_validator(mode="after")
    def validate_role(self):
        self.reviewer_role = self.reviewer_role.upper()
        if self.reviewer_role not in ASSIGNMENT_ROLES:
            raise ValueError("Invalid reviewer role")
        return self


class ThreadCreate(BaseModel):
    anchor_type: str
    page_id: uuid.UUID | None = None
    panel_id: uuid.UUID | None = None
    layer_id: uuid.UUID | None = None
    title: str = Field(min_length=2, max_length=180)
    body: str = Field(min_length=2, max_length=5000)
    severity: str = "COMMENT"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_anchor(self):
        self.anchor_type = self.anchor_type.upper()
        if self.anchor_type not in ANCHOR_TYPES:
            raise ValueError("Invalid anchor type")
        if self.anchor_type == "PAGE" and not self.page_id:
            raise ValueError("PAGE requires page_id")
        if self.anchor_type == "PANEL" and not self.panel_id:
            raise ValueError("PANEL requires panel_id")
        if self.anchor_type == "LAYER" and not self.layer_id:
            raise ValueError("LAYER requires layer_id")
        return self


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    mentions: list[uuid.UUID] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class ThreadResolution(BaseModel):
    note: str = Field(min_length=2, max_length=2000)


class ChangeRequestCreate(BaseModel):
    thread_id: uuid.UUID | None = None
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=5000)
    priority: str = "NORMAL"
    target_snapshot: dict[str, Any] = Field(default_factory=dict)


class ChecklistItemCreate(BaseModel):
    category: str
    code: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=2000)
    required: bool = True
    status: str = "PENDING"
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_category(self):
        self.category = self.category.upper()
        if self.category not in CHECKLIST_CATEGORIES:
            raise ValueError("Invalid checklist category")
        return self


class ChecklistCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    version: str = Field(min_length=1, max_length=40)
    items: list[ChecklistItemCreate] = Field(min_length=1)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=3, max_length=180)
    minimum_approvals: int = Field(default=1, ge=1, le=20)
    required_roles: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class DecisionCreate(BaseModel):
    decision: str
    reviewer_role: str
    note: str = Field(default="", max_length=3000)

    @model_validator(mode="after")
    def validate_decision(self):
        self.decision = self.decision.upper()
        self.reviewer_role = self.reviewer_role.upper()
        if self.decision not in DECISIONS:
            raise ValueError("Invalid decision")
        if self.reviewer_role not in ASSIGNMENT_ROLES:
            raise ValueError("Invalid reviewer role")
        if self.decision in {"REQUEST_CHANGES", "REJECT"} and len(self.note.strip()) < 3:
            raise ValueError("A justification is required")
        return self


class ReleaseCreate(BaseModel):
    comic_project_id: uuid.UUID
    source_version_id: uuid.UUID
    review_session_id: uuid.UUID
    release_name: str = Field(min_length=3, max_length=180)
    release_notes: str = Field(default="", max_length=5000)
    snapshot: dict[str, Any]
    scheduled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicationTargetCreate(BaseModel):
    target_type: str
    target_id: uuid.UUID | None = None
    availability_from: datetime | None = None
    availability_until: datetime | None = None
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_target(self):
        self.target_type = self.target_type.upper()
        if self.target_type not in TARGET_TYPES:
            raise ValueError("Invalid publication target")
        if self.target_type not in {"INSTITUTIONAL_LIBRARY", "PUBLIC_CATALOG"} and not self.target_id:
            raise ValueError("This target type requires target_id")
        if self.availability_from and self.availability_until and self.availability_until <= self.availability_from:
            raise ValueError("availability_until must be after availability_from")
        return self
