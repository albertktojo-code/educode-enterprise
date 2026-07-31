from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"


def read_backend(relative_path: str) -> str:
    return (BACKEND / relative_path).read_text(encoding="utf-8")


def read_frontend(relative_path: str) -> str:
    if not FRONTEND.exists():
        pytest.skip("Frontend não é montado no container do backend.")
    return (FRONTEND / relative_path).read_text(encoding="utf-8")


def test_monitoring_reuses_delivery_and_hq_state_without_new_table() -> None:
    service = read_backend("app/comic_page_editor/activity_delivery.py")
    for marker in (
        "AssessmentPublication",
        "AssessmentTarget",
        "AssessmentSession",
        "AssessmentSessionEvent",
        "AssessmentSessionItem",
        "HQStudentExperienceState",
    ):
        assert marker in service
    monitor = service.split("async def monitoring_summary", maxsplit=1)[1]
    assert "__tablename__" not in service
    assert "response_payload" not in monitor
    assert "activity.answer_key" not in monitor


def test_monitoring_is_tenant_scoped_private_and_filterable() -> None:
    service = read_backend("app/comic_page_editor/activity_delivery.py")
    router = read_backend("app/comic_page_editor/router.py")
    assert service.count("actor.organization_id") >= 8
    assert '"answers_exposed": False' in service
    assert '"device_details_exposed": False' in service
    assert '"ranking_enabled": False' in service
    assert "classroom_id: uuid.UUID | None" in router
    assert "student_id: uuid.UUID | None" in router
    assert "status_filter" in router
    assert "require_role(actor,EDITOR_ROLES)" in router


def test_teacher_commands_use_canonical_audit_and_events() -> None:
    router = read_backend("app/assessment_delivery/router.py")
    schemas = read_backend("app/assessment_delivery/schemas.py")
    for marker in (
        "GRANT_ATTEMPT",
        "SEND_MESSAGE",
        "RELEASE_HINT",
        "RELEASE_ANSWER_KEY",
    ):
        assert marker in router
        assert marker in schemas
    assert "AssessmentTarget" in router
    assert "UserNotification" in router
    assert "append_domain_audit" in router
    assert 'module_name="assessment_delivery"' in router
    assert 'payload.event_type.upper().startswith("TEACHER_")' in router


def test_frontend_uses_authenticated_polling_and_registered_route() -> None:
    page = read_frontend(
        "src/features/comicPageEditor/TeacherMonitoringPage.tsx"
    )
    api = read_frontend("src/features/comicPageEditor/api.ts")
    routes = read_frontend("src/features/comicPageEditor/routes.tsx")
    assert "setInterval" in page
    assert "comicPageEditorApi.monitorActivityDelivery" in page
    assert "aria-live" in page
    assert "fetch(" not in page
    assert 'from "../../lib/api"' in api
    assert "/teacher/comic-studio/monitoring/:deliveryId" in routes


def test_student_help_and_teacher_support_stay_in_canonical_session_events() -> None:
    api = read_frontend("src/features/hqStudentExperience/api.ts")
    page = read_frontend(
        "src/features/hqStudentExperience/"
        "HQStudentExperiencePage.tsx"
    )
    service = read_backend(
        "app/comic_page_editor/student_experience.py"
    )
    assert "STUDENT_HELP_REQUESTED" in api
    assert "/assessment-delivery/sessions/" in api
    assert "teacher_support" in page
    assert "released_answer_key" in page
    assert "AssessmentSessionEvent" in service


def test_version_and_build_identifier_are_16_11_6() -> None:
    config = read_backend("app/core/config.py")
    pyproject = read_backend("pyproject.toml")
    assert 'app_version: str = "0.16.11.6"' in config
    assert "sprint-16.11.6-hq-teacher-monitoring" in config
    assert 'version = "0.16.11.6"' in pyproject
