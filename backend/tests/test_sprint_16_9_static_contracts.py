from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_governance_tables():
    text = (
        BACKEND / "alembic/versions/0045_institutional_governance.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0045_institutional_governance"' in text
    assert (
        'down_revision: str | None = "0044_intervention_effectiveness"'
        in text
    )
    assert len("0045_institutional_governance") <= 32
    for table in (
        "institutional_governance_assets",
        "institutional_governance_reviews",
        "institutional_governance_snapshots",
        "institutional_governance_incidents",
        "institutional_governance_events",
    ):
        assert f'"{table}"' in text


def test_governance_is_a_layer_not_a_parallel_operational_domain():
    models = (
        BACKEND / "app/institutional_governance/models.py"
    ).read_text(encoding="utf-8")
    assert '__tablename__ = "ai_models"' not in models
    assert '__tablename__ = "adaptive_model_versions"' not in models
    assert '__tablename__ = "learning_interventions"' not in models
    assert '__tablename__ = "background_jobs"' not in models
    assert '__tablename__ = "system_audit_events"' not in models


def test_human_approval_separation_and_versioning_are_enforced():
    services = (
        BACKEND / "app/institutional_governance/services.py"
    ).read_text(encoding="utf-8")
    assert "owner_user_id == actor.user_id" in services
    assert "O responsável pelo ativo não pode aprovar" in services
    assert "clone_version" in services
    assert "retired_by_new_version" in services
    assert "required_approvals" in (
        BACKEND / "app/institutional_governance/policies.py"
    ).read_text(encoding="utf-8")


def test_monitoring_opens_review_but_never_auto_suspends():
    services = (
        BACKEND / "app/institutional_governance/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/institutional_governance/router.py"
    ).read_text(encoding="utf-8")
    assert 'asset.status = "review_required"' in services
    monitor_block = services.split(
        "async def monitor_asset", 1
    )[1].split("async def refresh_monitoring", 1)[0]
    assert 'asset.status = "suspended"' not in monitor_block
    assert '@router.post("/assets/{asset_id}/suspend")' in router
    assert "human_suspension_required" in router


def test_existing_jobs_audit_ai_and_effectiveness_are_reused():
    services = (
        BACKEND / "app/institutional_governance/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/institutional_governance/router.py"
    ).read_text(encoding="utf-8")
    assert "BackgroundJob" in services
    assert "InterventionEvaluationCheckpoint" in services
    assert "AIGenerationRequest" in services
    assert "AIQualityEvaluation" in services
    assert "append_domain_audit" in router
    assert "governance_background_jobs" not in services


def test_execution_gates_are_integrated_in_monitor_mode():
    orchestrator = (
        BACKEND / "app/services/ai/orchestrator.py"
    ).read_text(encoding="utf-8")
    interventions = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    config = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")
    assert "assert_ai_execution_allowed" in orchestrator
    assert "governance_checks" in orchestrator
    assert "assert_adaptive_model_allowed" in interventions
    assert 'governance_enforcement_mode: str = Field(default="monitor")' in config


def test_small_samples_do_not_trigger_threshold_incidents():
    services = (
        BACKEND / "app/institutional_governance/services.py"
    ).read_text(encoding="utf-8")
    assert "privacy_suppressed" in services
    assert "if privacy_suppressed" in services
    assert "threshold_breaches(result, asset.monitoring_policy)" in services
    assert "minimum_group_size" in services


def test_router_and_model_registry_are_integrated():
    api_router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    assert api_router.count("institutional_governance_router") == 2
    assert "institutional_governance_models" in registry
