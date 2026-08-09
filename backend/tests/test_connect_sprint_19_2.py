from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.delivery import ClassroomAnnouncementCreate

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_announcement_payload_requires_internal_destination_and_content() -> None:
    valid = ClassroomAnnouncementCreate(
        classroom_ids=[uuid4()],
        title="Aviso da semana",
        message="Confiram as atividades publicadas.",
    )
    assert valid.action_path == "/aluno"

    for payload in (
        {
            "classroom_ids": [],
            "title": "Aviso",
            "message": "Mensagem",
        },
        {
            "classroom_ids": [uuid4()],
            "title": "   ",
            "message": "Mensagem",
        },
        {
            "classroom_ids": [uuid4()],
            "title": "Aviso",
            "message": "Mensagem",
            "action_path": "https://example.com",
        },
        {
            "classroom_ids": [uuid4()],
            "title": "Aviso",
            "message": "Mensagem",
            "action_path": "//example.com",
        },
    ):
        with pytest.raises(ValidationError):
            ClassroomAnnouncementCreate(**payload)


def test_announcement_endpoint_is_scoped_deduplicated_and_audited() -> None:
    router = (BACKEND / "app/api/v1/routes_delivery.py").read_text(encoding="utf-8")
    assert '"/connect/announcements"' in router
    assert "require_roles(*TEACHER_ROLES)" in router
    assert "Classroom.organization_id == organization_id" in router
    assert "Classroom.is_active.is_(True)" in router
    assert 'ClassroomEnrollment.role == "student"' in router
    assert "Membership.organization_id == organization_id" in router
    assert "Membership.is_active.is_(True)" in router
    assert "list(dict.fromkeys(data.classroom_ids))" in router
    assert "list(\n        dict.fromkeys(" in router
    assert 'notification_type="classroom_announcement"' in router
    assert 'action="announcement.sent"' in router


def test_teacher_composer_and_student_category_are_connected() -> None:
    teacher_page = (FRONTEND / "pages/NotificationsPage.tsx").read_text(encoding="utf-8")
    student_page = (FRONTEND / "pages/StudentNotificationsPage.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "features/connect/notificationsApi.ts").read_text(encoding="utf-8")
    assert "teacherAnnouncementsApi.send" in teacher_page
    assert "selectedClassrooms" in teacher_page
    assert "Turmas destinatárias" in teacher_page
    assert 'aria-live="polite"' in teacher_page
    assert "Processamentos recentes" in teacher_page
    assert "classroom_announcement" in student_page
    assert "Comunicados" in student_page
    assert "'/connect/announcements'" in api


def test_sprint_reuses_existing_database_head() -> None:
    assert list((BACKEND / "alembic/versions").glob("0059*.py")) == []
