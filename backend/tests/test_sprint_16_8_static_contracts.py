from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_tables():
    text = (
        BACKEND / "alembic/versions/0044_intervention_effectiveness.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0044_intervention_effectiveness"' in text
    assert (
        'down_revision: str | None = "0043_intervention_orchestration"'
        in text
    )
    assert len("0044_intervention_effectiveness") <= 32
    assert '"intervention_evaluation_checkpoints"' in text
    assert '"intervention_effectiveness_metrics"' in text


def test_longitudinal_domain_does_not_duplicate_interventions():
    models = (
        BACKEND / "app/intervention_effectiveness/models.py"
    ).read_text(encoding="utf-8")
    assert "class InterventionEvaluationCheckpoint" in models
    assert "class InterventionEffectivenessMetric" in models
    assert '__tablename__ = "learning_interventions"' not in models
    assert '__tablename__ = "learning_alerts"' not in models
    assert '__tablename__ = "background_jobs"' not in models


def test_completion_schedules_followups():
    orchestration = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    effectiveness = (
        BACKEND / "app/intervention_effectiveness/services.py"
    ).read_text(encoding="utf-8")
    assert "register_intervention_completion" in orchestration
    assert "schedule_checkpoints" in effectiveness
    for window in ("immediate", "d7", "d15", "d30", "d60"):
        assert window in (
            BACKEND / "app/intervention_effectiveness/policies.py"
        ).read_text(encoding="utf-8")


def test_existing_jobs_audit_and_evidence_are_reused():
    services = (
        BACKEND / "app/intervention_effectiveness/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/intervention_effectiveness/router.py"
    ).read_text(encoding="utf-8")
    assert "BackgroundJob" in services
    assert "StudentAttempt" in services
    assert "ComicReadingCheckpoint" in services
    assert "ComicReaderSessionMetric" in services
    assert "LearningAlert" in services
    assert "append_domain_audit" in router
    assert "effectiveness_jobs" not in services


def test_privacy_retention_and_recurrence_are_explicit():
    services = (
        BACKEND / "app/intervention_effectiveness/services.py"
    ).read_text(encoding="utf-8")
    policies = (
        BACKEND / "app/intervention_effectiveness/policies.py"
    ).read_text(encoding="utf-8")
    assert "privacy_suppressed" in services
    assert "intervention_effectiveness_min_group_size" in services
    assert "alert_recurred" in services
    assert "retention_tolerance" in policies
    assert "insufficient_evidence" in policies


def test_router_and_model_registry_are_integrated():
    api_router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    assert api_router.count("intervention_effectiveness_router") == 2
    assert "intervention_effectiveness_models" in registry


def test_export_does_not_bypass_privacy():
    router = (
        BACKEND / "app/intervention_effectiveness/router.py"
    ).read_text(encoding="utf-8")
    services = (
        BACKEND / "app/intervention_effectiveness/services.py"
    ).read_text(encoding="utf-8")
    assert "privacy_suppressed" in router
    assert "None if suppressed" in router
    assert "metrics_csv" in services
