from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_tables():
    text = (
        BACKEND / "alembic/versions/0043_intervention_orchestration.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0043_intervention_orchestration"' in text
    assert 'down_revision: str | None = "0042_auth_session_security"' in text
    assert len("0043_intervention_orchestration") <= 32
    assert '"learning_intervention_events"' in text
    assert '"learning_alerts"' in text
    assert '"adaptive_recommendations"' in text


def test_canonical_models_are_extended_instead_of_duplicated():
    analytics = (BACKEND / "app/models/analytics.py").read_text(encoding="utf-8")
    adaptive = (BACKEND / "app/models/adaptive.py").read_text(encoding="utf-8")
    insights = (
        BACKEND / "app/adaptive_insights/models.py"
    ).read_text(encoding="utf-8")
    assert "source_recommendation_id" in analytics
    assert "class LearningInterventionEvent" in analytics
    assert "source_alert_id" in adaptive
    assert "learning_intervention_id" in insights
    assert 'class ComicLearningIntervention' not in analytics
    assert '__tablename__ = "comic_interventions"' not in analytics


def test_human_approval_and_existing_ai_orchestrator_are_mandatory():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    assert "create_generation_request" in services
    assert "human_approval_required" in services
    assert "pending_review" in services
    assert "approve_proposal" in router
    assert "automatic_application" in services
    assert not (BACKEND / "app/intervention_orchestration/models.py").exists()


def test_existing_alerts_paths_outcomes_jobs_and_audit_are_reused():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    assert "LearningAlert" in services
    assert "approve_recommendation_as_path" in services
    assert "InterventionOutcomeRecord" in services
    assert "append_domain_audit" in router
    assert "BackgroundJob" not in services
    assert "learning_intervention_jobs" not in services


def test_router_and_registry_are_integrated():
    api_router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    assert api_router.count("intervention_orchestration_router") == 2
    assert "intervention_orchestration_version" in registry
