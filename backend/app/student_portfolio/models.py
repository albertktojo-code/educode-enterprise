from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentPortfolioEntry(Base):
    __tablename__ = "student_portfolio_entries"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "student_user_id",
            "assignment_id",
            name="uq_student_portfolio_assignment",
        ),
        CheckConstraint(
            "char_length(reflection) <= 2000", name="ck_student_portfolio_reflection_length"
        ),
        CheckConstraint("revision >= 1", name="ck_student_portfolio_revision"),
        Index(
            "ix_student_portfolio_owner_created", "organization_id", "student_user_id", "created_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    student_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[UUID] = mapped_column(
        ForeignKey("material_assignments.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("student_attempts.id", ondelete="RESTRICT"), nullable=False
    )
    title_snapshot: Mapped[str] = mapped_column(String(240), nullable=False)
    assignment_type_snapshot: Mapped[str] = mapped_column(String(40), nullable=False)
    percentage_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    reflection: Mapped[str] = mapped_column(Text, default="", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed_at_snapshot: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StudentCertificate(Base):
    __tablename__ = "student_certificates"
    __table_args__ = (
        UniqueConstraint("verification_code", name="uq_student_certificate_code"),
        Index("ix_student_certificates_owner", "organization_id", "student_user_id", "issued_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    student_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    issued_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verification_code: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_entry_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    revocation_reason: Mapped[str] = mapped_column(String(300), default="", nullable=False)
