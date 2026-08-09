from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

GuardianRole = Literal[
    "legal",
    "pedagogical",
    "financial",
    "emergency",
    "pickup",
]


class SchoolUnitCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    address: dict[str, str] = Field(default_factory=dict)


class SchoolUnitRead(SchoolUnitCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime


class CapacityWrite(BaseModel):
    maximum_seats: int = Field(ge=1, le=500)
    reservation_duration_minutes: int = Field(default=1440, ge=5, le=10080)
    waitlist_enabled: bool = True


class CapacitySnapshot(BaseModel):
    classroom_id: UUID
    classroom_name: str
    maximum_seats: int
    occupied_seats: int
    reserved_seats: int
    available_seats: int
    waitlist_size: int
    reservation_duration_minutes: int
    waitlist_enabled: bool


class StudentProfileInput(BaseModel):
    user_id: UUID | None = None
    legal_name: str = Field(min_length=2, max_length=180)
    social_name: str | None = Field(default=None, max_length=180)
    birth_date: date
    nationality: str = Field(default="Brasileira", min_length=2, max_length=80)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    previous_school: str | None = Field(default=None, max_length=180)
    emergency_contacts: list[dict[str, str]] = Field(default_factory=list, max_length=5)


class GuardianInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    phone: str = Field(min_length=8, max_length=40)
    relationship: str = Field(min_length=2, max_length=60)
    roles: list[GuardianRole] = Field(min_length=1, max_length=5)
    pickup_authorized: bool = False
    emergency_contact: bool = False
    address: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_roles(self) -> "GuardianInput":
        if len(set(self.roles)) != len(self.roles):
            raise ValueError("papéis do responsável não podem ser repetidos")
        return self


class EnrollmentApplicationCreate(BaseModel):
    school_unit_id: UUID
    classroom_id: UUID
    academic_year: int = Field(ge=2020, le=2100)
    intended_grade: str = Field(min_length=1, max_length=60)
    intended_shift: str = Field(min_length=2, max_length=30)
    student: StudentProfileInput
    guardians: list[GuardianInput] = Field(min_length=1, max_length=8)
    administrative_notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def unique_guardian_emails(self) -> "EnrollmentApplicationCreate":
        emails = [str(item.email).casefold() for item in self.guardians]
        if len(emails) != len(set(emails)):
            raise ValueError("responsáveis devem possuir e-mails distintos")
        if self.student.birth_date >= date.today():
            raise ValueError("data de nascimento deve estar no passado")
        return self


class EnrollmentApplicationRead(BaseModel):
    id: UUID
    student_profile_id: UUID
    student_name: str
    school_unit_id: UUID
    school_unit_name: str
    classroom_id: UUID
    classroom_name: str
    academic_year: int
    intended_grade: str
    intended_shift: str
    status: str
    submitted_at: datetime


class SeatDecisionRead(BaseModel):
    application_id: UUID
    outcome: Literal["reserved", "waitlisted", "already_reserved", "already_waitlisted"]
    capacity: CapacitySnapshot
    reservation_expires_at: datetime | None = None
    waitlist_position: int | None = None


class EnrollmentApprovalRead(BaseModel):
    application_id: UUID
    enrollment_id: UUID
    status: str
    classroom_participant_created: bool


class AdmissionsDashboard(BaseModel):
    applications: list[EnrollmentApplicationRead]
    capacities: list[CapacitySnapshot]
    submitted: int
    under_review: int
    waitlisted: int
    approved: int


DocumentReviewDecision = Literal[
    "under_review",
    "approved",
    "rejected",
    "illegible",
    "expired",
    "resubmission_requested",
]


class EnrollmentDocumentRequirementCreate(BaseModel):
    school_unit_id: UUID | None = None
    code: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=1000)
    is_required: bool = True
    accepted_mime_types: list[Literal["application/pdf", "image/jpeg", "image/png"]] = Field(
        default_factory=lambda: ["application/pdf", "image/jpeg", "image/png"],
        min_length=1,
        max_length=3,
    )
    max_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    retention_days: int = Field(default=1825, ge=30, le=36500)

    @model_validator(mode="after")
    def unique_mime_types(self) -> "EnrollmentDocumentRequirementCreate":
        if len(self.accepted_mime_types) != len(set(self.accepted_mime_types)):
            raise ValueError("tipos de arquivo não podem ser repetidos")
        return self


class EnrollmentDocumentRequirementRead(EnrollmentDocumentRequirementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime


class EnrollmentDocumentVersionRead(BaseModel):
    id: UUID
    version_number: int
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    uploaded_by_user_id: UUID
    created_at: datetime
    download_path: str


class EnrollmentDocumentReviewRead(BaseModel):
    id: UUID
    document_version_id: UUID
    decision: str
    note: str
    reviewed_by_user_id: UUID
    created_at: datetime


class EnrollmentDocumentRead(BaseModel):
    id: UUID
    application_id: UUID
    requirement_id: UUID
    requirement_code: str
    requirement_name: str
    status: str
    current_version_number: int
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    review_note: str
    expires_at: datetime | None
    versions: list[EnrollmentDocumentVersionRead]
    reviews: list[EnrollmentDocumentReviewRead]
    created_at: datetime
    updated_at: datetime


class EnrollmentDocumentChecklistItem(BaseModel):
    requirement: EnrollmentDocumentRequirementRead
    document: EnrollmentDocumentRead | None


class EnrollmentDocumentReviewWrite(BaseModel):
    decision: DocumentReviewDecision
    note: str = Field(default="", max_length=2000)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_review_note(self) -> "EnrollmentDocumentReviewWrite":
        if (
            self.decision in {"rejected", "illegible", "resubmission_requested"}
            and not self.note.strip()
        ):
            raise ValueError("informe a justificativa da decisão")
        if self.decision == "expired" and self.expires_at is None:
            raise ValueError("informe a data de vencimento")
        return self


class EnrollmentContractTemplateCreate(BaseModel):
    school_unit_id: UUID | None = None
    code: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=160)
    body_template: str = Field(min_length=20, max_length=50000)


class EnrollmentContractTemplateRead(EnrollmentContractTemplateCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    is_active: bool
    created_at: datetime


class EnrollmentContractGenerate(BaseModel):
    template_id: UUID
    guardian_profile_id: UUID


class EnrollmentContractVersionRead(BaseModel):
    id: UUID
    version_number: int
    rendered_content: str
    variables_snapshot: dict[str, str]
    content_sha256: str
    created_at: datetime


class EnrollmentContractAcceptanceRead(BaseModel):
    id: UUID
    contract_version_id: UUID
    guardian_profile_id: UUID
    accepted_name: str
    acceptance_hash: str
    accepted_at: datetime


class EnrollmentContractRead(BaseModel):
    id: UUID
    application_id: UUID
    template_id: UUID
    template_name: str
    guardian_profile_id: UUID | None
    guardian_name: str | None
    status: str
    current_version_number: int
    void_reason: str
    versions: list[EnrollmentContractVersionRead]
    acceptance: EnrollmentContractAcceptanceRead | None
    created_at: datetime
    updated_at: datetime


class EnrollmentContractAccept(BaseModel):
    confirmation: Literal["ACEITO"]
    accepted_name: str = Field(min_length=2, max_length=180)


class EnrollmentContractVoid(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


class EnrollmentGuardianOptionRead(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr


class ActiveEnrollmentRead(BaseModel):
    id: UUID
    student_profile_id: UUID
    student_name: str
    classroom_id: UUID
    classroom_name: str
    school_unit_id: UUID
    school_unit_name: str
    academic_year: int
    status: str


class EnrollmentRenewalCreate(BaseModel):
    target_classroom_id: UUID
    target_academic_year: int = Field(ge=2020, le=2100)
    reason: str = Field(default="", max_length=2000)


class EnrollmentTransferCreate(BaseModel):
    transfer_type: Literal["internal", "external"]
    destination_classroom_id: UUID | None = None
    destination_name: str = Field(default="", max_length=180)
    reason: str = Field(min_length=3, max_length=2000)

    @model_validator(mode="after")
    def validate_destination(self) -> "EnrollmentTransferCreate":
        if self.transfer_type == "internal" and self.destination_classroom_id is None:
            raise ValueError("selecione a turma de destino")
        if self.transfer_type == "external" and not self.destination_name.strip():
            raise ValueError("informe a instituição de destino")
        return self


class EnrollmentMovementReview(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_rejection_note(self) -> "EnrollmentMovementReview":
        if self.decision == "rejected" and not self.note.strip():
            raise ValueError("informe a justificativa da rejeição")
        return self


class EnrollmentRenewalRead(BaseModel):
    id: UUID
    enrollment_id: UUID
    student_name: str
    source_classroom_name: str
    target_classroom_id: UUID
    target_classroom_name: str
    target_academic_year: int
    status: str
    reason: str
    review_note: str
    result_application_id: UUID | None
    created_at: datetime


class EnrollmentTransferRead(BaseModel):
    id: UUID
    enrollment_id: UUID
    student_name: str
    source_classroom_name: str
    transfer_type: str
    destination_classroom_id: UUID | None
    destination_name: str
    status: str
    reason: str
    review_note: str
    result_application_id: UUID | None
    created_at: datetime


class EnrollmentMovementsDashboard(BaseModel):
    enrollments: list[ActiveEnrollmentRead]
    renewals: list[EnrollmentRenewalRead]
    transfers: list[EnrollmentTransferRead]
