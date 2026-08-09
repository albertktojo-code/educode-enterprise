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


class CertificateIssue(BaseModel):
    student_user_id: UUID
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=2000)
    evidence_entry_ids: list[UUID] = Field(min_length=1, max_length=50)


class CertificateRevoke(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class CertificateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    verification_code: str
    evidence_entry_ids: list[str]
    status: str
    issued_at: datetime
    revoked_at: datetime | None
    revocation_reason: str


class CertificateStudentRead(BaseModel):
    id: UUID
    full_name: str
    email: str


class PublicCertificateEvidence(BaseModel):
    title: str
    assignment_type: str
    percentage: float


class PublicCertificateRead(BaseModel):
    title: str
    description: str
    verification_code: str
    status: str
    issued_at: datetime
    revoked_at: datetime | None
    revocation_reason: str
    student_name: str
    issuer_name: str
    organization_name: str
    evidence: list[PublicCertificateEvidence]
