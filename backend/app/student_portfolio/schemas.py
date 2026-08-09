from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PortfolioEntryCreate(BaseModel):
    assignment_id: UUID
    reflection: str = Field(default="", max_length=2000)


class PortfolioEntryUpdate(BaseModel):
    reflection: str = Field(max_length=2000)


class PortfolioEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assignment_id: UUID
    attempt_id: UUID
    title_snapshot: str
    assignment_type_snapshot: str
    percentage_snapshot: float
    reflection: str
    revision: int
    completed_at_snapshot: datetime | None
    created_at: datetime
    updated_at: datetime


class PortfolioProductionRead(BaseModel):
    id: UUID
    kind: str
    title: str
    description: str
    status: str
    updated_at: datetime
    route: str
