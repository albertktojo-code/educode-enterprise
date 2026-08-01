from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_later_migration_chain_extends_0043_once():
    versions = BACKEND / "alembic/versions"
    assert (versions / "0043_intervention_orchestration.py").is_file()
    migrations = [
        path for path in versions.iterdir() if path.name.startswith("0044_")
    ]
    assert [path.name for path in migrations] == [
        "0044_intervention_effectiveness.py"
    ]
    assert (
        'down_revision: str | None = "0043_intervention_orchestration"'
        in migrations[0].read_text(encoding="utf-8")
    )


def test_concurrent_operations_use_row_locks():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    assert services.count(".with_for_update()") >= 2
    assert "lock=True" in router
    assert "PROPOSAL_ALREADY_CONVERTED" in services
    assert "INTERVENTION_ALREADY_ACTIVE" in services


def test_organization_and_resource_references_are_validated():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    for model in (
        "Membership",
        "Classroom",
        "ClassroomEnrollment",
        "ComicEditorialRelease",
        "MaterialAssignment",
        "AccessibleResourceVersion",
    ):
        assert model in services
    assert "validate_recommendation_references" in services


def test_student_payload_does_not_expose_internal_evidence():
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    assert "student_intervention_payload" in router
    assert '"baseline_snapshot"' not in router.split(
        "def student_intervention_payload", 1
    )[1].split("@router.get", 1)[0]
    policies = (
        BACKEND / "app/intervention_orchestration/policies.py"
    ).read_text(encoding="utf-8")
    assert "safe_student_actions" in policies
    assert "ClassroomEnrollment" in router


def test_alert_is_reopened_when_result_is_not_improved():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    assert 'recommendation.status = "completed" if resolved else "needs_revision"' in services
    assert "alert.status = AlertStatus.OPEN" in services
    assert 'recommendation.status = "canceled"' in router


def test_ai_request_is_not_claimed_as_ai_authorship():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    assert "created_by_ai=False" in services
    assert '"ai_requested"' in router


def test_new_json_fields_match_jsonb_migration():
    analytics = (BACKEND / "app/models/analytics.py").read_text(encoding="utf-8")
    assert "from sqlalchemy.dialects.postgresql import JSONB" in analytics
    assert "plan_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB" in analytics
    assert "event_data: Mapped[dict[str, Any]] = mapped_column(JSONB" in analytics


def test_evidence_window_and_privacy_suppression_are_enforced():
    services = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    config = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")
    assert "intervention_evidence_window_days" in config
    assert "ComicReaderEvent.occurred_at >= window_start" in services
    assert "privacy_suppressed.is_(False)" in services
