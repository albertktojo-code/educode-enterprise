from fastapi import APIRouter

from app.adaptive_evolution.router import router as adaptive_evolution_router
from app.adaptive_insights.router import router as adaptive_insights_router
from app.anime_studio.media_router import router as anime_media_router
from app.anime_studio.router import router as anime_studio_router
from app.api.v1 import (
    routes_adaptive,
    routes_ai_advanced,
    routes_ai_runtime,
    routes_analytics,
    routes_assessments,
    routes_assets,
    routes_auth,
    routes_comics,
    routes_consolidation,
    routes_creative,
    routes_delivery,
    routes_documents,
    routes_education,
    routes_health,
    routes_infrastructure,
    routes_mock_ai,
    routes_observability,
    routes_operations,
    routes_organizations,
    routes_pedagogy,
    routes_platform,
    routes_preview,
    routes_rag,
    routes_release,
    routes_retrieval,
    routes_sequences,
    routes_statistics,
    routes_statistics_advanced,
    routes_teacher_studio,
    routes_users,
)
from app.assessment_analytics.router import router as assessment_analytics_router
from app.assessment_delivery.router import router as assessment_delivery_router
from app.assessment_hub.router import router as assessment_hub_router
from app.assessment_review.router import router as assessment_review_router
from app.comic_layout_studio.router import router as comic_layout_studio_router
from app.comic_page_editor.router import router as comic_page_editor_router
from app.comic_reader_access.router import router as comic_reader_access_router
from app.comic_reader_analytics.router import router as comic_reader_analytics_router
from app.comic_review_publish.router import router as comic_review_publish_router
from app.comic_visual_library.router import router as comic_visual_library_router
from app.institutional_governance.router import router as institutional_governance_router
from app.instrument_governance.router import router as instrument_governance_router
from app.intervention_effectiveness.router import router as intervention_effectiveness_router
from app.intervention_orchestration.router import router as intervention_orchestration_router
from app.student_portfolio.router import router as student_portfolio_router
from app.ui_preferences.router import router as ui_preferences_router

api_router = APIRouter()
api_router.include_router(adaptive_evolution_router)

for route in (
    routes_health,
    routes_consolidation,
    routes_ai_runtime,
    routes_ai_advanced,
    routes_operations,
    routes_observability,
    routes_platform,
    routes_release,
    routes_infrastructure,
    routes_analytics,
    routes_adaptive,
    routes_assessments,
    routes_assets,
    routes_auth,
    routes_organizations,
    routes_users,
    routes_documents,
    routes_delivery,
    routes_education,
    routes_pedagogy,
    routes_comics,
    routes_preview,
    routes_creative,
    routes_sequences,
    routes_teacher_studio,
    routes_retrieval,
    routes_statistics,
    routes_statistics_advanced,
    routes_rag,
    routes_mock_ai,
):
    api_router.include_router(route.router)

api_router.include_router(adaptive_insights_router)

api_router.include_router(assessment_hub_router)

api_router.include_router(assessment_delivery_router)

api_router.include_router(instrument_governance_router)

api_router.include_router(assessment_review_router)

api_router.include_router(assessment_analytics_router)

api_router.include_router(comic_page_editor_router)

api_router.include_router(comic_layout_studio_router)

api_router.include_router(comic_visual_library_router)

api_router.include_router(comic_review_publish_router)

api_router.include_router(comic_reader_access_router)
api_router.include_router(comic_reader_analytics_router)
api_router.include_router(intervention_orchestration_router)
api_router.include_router(intervention_effectiveness_router)
api_router.include_router(institutional_governance_router)
api_router.include_router(ui_preferences_router)
api_router.include_router(student_portfolio_router)
api_router.include_router(anime_studio_router)
api_router.include_router(anime_media_router)
