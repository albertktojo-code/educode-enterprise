"""school admissions foundation

Revision ID: 0059_school_admissions
Revises: 0058_student_certificates
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0059_school_admissions"
down_revision: str | None = "0058_student_certificates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        "school_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column(
            "address", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_school_unit_org_code"),
    )
    op.create_index("ix_school_units_org_active", "school_units", ["organization_id", "is_active"])

    op.add_column("classrooms", sa.Column("school_unit_id", sa.Uuid()))
    op.add_column("classrooms", sa.Column("shift", sa.String(30)))
    op.create_foreign_key(
        "fk_classrooms_school_unit",
        "classrooms",
        "school_units",
        ["school_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_classrooms_school_unit_id", "classrooms", ["school_unit_id"])

    op.create_table(
        "institutional_staff_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("school_unit_id", sa.Uuid()),
        sa.Column("staff_role", sa.String(30), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "staff_role IN ('secretariat', 'coordinator', 'school_finance')",
            name="ck_staff_assignment_role",
        ),
        sa.ForeignKeyConstraint(["membership_id"], ["memberships.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["school_unit_id"], ["school_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "membership_id",
            "school_unit_id",
            "staff_role",
            name="uq_staff_assignment_scope",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_staff_assignments_org_role",
        "institutional_staff_assignments",
        ["organization_id", "staff_role", "is_active"],
    )

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("legal_name", sa.String(180), nullable=False),
        sa.Column("social_name", sa.String(180)),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("nationality", sa.String(80), server_default="Brasileira", nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(40)),
        sa.Column("previous_school", sa.String(180)),
        sa.Column(
            "emergency_contacts",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        *timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_student_profile_org_user"),
    )
    op.create_index(
        "ix_student_profiles_org_name", "student_profiles", ["organization_id", "legal_name"]
    )

    op.create_table(
        "guardian_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid()),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column(
            "address", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_guardian_profile_org_email"),
    )
    op.create_index(
        "ix_guardian_profiles_org_name", "guardian_profiles", ["organization_id", "full_name"]
    )

    op.create_table(
        "student_guardian_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("student_profile_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_profile_id", sa.Uuid(), nullable=False),
        sa.Column("relationship", sa.String(60), nullable=False),
        sa.Column(
            "roles", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("pickup_authorized", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("emergency_contact", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["guardian_profile_id"], ["guardian_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_profile_id", "guardian_profile_id", name="uq_student_guardian_link"
        ),
    )
    op.create_index(
        "ix_student_guardian_links_org",
        "student_guardian_links",
        ["organization_id", "student_profile_id"],
    )

    op.create_table(
        "student_enrollment_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("school_unit_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("student_profile_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("intended_grade", sa.String(60), nullable=False),
        sa.Column("intended_shift", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), server_default="submitted", nullable=False),
        sa.Column("administrative_notes", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("reviewed_by_user_id", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'under_review', 'waitlisted', "
            "'approved', 'rejected', 'cancelled')",
            name="ck_enrollment_application_status",
        ),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["school_unit_id"], ["school_units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_enrollment_applications_org_status",
        "student_enrollment_applications",
        ["organization_id", "status", "created_at"],
    )
    op.create_index(
        "ix_enrollment_applications_classroom",
        "student_enrollment_applications",
        ["organization_id", "classroom_id", "status"],
    )

    op.create_table(
        "class_capacity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("maximum_seats", sa.Integer(), nullable=False),
        sa.Column(
            "reservation_duration_minutes", sa.Integer(), server_default="1440", nullable=False
        ),
        sa.Column("waitlist_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("maximum_seats > 0", name="ck_class_capacity_positive"),
        sa.CheckConstraint(
            "reservation_duration_minutes BETWEEN 5 AND 10080",
            name="ck_class_capacity_reservation_duration",
        ),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_id", name="uq_class_capacity_classroom"),
    )
    op.create_index("ix_class_capacity_org", "class_capacity", ["organization_id", "classroom_id"])

    op.create_table(
        "student_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("student_profile_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column(
            "enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending_identity', 'active', 'transferred', 'cancelled')",
            name="ck_student_enrollment_status",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["student_enrollment_applications.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["student_profile_id"], ["student_profiles.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_student_enrollment_application"),
    )
    op.create_index(
        "ix_student_enrollments_org_classroom",
        "student_enrollments",
        ["organization_id", "classroom_id", "status"],
    )

    op.create_table(
        "seat_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'converted', 'expired', 'released')",
            name="ck_seat_reservation_status",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["student_enrollment_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_seat_reservation_application"),
    )
    op.create_index(
        "ix_seat_reservations_classroom_active",
        "seat_reservations",
        ["organization_id", "classroom_id", "status", "expires_at"],
    )

    op.create_table(
        "enrollment_waitlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(30), server_default="waiting", nullable=False),
        sa.Column("offered_until", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint("position > 0", name="ck_enrollment_waitlist_position"),
        sa.CheckConstraint(
            "status IN ('waiting', 'offered', 'accepted', 'declined', 'cancelled')",
            name="ck_enrollment_waitlist_status",
        ),
        sa.ForeignKeyConstraint(
            ["application_id"], ["student_enrollment_applications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_enrollment_waitlist_application"),
    )
    op.create_index(
        "ix_enrollment_waitlists_classroom_position",
        "enrollment_waitlists",
        ["organization_id", "classroom_id", "status", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_enrollment_waitlists_classroom_position", table_name="enrollment_waitlists")
    op.drop_table("enrollment_waitlists")
    op.drop_index("ix_seat_reservations_classroom_active", table_name="seat_reservations")
    op.drop_table("seat_reservations")
    op.drop_index("ix_student_enrollments_org_classroom", table_name="student_enrollments")
    op.drop_table("student_enrollments")
    op.drop_index("ix_class_capacity_org", table_name="class_capacity")
    op.drop_table("class_capacity")
    op.drop_index(
        "ix_enrollment_applications_classroom", table_name="student_enrollment_applications"
    )
    op.drop_index(
        "ix_enrollment_applications_org_status", table_name="student_enrollment_applications"
    )
    op.drop_table("student_enrollment_applications")
    op.drop_index("ix_student_guardian_links_org", table_name="student_guardian_links")
    op.drop_table("student_guardian_links")
    op.drop_index("ix_guardian_profiles_org_name", table_name="guardian_profiles")
    op.drop_table("guardian_profiles")
    op.drop_index("ix_student_profiles_org_name", table_name="student_profiles")
    op.drop_table("student_profiles")
    op.drop_index("ix_staff_assignments_org_role", table_name="institutional_staff_assignments")
    op.drop_table("institutional_staff_assignments")
    op.drop_index("ix_classrooms_school_unit_id", table_name="classrooms")
    op.drop_constraint("fk_classrooms_school_unit", "classrooms", type_="foreignkey")
    op.drop_column("classrooms", "shift")
    op.drop_column("classrooms", "school_unit_id")
    op.drop_index("ix_school_units_org_active", table_name="school_units")
    op.drop_table("school_units")
