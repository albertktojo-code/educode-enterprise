from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_credentials_uses_one_frontend_contract() -> None:
    types = (FRONTEND / "features/credentials/types.ts").read_text(encoding="utf-8")
    api = (FRONTEND / "features/credentials/api.ts").read_text(encoding="utf-8")
    teacher = (FRONTEND / "pages/TeacherCertificatesPage.tsx").read_text(encoding="utf-8")
    student = (FRONTEND / "pages/StudentPortfolioPage.tsx").read_text(encoding="utf-8")
    public = (FRONTEND / "pages/PublicCertificatePage.tsx").read_text(encoding="utf-8")
    assert "export interface PortfolioCertificate" in types
    assert "export interface PublicCertificate" in types
    assert "export const credentialsApi" in api
    assert "credentialsApi.issue" in teacher and "credentialsApi.revoke" in teacher
    assert "credentialsApi.ownCertificates" in student
    assert "credentialsApi.verify" in public and "credentialsApi.qrUrl" in public
    assert "interface Certificate" not in teacher
    assert "interface PublicCertificate" not in public


def test_certificate_verification_is_discoverable_before_login() -> None:
    login = (FRONTEND / "pages/LoginPage.tsx").read_text(encoding="utf-8")
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    assert 'to="/credentials/verificar"' in login
    assert 'path="/credentials/verificar"' in app
    assert app.index('path="/credentials/verificar"') < app.index(
        "<Route element={<ProtectedRoute />}"
    )


def test_consolidation_keeps_database_head_unchanged() -> None:
    assert list((BACKEND / "alembic/versions").glob("0059*.py")) == []
