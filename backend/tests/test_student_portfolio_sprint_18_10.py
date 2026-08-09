from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend")


def test_productions_reuse_canonical_authorship_and_tenant_fields() -> None:
    router = (BACKEND / "app/student_portfolio/router.py").read_text(encoding="utf-8")
    assert "Project.owner_id == actor.user_id" in router
    assert "GeneratedComic.created_by_user_id == actor.user_id" in router
    assert "AnimeProject.created_by_user_id == actor.user_id" in router
    assert router.count("organization_id == actor.organization_id") >= 3


def test_portfolio_exposes_authored_productions_without_migration() -> None:
    page = (FRONTEND / "src/pages/StudentPortfolioPage.tsx").read_text(encoding="utf-8")
    assert "'/student/portfolio/productions'" in page
    assert "MINHAS PRODUÇÕES" in page
    assert "Nenhuma produção autoral ainda" in page
    assert "production.route" in page
