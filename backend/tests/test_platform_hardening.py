from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.core.config import Settings, validate_runtime_security
from app.services.platform import sha256_file, storage_status


def test_sprint_13_revision_fits_alembic_version_column():
    assert len("0024_platform_hardening") <= 32


def test_sha256_file_is_deterministic(tmp_path: Path):
    file_path = tmp_path / "artifact.bin"
    file_path.write_bytes(b"educode-sprint-13")
    assert sha256_file(file_path) == hashlib.sha256(b"educode-sprint-13").hexdigest()


def test_storage_status_creates_and_checks_all_paths(tmp_path: Path):
    settings = Settings(
        document_storage_path=str(tmp_path / "documents"),
        creative_storage_path=str(tmp_path / "creative"),
        institutional_asset_storage_path=str(tmp_path / "institutional"),
        backup_storage_path=str(tmp_path / "backups"),
    )
    result = storage_status(settings)
    assert set(result) == {"documents", "creative", "institutional_assets", "backups", "objects"}
    assert all(item["writable"] is True for item in result.values())


def test_production_security_defaults_are_explicit():
    settings = Settings()
    assert settings.rate_limit_login_requests < settings.rate_limit_default_requests
    assert settings.health_dependency_timeout_seconds >= 1
    assert tuple(map(int, settings.app_version.split("."))) >= (0, 14, 0)


@pytest.mark.parametrize(
    "environment",
    ["test", "homologation", "staging", "production"],
)
def test_insecure_jwt_secret_is_blocked_outside_development(environment: str):
    settings = Settings(
        environment=environment,
        jwt_secret_key="troque-esta-chave-por-uma-chave-longa-e-aleatoria",
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validate_runtime_security(settings)


def test_development_keeps_explicit_local_secret_compatibility():
    settings = Settings(
        environment="development",
        jwt_secret_key="change-me-with-at-least-32-characters",
    )
    validate_runtime_security(settings)


def test_audit_hash_changes_when_event_is_modified():
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.services.platform import build_audit_hash

    event_id = uuid4()
    organization_id = uuid4()
    created_at = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)
    base = dict(
        event_id=event_id,
        organization_id=organization_id,
        user_id=None,
        module_name="assessment",
        action="grade.changed",
        entity_type="student_attempt",
        entity_id=uuid4(),
        request_id="request-123",
        ip_address="127.0.0.1",
        details={"old_score": 6.0, "new_score": 8.0},
        previous_hash="abc",
        created_at=created_at,
    )
    original = build_audit_hash(**base)
    changed = build_audit_hash(**{**base, "details": {"old_score": 6.0, "new_score": 9.0}})
    assert original != changed
    assert len(original) == 64


def test_real_restore_test_uses_temporary_database(tmp_path: Path, monkeypatch):
    import io
    import json
    import subprocess
    import tarfile
    from uuid import uuid4

    from app.models.platform import BackupRun
    from app.services.platform import execute_restore_test, sha256_file

    archive_path = tmp_path / "backup.tar.gz"
    dump_bytes = b"mock custom postgres dump"
    manifest_bytes = json.dumps({"backup_type": "database"}).encode()
    with tarfile.open(archive_path, "w:gz") as archive:
        dump_info = tarfile.TarInfo("database.dump")
        dump_info.size = len(dump_bytes)
        archive.addfile(dump_info, io.BytesIO(dump_bytes))
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest_bytes)
        archive.addfile(manifest_info, io.BytesIO(manifest_bytes))

    commands: list[list[str]] = []

    def fake_run(command, *, env=None, capture_output=True, text=True):
        commands.append(list(command))
        if command[0] == "pg_restore" and "--list" in command:
            return subprocess.CompletedProcess(command, 0, stdout="1; TABLE public users\n", stderr="")
        if command[0] == "psql" and "COUNT(*)" in command[-1]:
            return subprocess.CompletedProcess(command, 0, stdout="117\n", stderr="")
        if command[0] == "psql" and "version_num" in command[-1]:
            return subprocess.CompletedProcess(command, 0, stdout="0024_platform_hardening\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("app.services.platform.subprocess.run", fake_run)
    backup = BackupRun(
        id=uuid4(),
        organization_id=uuid4(),
        requested_by_user_id=uuid4(),
        backup_type="database",
        status="completed",
        storage_path=str(archive_path),
        checksum_sha256=sha256_file(archive_path),
    )
    settings = Settings(
        database_url="postgresql+asyncpg://educode:secret@db:5432/educode",
        backup_storage_path=str(tmp_path),
    )
    result = execute_restore_test(backup, settings)

    assert result["real_restore"] is True
    assert result["restored_public_tables"] == 117
    assert result["restored_migration"] == "0024_platform_hardening"
    assert any(command[0] == "createdb" for command in commands)
    assert any(command[0] == "pg_restore" and "--dbname" in command for command in commands)
    assert commands[-1][0] == "dropdb"


def test_rate_limit_scope_cannot_be_bypassed_with_different_resource_ids():
    from app.core.middleware import _rate_scope

    first = _rate_scope('/api/v1/assessments/11111111-1111-1111-1111-111111111111')
    second = _rate_scope('/api/v1/assessments/22222222-2222-2222-2222-222222222222')
    assert first == second == 'api:v1:assessments'


def test_platform_backup_requires_global_operator():
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.api.v1.routes_platform import require_platform_operator

    with pytest.raises(HTTPException) as error:
        require_platform_operator(SimpleNamespace(is_superuser=False))
    assert error.value.status_code == 403
    require_platform_operator(SimpleNamespace(is_superuser=True))
