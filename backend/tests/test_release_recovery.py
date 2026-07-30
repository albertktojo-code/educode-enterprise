from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.core.config import Settings
from app.services.release import (
    active_maintenance,
    configuration_release_warnings,
    scan_migration_sql,
    selective_restore_plan,
    validate_revision_id,
)


def test_sprint_13_2_revision_fits_alembic_column():
    assert len("0026_release_recovery") <= 32
    assert validate_revision_id("0026_release_recovery") == []


def test_revision_validation_rejects_long_or_unsafe_values():
    assert validate_revision_id("x" * 33)
    assert validate_revision_id("0026 invalid")


def test_migration_scan_blocks_destructive_operations():
    safe = scan_migration_sql("CREATE TABLE example (id uuid);")
    unsafe = scan_migration_sql("ALTER TABLE example DROP COLUMN old_value;")
    assert safe["safe"] is True
    assert unsafe["safe"] is False
    assert "drop_column" in unsafe["destructive_operations"]


def test_selective_restore_plan_preserves_versions():
    plan = selective_restore_plan("comic", str(uuid4()), "new_version")
    assert plan["destructive"] is False
    assert "pages" in plan["dependencies"]
    assert plan["recommended_mode"] == "new_version"


def test_active_maintenance_respects_time_range():
    now = datetime(2026, 7, 24, 12, tzinfo=UTC)
    window = SimpleNamespace(
        status="active",
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(minutes=10),
    )
    assert active_maintenance(window, now) is True
    window.status = "cancelled"
    assert active_maintenance(window, now) is False


def test_production_release_warnings_require_https_and_secret():
    settings = Settings(
        environment="production",
        debug=False,
        public_base_url="http://localhost:5173",
        backend_cors_origins=["http://localhost:5173"],
        jwt_secret_key="change-me-with-at-least-32-characters",
        deployment_strategy="blue_green",
        reverse_proxy_enabled=False,
    )
    warnings = configuration_release_warnings(settings)
    assert any("JWT_SECRET_KEY" in item for item in warnings)
    assert any("HTTPS" in item for item in warnings)
    assert any("Blue-green" in item for item in warnings)


def test_release_defaults_are_explicit():
    settings = Settings()
    assert tuple(map(int, settings.app_version.split("."))) >= (0, 14, 0)
    assert settings.require_release_backup is True
    assert settings.require_release_approval is True
    assert settings.default_rpo_minutes >= settings.default_rto_minutes
