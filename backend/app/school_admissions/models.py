from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApplicationStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    WAITLISTED = "waitlisted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class EnrollmentStatus(StrEnum):
    PENDING_IDENTITY = "pending_identity"
    ACTIVE = "active"
    TRANSFERRED = "transferred"
    CANCELLED = "cancelled"


class ReservationStatus(StrEnum):
    ACTIVE = "active"
    CONVERTED = "converted"
    EXPIRED = "expired"
    RELEASED = "released"


class WaitlistStatus(StrEnum):
    WAITING = "waiting"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class EnrollmentDocumentStatus(StrEnum):
    MISSING = "missing"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ILLEGIBLE = "illegible"
    EXPIRED = "expired"
    RESUBMISSION_REQUESTED = "resubmission_requested"


class EnrollmentContractStatus(StrEnum):
    GENERATED = "generated"
    ACCEPTED = "accepted"
    VOIDED = "voided"


class EnrollmentMovementStatus(StrEnum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class EnrollmentTransferType(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class SchoolUnit(Base):
    __tablename__ = "school_units"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_school_unit_org_code"),
        Index("ix_school_units_org_active", "organization_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class InstitutionalStaffAssignment(Base):
    __tablename__ = "institutional_staff_assignments"
    __table_args__ = (
        UniqueConstraint(
            "membership_id",
            "school_unit_id",
            "staff_role",
            name="uq_staff_assignment_scope",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "staff_role IN ('secretariat', 'coordinator', 'school_finance')",
            name="ck_staff_assignment_role",
        ),
        Index("ix_staff_assignments_org_role", "organization_id", "staff_role", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False
    )
    school_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("school_units.id", ondelete="CASCADE")
    )
    staff_role: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_student_profile_org_user"),
        Index("ix_student_profiles_org_name", "organization_id", "legal_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    legal_name: Mapped[str] = mapped_column(String(180), nullable=False)
    social_name: Mapped[str | None] = mapped_column(String(180))
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    nationality: Mapped[str] = mapped_column(String(80), default="Brasileira", nullable=False)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(40))
    previous_school: Mapped[str | None] = mapped_column(String(180))
    emergency_contacts: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GuardianProfile(Base):
    __tablename__ = "guardian_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_guardian_profile_org_email"),
        Index("ix_guardian_profiles_org_name", "organization_id", "full_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StudentGuardianLink(Base):
    __tablename__ = "student_guardian_links"
    __table_args__ = (
        UniqueConstraint(
            "student_profile_id", "guardian_profile_id", name="uq_student_guardian_link"
        ),
        Index("ix_student_guardian_links_org", "organization_id", "student_profile_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    student_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False
    )
    guardian_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("guardian_profiles.id", ondelete="CASCADE"), nullable=False
    )
    relationship: Mapped[str] = mapped_column(String(60), nullable=False)
    roles: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    pickup_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    emergency_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StudentEnrollmentApplication(Base):
    __tablename__ = "student_enrollment_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'submitted', 'under_review', 'waitlisted', "
            "'approved', 'rejected', 'cancelled')",
            name="ck_enrollment_application_status",
        ),
        Index(
            "ix_enrollment_applications_org_status",
            "organization_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_enrollment_applications_classroom",
            "organization_id",
            "classroom_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("school_units.id", ondelete="RESTRICT"), nullable=False
    )
    classroom_id: Mapped[UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False
    )
    student_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    submitted_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    intended_grade: Mapped[str] = mapped_column(String(60), nullable=False)
    intended_shift: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=ApplicationStatus.SUBMITTED)
    administrative_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_student_enrollment_application"),
        CheckConstraint(
            "status IN ('pending_identity', 'active', 'transferred', 'cancelled')",
            name="ck_student_enrollment_status",
        ),
        Index(
            "ix_student_enrollments_org_classroom",
            "organization_id",
            "classroom_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="RESTRICT"), nullable=False
    )
    student_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    classroom_id: Mapped[UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ClassCapacity(Base):
    __tablename__ = "class_capacity"
    __table_args__ = (
        UniqueConstraint("classroom_id", name="uq_class_capacity_classroom"),
        CheckConstraint("maximum_seats > 0", name="ck_class_capacity_positive"),
        CheckConstraint(
            "reservation_duration_minutes BETWEEN 5 AND 10080",
            name="ck_class_capacity_reservation_duration",
        ),
        Index("ix_class_capacity_org", "organization_id", "classroom_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    classroom_id: Mapped[UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False
    )
    maximum_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    reservation_duration_minutes: Mapped[int] = mapped_column(Integer, default=1440, nullable=False)
    waitlist_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SeatReservation(Base):
    __tablename__ = "seat_reservations"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_seat_reservation_application"),
        CheckConstraint(
            "status IN ('active', 'converted', 'expired', 'released')",
            name="ck_seat_reservation_status",
        ),
        Index(
            "ix_seat_reservations_classroom_active",
            "organization_id",
            "classroom_id",
            "status",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="CASCADE"), nullable=False
    )
    classroom_id: Mapped[UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), default=ReservationStatus.ACTIVE)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentWaitlist(Base):
    __tablename__ = "enrollment_waitlists"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_enrollment_waitlist_application"),
        CheckConstraint("position > 0", name="ck_enrollment_waitlist_position"),
        CheckConstraint(
            "status IN ('waiting', 'offered', 'accepted', 'declined', 'cancelled')",
            name="ck_enrollment_waitlist_status",
        ),
        Index(
            "ix_enrollment_waitlists_classroom_position",
            "organization_id",
            "classroom_id",
            "status",
            "position",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="CASCADE"), nullable=False
    )
    classroom_id: Mapped[UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=WaitlistStatus.WAITING)
    offered_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentDocumentRequirement(Base):
    __tablename__ = "enrollment_document_requirements"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "school_unit_id",
            "code",
            name="uq_enrollment_document_requirement_scope",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint("max_size_bytes > 0", name="ck_enrollment_requirement_size"),
        CheckConstraint("retention_days > 0", name="ck_enrollment_requirement_retention"),
        Index(
            "ix_enrollment_document_requirements_org_active",
            "organization_id",
            "is_active",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("school_units.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepted_mime_types: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    max_size_bytes: Mapped[int] = mapped_column(Integer, default=10 * 1024 * 1024, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=1825, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentDocument(Base):
    __tablename__ = "enrollment_documents"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "requirement_id", name="uq_enrollment_document_application_slot"
        ),
        CheckConstraint(
            "status IN ('submitted', 'under_review', 'approved', 'rejected', "
            "'illegible', 'expired', 'resubmission_requested')",
            name="ck_enrollment_document_status",
        ),
        CheckConstraint("current_version_number > 0", name="ck_enrollment_document_version"),
        Index(
            "ix_enrollment_documents_org_status",
            "organization_id",
            "status",
            "updated_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_document_requirements.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default=EnrollmentDocumentStatus.SUBMITTED, nullable=False
    )
    current_version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentDocumentVersion(Base):
    __tablename__ = "enrollment_document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_enrollment_document_version"),
        UniqueConstraint("storage_key", name="uq_enrollment_document_storage_key"),
        CheckConstraint("version_number > 0", name="ck_enrollment_document_version_positive"),
        CheckConstraint("size_bytes > 0", name="ck_enrollment_document_file_size"),
        Index(
            "ix_enrollment_document_versions_org_document",
            "organization_id",
            "document_id",
            "version_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_documents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnrollmentDocumentReview(Base):
    __tablename__ = "enrollment_document_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('under_review', 'approved', 'rejected', 'illegible', "
            "'expired', 'resubmission_requested')",
            name="ck_enrollment_document_review_decision",
        ),
        Index(
            "ix_enrollment_document_reviews_org_document",
            "organization_id",
            "document_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_documents.id", ondelete="CASCADE"), nullable=False
    )
    document_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_document_versions.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnrollmentContractTemplate(Base):
    __tablename__ = "enrollment_contract_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "school_unit_id",
            "code",
            name="uq_enrollment_contract_template_scope",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_enrollment_contract_templates_org_active", "organization_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    school_unit_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("school_units.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentContract(Base):
    __tablename__ = "enrollment_contracts"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_enrollment_contract_application"),
        CheckConstraint(
            "status IN ('generated', 'accepted', 'voided')",
            name="ck_enrollment_contract_status",
        ),
        CheckConstraint("current_version_number > 0", name="ck_enrollment_contract_version"),
        Index("ix_enrollment_contracts_org_status", "organization_id", "status", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="RESTRICT"), nullable=False
    )
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_contract_templates.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=EnrollmentContractStatus.GENERATED)
    current_version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    generated_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    voided_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    void_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentContractVersion(Base):
    __tablename__ = "enrollment_contract_versions"
    __table_args__ = (
        UniqueConstraint("contract_id", "version_number", name="uq_enrollment_contract_version"),
        CheckConstraint("version_number > 0", name="ck_enrollment_contract_version_positive"),
        Index(
            "ix_enrollment_contract_versions_org_contract",
            "organization_id",
            "contract_id",
            "version_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_contracts.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    template_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_content: Mapped[str] = mapped_column(Text, nullable=False)
    variables_snapshot: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnrollmentContractAcceptance(Base):
    __tablename__ = "enrollment_contract_acceptances"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_enrollment_contract_acceptance"),
        Index(
            "ix_enrollment_contract_acceptances_org_guardian",
            "organization_id",
            "guardian_profile_id",
            "accepted_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_contracts.id", ondelete="RESTRICT"), nullable=False
    )
    contract_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("enrollment_contract_versions.id", ondelete="RESTRICT"), nullable=False
    )
    guardian_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("guardian_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    accepted_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    accepted_name: Mapped[str] = mapped_column(String(180), nullable=False)
    acceptance_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnrollmentRenewalRequest(Base):
    __tablename__ = "enrollment_renewal_requests"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "target_academic_year", name="uq_enrollment_renewal_year"
        ),
        CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'cancelled')",
            name="ck_enrollment_renewal_status",
        ),
        Index("ix_enrollment_renewals_org_status", "organization_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    target_classroom_id: Mapped[UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"), nullable=False
    )
    target_academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=EnrollmentMovementStatus.SUBMITTED)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    review_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    result_application_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EnrollmentTransferRequest(Base):
    __tablename__ = "enrollment_transfer_requests"
    __table_args__ = (
        CheckConstraint(
            "transfer_type IN ('internal', 'external')", name="ck_enrollment_transfer_type"
        ),
        CheckConstraint(
            "status IN ('submitted', 'approved', 'rejected', 'cancelled')",
            name="ck_enrollment_transfer_status",
        ),
        CheckConstraint(
            "(transfer_type = 'internal' AND destination_classroom_id IS NOT NULL) OR "
            "(transfer_type = 'external' AND destination_name <> '')",
            name="ck_enrollment_transfer_destination",
        ),
        Index("ix_enrollment_transfers_org_status", "organization_id", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    enrollment_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_enrollments.id", ondelete="RESTRICT"), nullable=False
    )
    transfer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    destination_classroom_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT")
    )
    destination_name: Mapped[str] = mapped_column(String(180), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=EnrollmentMovementStatus.SUBMITTED)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    review_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    result_application_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("student_enrollment_applications.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
