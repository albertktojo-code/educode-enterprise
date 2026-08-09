from pathlib import Path

from app.student_portfolio.schemas import PublicCertificateRead

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_public_certificate_schema_minimizes_student_data() -> None:
    fields = set(PublicCertificateRead.model_fields)
    assert {"student_name", "issuer_name", "organization_name", "evidence"} <= fields
    assert "email" not in fields
    assert "student_user_id" not in fields
    assert "organization_id" not in fields


def test_public_verification_and_qr_have_clear_contracts() -> None:
    router = (BACKEND / "app/student_portfolio/router.py").read_text(encoding="utf-8")
    pyproject = (BACKEND / "pyproject.toml").read_text(encoding="utf-8")
    assert '"/certificates/verify/{verification_code}"' in router
    assert '"/certificates/verify/{verification_code}/qr"' in router
    assert "verification_code.strip().upper()" in router
    assert 'media_type="image/svg+xml"' in router
    assert 'parsed_origin.scheme not in {"http", "https"}' in router
    assert '"qrcode>=8.2,<9.0"' in pyproject


def test_public_page_is_outside_protected_layout_and_supports_print() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    page = (FRONTEND / "pages/PublicCertificatePage.tsx").read_text(encoding="utf-8")
    credentials_api = (FRONTEND / "features/credentials/api.ts").read_text(encoding="utf-8")
    css = (FRONTEND / "pages/publicCertificate.css").read_text(encoding="utf-8")
    public_route = app.index('path="/credentials/verificar/:verificationCode"')
    protected_route = app.index("<Route element={<ProtectedRoute />}")
    assert public_route < protected_route
    assert "auth: false" in credentials_api
    assert "window.print()" in page
    assert "student_user_id" not in page and "email" not in page
    assert "@media print" in css


def test_sprint_does_not_add_a_database_revision() -> None:
    assert list((BACKEND / "alembic/versions").glob("0059*.py")) == []
