from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.delivery import AttemptStatus, StudentAnswer, StudentAttempt
from app.models.operations import BackgroundJob, WorkerHeartbeat
from app.models.platform import BackupRun, SystemAuditEvent


def utcnow() -> datetime:
    return datetime.now(UTC)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def current_migration(session: AsyncSession) -> str:
    try:
        value = await session.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    except Exception:
        return "unknown"
    return str(value or "unknown")


async def redis_status(settings: Settings | None = None) -> tuple[str, int, dict[str, Any]]:
    settings = settings or get_settings()
    started = time.perf_counter()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        pong = await asyncio.wait_for(client.ping(), timeout=settings.health_dependency_timeout_seconds)
        latency = int((time.perf_counter() - started) * 1000)
        return ("healthy" if pong else "degraded", latency, {"response": bool(pong)})
    except Exception as exc:
        return "unavailable", int((time.perf_counter() - started) * 1000), {"error": type(exc).__name__}
    finally:
        await client.aclose()


async def database_status(session: AsyncSession) -> tuple[str, int, dict[str, Any]]:
    started = time.perf_counter()
    try:
        await session.execute(text("SELECT 1"))
        latency = int((time.perf_counter() - started) * 1000)
        return "healthy", latency, {"migration": await current_migration(session)}
    except Exception as exc:
        return "unavailable", int((time.perf_counter() - started) * 1000), {"error": type(exc).__name__}


def configuration_warnings(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    warnings: list[str] = []
    if settings.jwt_secret_key.startswith("change-me") or len(settings.jwt_secret_key) < 32:
        warnings.append("JWT_SECRET_KEY insegura ou curta.")
    if len(settings.initial_admin_password) < 12 or settings.initial_admin_password == "Admin@123456":
        warnings.append("A senha inicial do administrador deve ser alterada antes da homologação.")
    database_password = make_url(settings.database_url).password or ""
    if database_password in {"educode_dev_password", "password", "postgres"}:
        warnings.append("A senha do PostgreSQL ainda utiliza um valor de desenvolvimento.")
    if settings.environment in {"homologation", "staging", "production"} and settings.debug:
        warnings.append("DEBUG deve permanecer desativado fora do desenvolvimento.")
    if settings.environment == "production" and any("localhost" in origin for origin in settings.backend_cors_origins):
        warnings.append("BACKEND_CORS_ORIGINS contém localhost em produção.")
    return warnings


def storage_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    paths = {
        "documents": settings.document_storage_path,
        "creative": settings.creative_storage_path,
        "institutional_assets": settings.institutional_asset_storage_path,
        "backups": settings.backup_storage_path,
        "objects": settings.object_storage_local_path,
    }
    result: dict[str, Any] = {}
    for name, raw_path in paths.items():
        path = Path(raw_path)
        try:
            path.mkdir(parents=True, exist_ok=True)
            usage = shutil.disk_usage(path)
            result[name] = {
                "path": str(path),
                "writable": os.access(path, os.W_OK),
                "free_bytes": usage.free,
                "total_bytes": usage.total,
            }
        except OSError as exc:
            result[name] = {"path": str(path), "writable": False, "error": str(exc)}
    return result


async def worker_status(session: AsyncSession, stale_seconds: int = 45) -> dict[str, Any]:
    now = utcnow()
    workers = list((await session.scalars(select(WorkerHeartbeat))).all())
    active = [w for w in workers if w.last_seen_at >= now - timedelta(seconds=stale_seconds)]
    return {
        "total": len(workers),
        "active": len(active),
        "queues": sorted({w.queue_name for w in active}),
        "stale_workers": [w.worker_name for w in workers if w not in active],
    }


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def build_audit_hash(
    *,
    event_id: UUID,
    organization_id: UUID,
    user_id: UUID | None,
    module_name: str,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    request_id: str,
    ip_address: str,
    details: dict[str, Any],
    previous_hash: str,
    created_at: datetime,
) -> str:
    payload = {
        "id": str(event_id),
        "organization_id": str(organization_id),
        "user_id": str(user_id) if user_id else None,
        "module_name": module_name,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "request_id": request_id,
        "ip_address": ip_address,
        "details": details,
        "previous_hash": previous_hash,
        "created_at": created_at.isoformat(),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def build_security_event_hash(
    *,
    event_id: UUID,
    organization_id: UUID | None,
    user_id: UUID | None,
    event_type: str,
    severity: str,
    request_id: str,
    ip_address: str,
    user_agent: str,
    details: dict[str, Any],
    previous_hash: str,
    created_at: datetime,
) -> str:
    payload = {
        "id": str(event_id),
        "organization_id": str(organization_id) if organization_id else None,
        "user_id": str(user_id) if user_id else None,
        "event_type": event_type,
        "severity": severity,
        "request_id": request_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": details,
        "previous_hash": previous_hash,
        "created_at": created_at.isoformat(),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


async def _acquire_audit_lock(session: AsyncSession, key: str) -> None:
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:audit_key))"),
        {"audit_key": key},
    )


async def append_audit_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID | None,
    module_name: str,
    action: str,
    entity_type: str = "",
    entity_id: UUID | None = None,
    request_id: str = "",
    ip_address: str = "",
    details: dict[str, Any] | None = None,
) -> SystemAuditEvent:
    await _acquire_audit_lock(session, f"audit:{organization_id}")
    previous = await session.scalar(
        select(SystemAuditEvent)
        .where(SystemAuditEvent.organization_id == organization_id)
        .order_by(SystemAuditEvent.created_at.desc(), SystemAuditEvent.id.desc())
        .limit(1)
    )
    previous_hash = previous.event_hash if previous else ""
    event_id = uuid4()
    created_at = utcnow()
    event_details = details or {}
    event_hash = build_audit_hash(
        event_id=event_id,
        organization_id=organization_id,
        user_id=user_id,
        module_name=module_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        ip_address=ip_address,
        details=event_details,
        previous_hash=previous_hash,
        created_at=created_at,
    )
    event = SystemAuditEvent(
        id=event_id,
        organization_id=organization_id,
        user_id=user_id,
        module_name=module_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        ip_address=ip_address,
        details=event_details,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )
    session.add(event)
    return event


async def append_security_event(
    session: AsyncSession,
    *,
    organization_id: UUID | None,
    user_id: UUID | None,
    event_type: str,
    severity: str = "info",
    request_id: str = "",
    ip_address: str = "",
    user_agent: str = "",
    details: dict[str, Any] | None = None,
):
    from app.models.platform import SecurityEvent

    await _acquire_audit_lock(
        session,
        f"security:{organization_id}" if organization_id else "security:global",
    )
    condition = (
        SecurityEvent.organization_id.is_(None)
        if organization_id is None
        else SecurityEvent.organization_id == organization_id
    )
    previous = await session.scalar(
        select(SecurityEvent)
        .where(condition)
        .order_by(SecurityEvent.created_at.desc(), SecurityEvent.id.desc())
        .limit(1)
    )
    previous_hash = previous.event_hash if previous else ""
    event_id = uuid4()
    created_at = utcnow()
    event_details = details or {}
    safe_user_agent = user_agent[:500]
    event_hash = build_security_event_hash(
        event_id=event_id,
        organization_id=organization_id,
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=safe_user_agent,
        details=event_details,
        previous_hash=previous_hash,
        created_at=created_at,
    )
    event = SecurityEvent(
        id=event_id,
        organization_id=organization_id,
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=safe_user_agent,
        details=event_details,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )
    session.add(event)
    return event


async def verify_audit_chain(session: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    events = list(
        (
            await session.scalars(
                select(SystemAuditEvent)
                .where(SystemAuditEvent.organization_id == organization_id)
                .order_by(SystemAuditEvent.created_at, SystemAuditEvent.id)
            )
        ).all()
    )
    expected_previous = ""
    broken: list[str] = []
    for event in events:
        expected_hash = build_audit_hash(
            event_id=event.id,
            organization_id=event.organization_id,
            user_id=event.user_id,
            module_name=event.module_name,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            request_id=event.request_id,
            ip_address=event.ip_address,
            details=event.details,
            previous_hash=event.previous_hash,
            created_at=event.created_at,
        )
        if event.previous_hash != expected_previous or event.event_hash != expected_hash:
            broken.append(str(event.id))
        expected_previous = event.event_hash
    return {"valid": not broken, "events": len(events), "broken_event_ids": broken[:20]}


def _database_connection(settings: Settings) -> tuple[list[str], str, dict[str, str]]:
    url = make_url(settings.database_url)
    args = [
        "--host", str(url.host or "db"),
        "--port", str(url.port or 5432),
        "--username", str(url.username or "educode"),
    ]
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = str(url.password)
    return args, str(url.database or "educode"), env


def _database_pg_args(settings: Settings) -> tuple[list[str], dict[str, str]]:
    args, database, env = _database_connection(settings)
    return [*args, "--dbname", database], env


def _run_command(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(command, env=env, capture_output=True, text=True)
    if process.returncode != 0:
        detail = (process.stderr or process.stdout or "Falha sem detalhes").strip()
        raise RuntimeError(f"{command[0]} falhou: {detail[:2000]}")
    return process


def execute_backup(backup: BackupRun, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    root = Path(settings.backup_storage_path) / str(backup.organization_id)
    root.mkdir(parents=True, exist_ok=True)
    stamp = utcnow().strftime("%Y%m%dT%H%M%SZ")
    archive_path = root / f"educode-{backup.backup_type}-{stamp}-{backup.id}.tar.gz"
    pg_args, env = _database_pg_args(settings)
    manifest: dict[str, Any] = {
        "created_at": utcnow().isoformat(),
        "backup_type": backup.backup_type,
        "files": [],
    }

    with tempfile.TemporaryDirectory(prefix="educode-backup-") as temp_dir:
        temp = Path(temp_dir)
        database_dump = temp / "database.dump"
        command = ["pg_dump", *pg_args, "--format=custom", "--file", str(database_dump)]
        _run_command(command, env)
        manifest["files"].append(
            {
                "name": "database.dump",
                "size_bytes": database_dump.stat().st_size,
                "checksum_sha256": sha256_file(database_dump),
            }
        )
        (temp / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(database_dump, arcname="database.dump")
            archive.add(temp / "manifest.json", arcname="manifest.json")
            if backup.backup_type == "full":
                for label, raw_path in (
                    ("documents", settings.document_storage_path),
                    ("creative", settings.creative_storage_path),
                    ("institutional-assets", settings.institutional_asset_storage_path),
                    ("objects", settings.object_storage_local_path),
                ):
                    source = Path(raw_path)
                    if source.exists():
                        archive.add(source, arcname=f"storage/{label}", recursive=True)
    return {
        "storage_path": str(archive_path),
        "checksum_sha256": sha256_file(archive_path),
        "size_bytes": archive_path.stat().st_size,
        "manifest": manifest,
    }


def validate_backup_archive(path: Path, expected_checksum: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError("Arquivo de backup não encontrado")
    actual_checksum = sha256_file(path)
    if expected_checksum and actual_checksum != expected_checksum:
        raise ValueError("Checksum do backup não confere")
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
        required = {"database.dump", "manifest.json"}
        missing = required.difference(names)
        if missing:
            raise ValueError(f"Backup incompleto: {', '.join(sorted(missing))}")
        with tempfile.TemporaryDirectory(prefix="educode-restore-test-") as temp_dir:
            archive.extract("database.dump", path=temp_dir, filter="data")
            dump_path = Path(temp_dir) / "database.dump"
            process = _run_command(["pg_restore", "--list", str(dump_path)], os.environ.copy())
            object_count = len(
                [line for line in process.stdout.splitlines() if line and not line.startswith(";")]
            )
    return {
        "checksum_valid": True,
        "archive_entries": len(names),
        "database_objects": object_count,
        "sample_entries": names[:20],
    }


def execute_restore_test(backup: BackupRun, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    archive_path = Path(backup.storage_path)
    structural = validate_backup_archive(archive_path, backup.checksum_sha256)
    common_args, source_database, env = _database_connection(settings)
    temporary_database = f"educode_restore_{uuid4().hex[:12]}"
    created = False
    with tempfile.TemporaryDirectory(prefix="educode-real-restore-") as temp_dir:
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extract("database.dump", path=temp_dir, filter="data")
        dump_path = Path(temp_dir) / "database.dump"
        try:
            _run_command(["createdb", *common_args, temporary_database], env)
            created = True
            _run_command(
                [
                    "pg_restore",
                    *common_args,
                    "--dbname", temporary_database,
                    "--no-owner",
                    "--no-privileges",
                    str(dump_path),
                ],
                env,
            )
            table_result = _run_command(
                [
                    "psql",
                    *common_args,
                    "--dbname", temporary_database,
                    "--tuples-only",
                    "--no-align",
                    "--command",
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';",
                ],
                env,
            )
            migration_result = _run_command(
                [
                    "psql",
                    *common_args,
                    "--dbname", temporary_database,
                    "--tuples-only",
                    "--no-align",
                    "--command",
                    "SELECT version_num FROM alembic_version LIMIT 1;",
                ],
                env,
            )
            return {
                **structural,
                "real_restore": True,
                "source_database": source_database,
                "temporary_database": temporary_database,
                "restored_public_tables": int(table_result.stdout.strip() or "0"),
                "restored_migration": migration_result.stdout.strip(),
            }
        finally:
            if created:
                _run_command(["dropdb", *common_args, "--if-exists", temporary_database], env)


async def integrity_report(session: AsyncSession, organization_id: UUID) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    incomplete_attempts = await session.scalar(
        select(func.count(StudentAttempt.id)).where(
            StudentAttempt.organization_id == organization_id,
            StudentAttempt.status == AttemptStatus.SUBMITTED,
            StudentAttempt.grading_complete.is_(False),
        )
    )
    findings.append({
        "code": "ATTEMPT_WITHOUT_FINAL_SCORE",
        "severity": "warning" if incomplete_attempts else "info",
        "count": int(incomplete_attempts or 0),
        "description": "Tentativas enviadas sem nota final.",
        "sample_ids": [],
    })
    orphan_answers = await session.scalar(
        select(func.count(StudentAnswer.id))
        .join(StudentAttempt, StudentAttempt.id == StudentAnswer.attempt_id)
        .where(StudentAttempt.organization_id == organization_id, StudentAnswer.question_id.is_(None))
    )
    findings.append({
        "code": "ANSWER_WITHOUT_QUESTION",
        "severity": "critical" if orphan_answers else "info",
        "count": int(orphan_answers or 0),
        "description": "Respostas sem questão vinculada.",
        "sample_ids": [],
    })
    stuck_jobs = await session.scalar(
        select(func.count(BackgroundJob.id)).where(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.status.in_(["processing", "validating", "waiting_provider"]),
            BackgroundJob.updated_at < utcnow() - timedelta(minutes=15),
        )
    )
    findings.append({
        "code": "STUCK_BACKGROUND_JOB",
        "severity": "warning" if stuck_jobs else "info",
        "count": int(stuck_jobs or 0),
        "description": "Tarefas sem atualização há mais de 15 minutos.",
        "sample_ids": [],
    })
    return findings
