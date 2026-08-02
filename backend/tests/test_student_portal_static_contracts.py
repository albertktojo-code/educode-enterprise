from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = PROJECT_ROOT / "frontend/src"


def test_student_portal_reuses_canonical_student_domains() -> None:
    portal = (FRONTEND / "pages/StudentPortalPage.tsx").read_text(encoding="utf-8")

    assert "'/student/assignments'" in portal
    assert "'/student/notifications'" in portal
    assert "'/analytics/student/progress'" in portal
    assert "comicReaderApi.releases()" in portal
    assert "animeStudioApi.listPublications()" in portal
    assert "Promise.allSettled" in portal


def test_student_portal_is_registered_in_route_and_navigation() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "components/AppLayout.tsx").read_text(encoding="utf-8")

    assert 'path="aluno" element={<StudentPortalPage />}' in app
    assert 'to: "/aluno"' in layout
    assert 'label: "Início"' in layout


def test_student_portal_exposes_loading_errors_and_accessible_landmarks() -> None:
    portal = (FRONTEND / "pages/StudentPortalPage.tsx").read_text(encoding="utf-8")

    assert 'role="status"' in portal
    assert 'role="alert"' in portal
    assert 'aria-label="Resumo da aprendizagem"' in portal
    assert 'aria-label="Atalhos da área do estudante"' in portal
