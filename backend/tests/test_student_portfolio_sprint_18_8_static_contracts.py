from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAGE = PROJECT_ROOT / "frontend/src/pages/StudentPortfolioPage.tsx"
APP = PROJECT_ROOT / "frontend/src/App.tsx"
LAYOUT = PROJECT_ROOT / "frontend/src/components/AppLayout.tsx"
PORTAL = PROJECT_ROOT / "frontend/src/pages/StudentPortalPage.tsx"
PRODUCTS = PROJECT_ROOT / "frontend/src/config/productCatalog.ts"


def test_portfolio_reuses_canonical_student_evidence_sources() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "api<StudentAssignmentCard[]>('/student/assignments')" in page
    assert "api<StudentOwnProgress>('/analytics/student/progress')" in page
    assert "comicReaderApi.releases()" in page
    assert "animeStudioApi.listPublications()" in page
    assert "progress_status === 'completed'" in page
    assert "best_percentage" in page


def test_portfolio_has_independent_failure_and_empty_states() -> None:
    page = PAGE.read_text(encoding="utf-8")

    assert "Promise.allSettled(requests)" in page
    assert "Algumas evidências não puderam ser carregadas" in page
    assert page.count("<EmptyState") >= 3
    assert 'aria-busy={loading}' in page
    assert "<progress max={100}" in page


def test_credentials_routes_students_to_portfolio() -> None:
    app = APP.read_text(encoding="utf-8")
    layout = LAYOUT.read_text(encoding="utf-8")
    portal = PORTAL.read_text(encoding="utf-8")
    products = PRODUCTS.read_text(encoding="utf-8")

    assert 'path="aluno/portfolio"' in app
    assert 'to: "/aluno/portfolio"' in layout
    assert 'to="/aluno/portfolio"' in portal
    assert "student: '/aluno/portfolio'" in products
