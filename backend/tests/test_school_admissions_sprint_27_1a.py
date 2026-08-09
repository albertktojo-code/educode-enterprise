from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db import model_registry
from app.school_admissions.schemas import EnrollmentApplicationCreate, StudentProfileInput

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def valid_payload() -> dict[str, object]:
    return {
        "school_unit_id": uuid4(),
        "classroom_id": uuid4(),
        "academic_year": 2027,
        "intended_grade": "6º ano",
        "intended_shift": "morning",
        "student": {
            "legal_name": "Estudante Teste",
            "birth_date": date.today() - timedelta(days=3650),
        },
        "guardians": [
            {
                "full_name": "Responsável Teste",
                "email": "responsavel@example.com",
                "phone": "11999999999",
                "relationship": "mãe",
                "roles": ["legal", "pedagogical"],
            }
        ],
    }


def test_application_schema_minimizes_sensitive_data_and_validates_guardians() -> None:
    application = EnrollmentApplicationCreate(**valid_payload())
    assert application.student.legal_name == "Estudante Teste"
    assert application.guardians[0].roles == ["legal", "pedagogical"]
    assert "cpf" not in StudentProfileInput.model_fields
    assert "rg" not in StudentProfileInput.model_fields

    future_birth = valid_payload()
    future_birth["student"] = {
        "legal_name": "Estudante Teste",
        "birth_date": date.today() + timedelta(days=1),
    }
    with pytest.raises(ValidationError):
        EnrollmentApplicationCreate(**future_birth)

    duplicate_guardian = valid_payload()
    duplicate_guardian["guardians"] = [
        duplicate_guardian["guardians"][0],
        duplicate_guardian["guardians"][0],
    ]
    with pytest.raises(ValidationError):
        EnrollmentApplicationCreate(**duplicate_guardian)


def test_foundation_models_are_registered_in_canonical_metadata() -> None:
    expected = {
        "school_units",
        "institutional_staff_assignments",
        "student_profiles",
        "guardian_profiles",
        "student_guardian_links",
        "student_enrollment_applications",
        "student_enrollments",
        "class_capacity",
        "seat_reservations",
        "enrollment_waitlists",
    }
    assert expected <= set(model_registry.registered_table_names())
    for table_name in expected:
        table = model_registry.Base.metadata.tables[table_name]
        assert "organization_id" in table.columns


def test_migration_is_manual_reversible_and_based_on_real_head() -> None:
    migration = (BACKEND / "alembic/versions/0059_school_admissions_foundation.py").read_text(
        encoding="utf-8"
    )
    assert 'revision: str = "0059_school_admissions"' in migration
    assert 'down_revision: str | None = "0058_student_certificates"' in migration
    assert 'op.create_table(\n        "school_units"' in migration
    assert '"ck_class_capacity_positive"' in migration
    assert '"uq_seat_reservation_application"' in migration
    assert 'ondelete="RESTRICT"' in migration
    assert 'op.drop_table("school_units")' in migration
    assert "op.execute" not in migration


def test_capacity_and_approval_services_lock_scope_and_remain_idempotent() -> None:
    services = (BACKEND / "app/school_admissions/services.py").read_text(encoding="utf-8")
    assert "statement.with_for_update()" in services
    assert "StudentEnrollment.organization_id == organization_id" in services
    assert "SeatReservation.organization_id == organization_id" in services
    assert "EnrollmentWaitlist.organization_id == organization_id" in services
    assert "existing = await session.scalar(" in services
    assert "if existing is not None:" in services
    assert 'action="enrollment.application.approved"' in services
    assert 'notification_type="enrollment_approved"' in services
    assert 'role="student"' in services


def test_rbac_feature_flags_and_routes_are_connected() -> None:
    policies = (BACKEND / "app/school_admissions/policies.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/school_admissions/router.py").read_text(encoding="utf-8")
    seed = (BACKEND / "app/db/seed.py").read_text(encoding="utf-8")
    api_router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    assert 'ADMISSIONS_FLAG = "SCHOOL_ADMISSIONS_ENABLED"' in policies
    assert "InstitutionalStaffAssignment.organization_id == actor.organization_id" in policies
    assert "InstitutionalStaffAssignment.membership_id == actor.membership_id" in policies
    assert '@router.post("/applications"' in router
    assert '"/applications/{application_id}/reserve"' in router
    assert '"/applications/{application_id}/approve"' in router
    assert "school_admissions_router" in api_router
    for flag in (
        "SCHOOL_ADMISSIONS_ENABLED",
        "SCHOOL_SECRETARIAT_ENABLED",
        "SCHOOL_REPORT_CARDS_ENABLED",
        "SCHOOL_EVENTS_ENABLED",
        "SCHOOL_ANNOUNCEMENTS_ENABLED",
        "SCHOOL_FINANCE_ENABLED",
        "FAMILY_PORTAL_ENABLED",
    ):
        assert f'("{flag}", False' in seed


def test_secretariat_frontend_uses_central_api_and_accessibility_states() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "components/AppLayout.tsx").read_text(encoding="utf-8")
    page = (FRONTEND / "pages/SchoolSecretariatPage.tsx").read_text(encoding="utf-8")
    admissions_page = (FRONTEND / "pages/SchoolAdmissionsPage.tsx").read_text(encoding="utf-8")
    capacity_page = (FRONTEND / "pages/SchoolCapacityPage.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "features/schoolAdmissions/api.ts").read_text(encoding="utf-8")
    assert 'path="secretaria"' in app
    assert 'to: "/secretaria"' in layout
    assert "manageOnly: true" in layout
    assert "schoolAdmissionsApi.dashboard" in page
    assert 'aria-live="polite"' in page
    assert "Nenhuma capacidade configurada" in capacity_page
    assert "Nenhuma pré-matrícula recebida" in admissions_page
    assert "api.get<AdmissionsDashboard>" in api
    assert "fetch(" not in api


def test_financial_domains_are_not_introduced_by_admissions_foundation() -> None:
    model = (BACKEND / "app/school_admissions/models.py").read_text(encoding="utf-8")
    migration = (BACKEND / "alembic/versions/0059_school_admissions_foundation.py").read_text(
        encoding="utf-8"
    )
    assert "school_invoices" not in model + migration
    assert "platform_invoices" not in model + migration
    assert "platform_billing" not in model + migration
