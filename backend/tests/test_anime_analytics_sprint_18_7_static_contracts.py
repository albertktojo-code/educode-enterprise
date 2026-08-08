from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE = PROJECT_ROOT / "backend/app/services/analytics.py"
ROUTES = PROJECT_ROOT / "backend/app/api/v1/routes_analytics.py"
PLAYER = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeStudentLibraryPage.tsx"
API = PROJECT_ROOT / "frontend/src/features/animeStudio/api.ts"
DASHBOARD = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeAnalyticsPage.tsx"
FRONTEND_ROUTES = PROJECT_ROOT / "frontend/src/features/animeStudio/routes.tsx"
STUDIO = PROJECT_ROOT / "frontend/src/features/animeStudio/AnimeStudioPage.tsx"


def test_audiovisual_events_reuse_canonical_learning_events() -> None:
    service = SERVICE.read_text(encoding="utf-8")
    player = PLAYER.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")

    assert "select(LearningEvent).where(" in service
    assert "LearningEvent.organization_id == organization_id" in service
    assert "anime_project_id" in service
    assert "`/student/assignments/${assignmentId}/events`" in api
    for event_type in (
        "anime_video_started",
        "anime_video_progress",
        "anime_checkpoint_opened",
        "anime_checkpoint_completed",
        "anime_video_completed",
    ):
        assert event_type in player


def test_teacher_analytics_is_aggregate_and_organization_scoped() -> None:
    service = SERVICE.read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")

    assert 'router.get("/anime/{project_id}"' in routes
    assert "Depends(require_roles(*TEACHER_ROLES))" in routes
    assert "AnimeProject.organization_id == organization_id" in service
    assert "StudentAttempt.organization_id == organization_id" in service
    assert "viewer_count" in service
    assert "completion_rate" in service


def test_dashboard_is_routable_from_anime_studio() -> None:
    dashboard = DASHBOARD.read_text(encoding="utf-8")
    routes = FRONTEND_ROUTES.read_text(encoding="utf-8")
    studio = STUDIO.read_text(encoding="utf-8")

    assert 'path: "/analytics/anime/:projectId"' in routes
    assert "animeStudioApi.getAnalytics(projectId)" in dashboard
    assert "FUNIL DE RETENÇÃO" in dashboard
    assert "Desempenho por checkpoint" in dashboard
    assert "to={`/analytics/anime/${project.id}`}" in studio
