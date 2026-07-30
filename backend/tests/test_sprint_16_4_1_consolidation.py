from app.api.actor_context import role_aliases
from app.comic_review_publish.policies import publication_readiness
from app.models.auth import OrganizationRole
from app.services.comic_runtime import domain_status


def test_owner_role_aliases_cover_incremental_admin_roles():
    roles = role_aliases(OrganizationRole.OWNER)
    assert {"OWNER", "ADMIN", "ORG_ADMIN", "PLATFORM_ADMIN", "EDITOR"}.issubset(roles)


def test_teacher_role_aliases_cover_editor_workflows():
    roles = role_aliases(OrganizationRole.TEACHER)
    assert {"TEACHER", "EDITOR", "REVIEWER"}.issubset(roles)
    assert "PLATFORM_ADMIN" not in roles


def test_member_role_aliases_cover_student_modules():
    roles = role_aliases(OrganizationRole.MEMBER)
    assert {"MEMBER", "STUDENT", "LEARNER"}.issubset(roles)


def test_runtime_status_mapping():
    assert domain_status("queued") == "QUEUED"
    assert domain_status("processing") == "RUNNING"
    assert domain_status("completed") == "COMPLETED"
    assert domain_status("failed") == "FAILED"


def test_publication_readiness_rejects_real_pending_items():
    result = publication_readiness(
        workflow_status="APPROVED",
        unresolved_threads=1,
        open_change_requests=1,
        checklist_blocked=True,
        release_hash="hash",
    )
    assert result["ready"] is False
    assert "UNRESOLVED_THREADS" in result["blocking_reasons"]
    assert "OPEN_CHANGE_REQUESTS" in result["blocking_reasons"]
    assert "CHECKLIST_BLOCKED" in result["blocking_reasons"]
