from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_educator_certificate_queries_are_tenant_scoped() -> None:
    router = (BACKEND / "app/student_portfolio/router.py").read_text(encoding="utf-8")
    assert '"/educator/students"' in router
    assert '"/educator/students/{student_user_id}/entries"' in router
    assert '"/educator/students/{student_user_id}/certificates"' in router
    assert "Membership.organization_id == actor.organization_id" in router
    assert "Membership.role == OrganizationRole.MEMBER" in router
    assert "StudentCertificate.organization_id == actor.organization_id" in router


def test_teacher_certificate_workspace_is_connected() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "components/AppLayout.tsx").read_text(encoding="utf-8")
    page = (FRONTEND / "pages/TeacherCertificatesPage.tsx").read_text(encoding="utf-8")
    credentials_api = (FRONTEND / "features/credentials/api.ts").read_text(encoding="utf-8")
    catalog = (FRONTEND / "config/productCatalog.ts").read_text(encoding="utf-8")
    assert 'path="credentials/certificados"' in app
    assert 'to: "/credentials/certificados"' in layout
    assert "educator: '/credentials/certificados'" in catalog
    assert "evidence_entry_ids: selectedEvidence" in page
    assert "credentialsApi.issue" in page
    assert "api.post<PortfolioCertificate>(`${ROOT}/certificates`" in credentials_api
    assert "/revoke`" in credentials_api


def test_sprint_does_not_add_a_database_revision() -> None:
    revisions = list((BACKEND / "alembic/versions").glob("0059*certificate*.py"))
    assert revisions == []
