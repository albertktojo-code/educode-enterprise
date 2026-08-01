from pathlib import Path


# Dentro do container backend o projeto Python e montado em /app.
# O frontend nao e montado nesse container e e validado pelo instalador
# no host e pelo build do servico frontend.
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_imports_model_registry():
    text = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "model_registry" in text


def test_incremental_compat_modules_use_central_actor_context():
    modules = {
        "adaptive_evolution",
        "adaptive_insights",
        "assessment_hub",
        "assessment_delivery",
        "instrument_governance",
        "assessment_review",
        "assessment_analytics",
        "comic_page_editor",
        "comic_layout_studio",
        "comic_visual_library",
        "comic_review_publish",
    }
    for module in modules:
        text = (BACKEND_ROOT / "app" / module / "compat.py").read_text(encoding="utf-8")
        assert "app.api.actor_context" in text, module


def test_consolidation_router_is_registered_in_backend():
    text = (BACKEND_ROOT / "app" / "api" / "v1" / "router.py").read_text(encoding="utf-8")
    assert "routes_consolidation" in text
    assert "routes_consolidation," in text
    assert "api_router.include_router(route.router)" in text
