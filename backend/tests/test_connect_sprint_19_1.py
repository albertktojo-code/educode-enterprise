from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_certificate_events_reuse_canonical_user_notifications() -> None:
    router = (BACKEND / "app/student_portfolio/router.py").read_text(encoding="utf-8")
    assert "UserNotification(" in router
    assert 'notification_type="certificate_issued"' in router
    assert 'notification_type="certificate_revoked"' in router
    assert 'action_path="/aluno/portfolio"' in router
    assert router.index('notification_type="certificate_revoked"') < router.index(
        'action="certificate.revoked"'
    )


def test_read_all_is_scoped_and_declared_before_dynamic_route() -> None:
    router = (BACKEND / "app/api/v1/routes_delivery.py").read_text(encoding="utf-8")
    bulk = '@router.patch("/student/notifications/read-all")'
    dynamic = '@router.patch("/student/notifications/{notification_id}/read"'
    assert router.index(bulk) < router.index(dynamic)
    assert "UserNotification.organization_id == org_id(membership)" in router
    assert "UserNotification.user_id == user.id" in router
    assert "UserNotification.status == NotificationStatus.UNREAD" in router
    assert 'return {"updated": len(notifications)}' in router


def test_student_notification_center_is_connected_to_connect() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "components/AppLayout.tsx").read_text(encoding="utf-8")
    catalog = (FRONTEND / "config/productCatalog.ts").read_text(encoding="utf-8")
    page = (FRONTEND / "pages/StudentNotificationsPage.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "features/connect/notificationsApi.ts").read_text(encoding="utf-8")
    assert 'path="aluno/notificacoes"' in app
    assert 'to: "/aluno/notificacoes"' in layout
    assert "student: '/aluno/notificacoes'" in catalog
    assert "studentNotificationsApi.markAllRead" in page
    assert "aria-live=\"polite\"" in page
    assert "'/student/notifications/read-all'" in api


def test_sprint_reuses_existing_database_head() -> None:
    assert list((BACKEND / "alembic/versions").glob("0059*.py")) == []
