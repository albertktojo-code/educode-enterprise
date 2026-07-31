from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.actor_context import ActorContext
from app.assessment_delivery.models import (
    AssessmentPublication,
    AssessmentSession,
    AssessmentSessionEvent,
    AssessmentSessionItem,
    AssessmentTarget,
)
from app.assessment_delivery.schemas import TeacherAction
from app.comic_page_editor.activity_delivery import (
    _hint_payload,
    derive_presence_status,
    monitoring_summary,
    safe_idle_threshold,
)
from app.comic_page_editor.models import (
    HQActivityBinding,
    HQActivityDeliveryLink,
    HQStudentExperienceState,
)
from app.db.session import AsyncSessionFactory
from app.models.auth import (
    Membership,
    Organization,
    OrganizationRole,
    User,
)
from app.models.education import Classroom, ClassroomEnrollment


@pytest.mark.parametrize(
    ("session_status", "experience_stage", "expected"),
    [
        (None, None, "NOT_STARTED"),
        ("IN_PROGRESS", None, "STARTED"),
        ("IN_PROGRESS", "READING", "READING"),
        ("IN_PROGRESS", "ACTIVITY", "ANSWERING"),
        ("PAUSED", "ACTIVITY", "PAUSED"),
        ("TIMED_OUT", "ACTIVITY", "PAUSED"),
        ("SUBMITTED", "ACTIVITY", "COMPLETED"),
        ("UNDER_REVIEW", "ACTIVITY", "COMPLETED"),
        ("IN_PROGRESS", "COMPLETED", "COMPLETED"),
    ],
)
def test_presence_status_is_derived_from_canonical_state(
    session_status: str | None,
    experience_stage: str | None,
    expected: str,
) -> None:
    assert derive_presence_status(session_status, experience_stage) == expected


def test_idle_threshold_is_bounded() -> None:
    assert safe_idle_threshold(None) == 180
    assert safe_idle_threshold("invalid") == 180
    assert safe_idle_threshold(1) == 30
    assert safe_idle_threshold(9999) == 3600


def test_approved_hint_payload_accepts_supported_formats() -> None:
    assert _hint_payload("Observe o primeiro passo.", 1) == {
        "level": 1,
        "message": "Observe o primeiro passo.",
    }
    assert _hint_payload(
        {"level": 2, "label": "Estratégia", "content": "Divida o problema."},
        1,
    ) == {
        "level": 2,
        "label": "Estratégia",
        "message": "Divida o problema.",
    }
    assert _hint_payload({}, 1) is None


def test_teacher_commands_require_their_sensitive_parameters() -> None:
    with pytest.raises(ValidationError):
        TeacherAction(action="EXTEND", reason="Apoio docente")
    with pytest.raises(ValidationError):
        TeacherAction(action="GRANT_ATTEMPT", reason="Apoio docente")
    with pytest.raises(ValidationError):
        TeacherAction(action="SEND_MESSAGE", reason="Apoio docente")
    with pytest.raises(ValidationError):
        TeacherAction(
            action="RELEASE_HINT",
            reason="Apoio docente",
            message="Releia a pergunta.",
        )

    action = TeacherAction(
        action="RELEASE_HINT",
        reason="Apoio docente",
        message="Releia a pergunta.",
        activity_id="bb32183c-18b2-44b7-adbf-4cc780329a53",
        hint_level=1,
    )
    assert action.action == "RELEASE_HINT"


@pytest.mark.asyncio
async def test_monitoring_snapshot_uses_org_scoped_canonical_records() -> None:
    organization_id = uuid4()
    student_id = uuid4()
    teacher_id = uuid4()
    classroom_id = uuid4()
    publication_id = uuid4()
    project_id = uuid4()
    delivery_id = uuid4()
    session_id = uuid4()
    activity_id = uuid4()
    now = datetime.now(UTC)

    async with AsyncSessionFactory() as session:
        try:
            organization = Organization(
                id=organization_id,
                name="Organização monitoramento",
                slug=f"monitoring-{organization_id.hex}",
            )
            student = User(
                id=student_id,
                email=f"{student_id.hex}@example.test",
                full_name="Estudante Monitorado",
                hashed_password="not-used-in-this-test",
            )
            session.add_all([organization, student])
            await session.flush()
            session.add(
                Membership(
                    user_id=student_id,
                    organization_id=organization_id,
                    role=OrganizationRole.MEMBER,
                )
            )
            classroom = Classroom(
                id=classroom_id,
                organization_id=organization_id,
                name="Turma Monitorada",
                is_active=True,
            )
            session.add(classroom)
            await session.flush()
            session.add(
                ClassroomEnrollment(
                    classroom_id=classroom_id,
                    user_id=student_id,
                    role="student",
                )
            )
            publication = AssessmentPublication(
                id=publication_id,
                organization_id=organization_id,
                code=f"HQ-{publication_id.hex[:8]}",
                title="HQ monitorada",
                source_type="HQ_ACTIVITY_SET",
                source_id=project_id,
                item_snapshot=[],
                status="PUBLISHED",
                starts_at=now - timedelta(hours=1),
                ends_at=now + timedelta(hours=1),
                duration_minutes=60,
                max_attempts=1,
                created_by_user_id=teacher_id,
            )
            target = AssessmentTarget(
                organization_id=organization_id,
                publication_id=publication_id,
                target_type="CLASSROOM",
                target_id=classroom_id,
                status="ACTIVE",
                assigned_by_user_id=teacher_id,
            )
            delivery = HQActivityDeliveryLink(
                id=delivery_id,
                organization_id=organization_id,
                comic_project_id=project_id,
                publication_id=publication_id,
                status="PUBLISHED",
                monitoring_settings={"idle_threshold_seconds": 60},
                created_by_user_id=teacher_id,
            )
            activity = HQActivityBinding(
                id=activity_id,
                organization_id=organization_id,
                comic_project_id=project_id,
                activity_page_id=uuid4(),
                question_version_id=uuid4(),
                activity_type="MULTIPLE_CHOICE",
                title="Atividade monitorada",
                instructions="Escolha uma opção.",
                activity_payload={},
                answer_key={},
                pedagogical_links={},
                accessibility={},
                difficulty="BASIC",
                status="APPROVED",
                display_order=1,
                max_score=1,
                teacher_review_required=True,
                created_by_user_id=teacher_id,
            )
            assessment_session = AssessmentSession(
                id=session_id,
                organization_id=organization_id,
                publication_id=publication_id,
                target_id=target.id,
                student_id=student_id,
                assessment_hub_attempt_id=uuid4(),
                session_number=1,
                status="IN_PROGRESS",
                started_at=now - timedelta(minutes=10),
                last_activity_at=now - timedelta(minutes=5),
                remaining_seconds=3000,
            )
            state = HQStudentExperienceState(
                organization_id=organization_id,
                comic_project_id=project_id,
                publication_id=publication_id,
                student_id=student_id,
                assessment_session_id=session_id,
                current_stage="ACTIVITY",
                current_page_number=3,
                current_panel_number=1,
                current_activity_index=0,
                reading_progress=100,
                activity_progress=0,
                answered_count=0,
                total_activity_count=1,
                resume_token="test-resume-token",
                preferences={},
                navigation_state={},
                last_feedback={},
                last_sequence=1,
                created_at=now - timedelta(minutes=10),
                updated_at=now - timedelta(minutes=5),
            )
            session_item = AssessmentSessionItem(
                organization_id=organization_id,
                session_id=session_id,
                question_version_id=activity.question_version_id,
                position=0,
                original_position=0,
                option_order=[],
                status="NOT_SEEN",
            )
            help_event = AssessmentSessionEvent(
                organization_id=organization_id,
                session_id=session_id,
                event_type="STUDENT_HELP_REQUESTED",
                severity="WARNING",
                source="CLIENT",
                occurred_at=now - timedelta(minutes=4),
                actor_user_id=student_id,
                metadata_payload={"activity_id": str(activity_id)},
            )
            session.add_all(
                [
                    publication,
                    target,
                    delivery,
                    activity,
                    assessment_session,
                    state,
                    session_item,
                    help_event,
                ]
            )
            await session.flush()

            actor = ActorContext(
                user_id=teacher_id,
                organization_id=organization_id,
                membership_id=uuid4(),
                roles=frozenset({"TEACHER"}),
            )
            snapshot = await monitoring_summary(
                session,
                actor=actor,
                link_id=delivery_id,
                classroom_id=classroom_id,
            )

            assert snapshot["summary"]["total_students"] == 1
            assert snapshot["students"][0]["student_name"] == (
                "Estudante Monitorado"
            )
            assert snapshot["students"][0]["presence_status"] == "ANSWERING"
            assert snapshot["students"][0]["support"]["help_pending"] is True
            assert snapshot["students"][0]["is_idle"] is True
            assert snapshot["privacy"]["answers_exposed"] is False
        finally:
            await session.rollback()
