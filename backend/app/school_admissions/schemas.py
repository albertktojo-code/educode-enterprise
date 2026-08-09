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
