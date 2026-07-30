from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.platform import BackupRun, DeploymentRelease
from app.models.release import (
    DeploymentApproval,
    DeploymentStep,
    MaintenanceWindow,
    ReleaseArtifact,
    ReleaseValidationRun,
)

DESTRUCTIVE_PATTERNS = {
    "drop_table": re.compile(r"\bDROP\s+TABLE\b", re.I),
    "drop_column": re.compile(r"\bDROP\s+COLUMN\b", re.I),
    "alter_type": re.compile(r"\bALTER\s+COLUMN\b.*\bTYPE\b", re.I | re.S),
    "truncate": re.compile(r"\bTRUNCATE\b", re.I),
    "not_null": re.compile(r"\bSET\s+NOT\s+NULL\b", re.I),
}

REQUIRED_RELEASE_STEPS = [
    (10, "preflight", "Preflight de ambiente"),
    (20, "migration_check", "Validação das migrations"),
    (30, "security_scan", "SBOM e vulnerabilidades"),
    (40, "backup", "Backup pré-implantação"),
    (50, "worker_drain", "Drenagem dos workers"),
    (60, "deploy", "Implantação dos artefatos"),
    (70, "migration", "Aplicação da migration"),
    (80, "smoke", "Smoke tests pós-implantação"),
    (90, "monitor", "Janela de monitoramento"),
]


def utcnow() -> datetime:
    return datetime.now(UTC)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_revision_id(revision: str) -> list[str]:
    problems: list[str] = []
    if len(revision) > 32:
        problems.append("O identificador excede 32 caracteres")
    if not re.fullmatch(r"[a-zA-Z0-9_]+", revision):
        problems.append("O identificador possui caracteres inválidos")
    return problems


def scan_migration_sql(sql: str) -> dict[str, Any]:
    findings = [name for name, pattern in DESTRUCTIVE_PATTERNS.items() if pattern.search(sql)]
    return {
        "safe": not findings,
        "destructive_operations": findings,
        "requires_manual_approval": bool(findings),
        "sql_sha256": sha256_text(sql),
        "line_count": len(sql.splitlines()),
    }


def validate_artifact_digest(artifact: ReleaseArtifact) -> bool:
    return bool(re.fullmatch(r"[a-fA-F0-9]{64}", artifact.digest_sha256 or "")) or bool(
        artifact.image_digest.startswith("sha256:") and len(artifact.image_digest) >= 71
    )


def configuration_release_warnings(settings: Settings | None = None) -> list[str]:
    settings = settings or get_settings()
    warnings: list[str] = []
    if settings.environment in {"homologation", "staging", "production"}:
        if settings.jwt_secret_key.startswith("change-me") or settings.jwt_secret_key.startswith("troque-"):
            warnings.append("JWT_SECRET_KEY ainda usa valor de desenvolvimento")
        if not settings.public_base_url.startswith("https://"):
            warnings.append("PUBLIC_BASE_URL deve utilizar HTTPS")
        if "localhost" in " ".join(settings.backend_cors_origins):
            warnings.append("CORS contém localhost")
        if settings.deployment_strategy == "blue_green" and not settings.reverse_proxy_enabled:
            warnings.append("Blue-green requer proxy reverso habilitado")
    return warnings


async def ensure_release_steps(session: AsyncSession, release: DeploymentRelease) -> list[DeploymentStep]:
    existing = list(
        (
            await session.scalars(
                select(DeploymentStep)
                .where(DeploymentStep.release_id == release.id)
                .order_by(DeploymentStep.step_order)
            )
        ).all()
    )
    if existing:
        return existing
    for order, key, title in REQUIRED_RELEASE_STEPS:
        session.add(
            DeploymentStep(
                organization_id=release.organization_id,
                release_id=release.id,
                step_order=order,
                step_key=key,
                title=title,
                status="pending",
                is_blocking=True,
            )
        )
    await session.flush()
    return list(
        (
            await session.scalars(
                select(DeploymentStep)
                .where(DeploymentStep.release_id == release.id)
                .order_by(DeploymentStep.step_order)
            )
        ).all()
    )


async def release_readiness(session: AsyncSession, release: DeploymentRelease) -> dict[str, Any]:
    steps = list(
        (
            await session.scalars(
                select(DeploymentStep).where(DeploymentStep.release_id == release.id)
            )
        ).all()
    )
    approvals = list(
        (
            await session.scalars(
                select(DeploymentApproval).where(DeploymentApproval.release_id == release.id)
            )
        ).all()
    )
    artifacts = list(
        (
            await session.scalars(
                select(ReleaseArtifact).where(ReleaseArtifact.release_id == release.id)
            )
        ).all()
    )
    validations = list(
        (
            await session.scalars(
                select(ReleaseValidationRun).where(ReleaseValidationRun.release_id == release.id)
            )
        ).all()
    )
    backup_ready = bool(
        await session.scalar(
            select(func.count(BackupRun.id)).where(
                BackupRun.organization_id == release.organization_id,
                BackupRun.status == "completed",
                BackupRun.created_at <= utcnow(),
            )
        )
    )
    blockers: list[str] = []
    warnings: list[str] = []
    if not artifacts:
        blockers.append("Nenhum artefato imutável foi registrado")
    elif any(not validate_artifact_digest(item) for item in artifacts):
        blockers.append("Há artefatos sem digest válido")
    if not backup_ready:
        blockers.append("Não existe backup concluído para a implantação")
    blocking_steps = [step for step in steps if step.is_blocking and step.status not in {"completed", "skipped"}]
    if blocking_steps:
        blockers.append(f"{len(blocking_steps)} etapas obrigatórias ainda não foram concluídas")
    approval_map = {item.approval_stage: item.status for item in approvals}
    required_approvals = {"technical", "security"}
    if release.environment == "production":
        required_approvals |= {"business", "production"}
    missing_approvals = [stage for stage in required_approvals if approval_map.get(stage) != "approved"]
    if missing_approvals:
        blockers.append("Aprovações pendentes: " + ", ".join(sorted(missing_approvals)))
    failed_validations = [item for item in validations if item.status == "failed"]
    if failed_validations:
        blockers.append("Há validações de release com falha")
    if not validations:
        warnings.append("Nenhuma validação automatizada foi registrada")
    migration_safe = not any(
        item.validation_type == "migration" and item.blockers for item in validations
    )
    completed_steps = len([step for step in steps if step.status in {"completed", "skipped"}])
    total_steps = len(steps)
    score = 100.0
    score -= min(70, len(blockers) * 20)
    score -= min(20, len(warnings) * 5)
    return {
        "release_id": release.id,
        "ready": not blockers,
        "score": max(0.0, score),
        "blockers": blockers,
        "warnings": warnings,
        "completed_steps": completed_steps,
        "total_steps": total_steps,
        "approvals": approval_map,
        "artifact_count": len(artifacts),
        "backup_ready": backup_ready,
        "migration_safe": migration_safe,
    }


def active_maintenance(window: MaintenanceWindow, now: datetime | None = None) -> bool:
    now = now or utcnow()
    return window.status in {"scheduled", "active"} and window.starts_at <= now < window.ends_at


def selective_restore_plan(entity_type: str, entity_id: str | None, restore_mode: str) -> dict[str, Any]:
    dependencies = {
        "organization": ["users", "projects", "documents", "assessments", "assets"],
        "project": ["documents", "comics", "pedagogy", "assignments"],
        "comic": ["pages", "panels", "balloons", "versions", "assets"],
        "assessment": ["versions", "items", "assignments", "attempts", "answers"],
        "asset_collection": ["collection_items", "asset_versions", "files"],
        "document": ["pages", "chapters", "chunks", "rag_contexts"],
        "report": ["analysis", "charts", "dataset_snapshot"],
        "character": ["variants", "files", "versions", "comic_usages"],
    }
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "restore_mode": restore_mode,
        "dependencies": dependencies.get(entity_type, []),
        "destructive": restore_mode == "replace",
        "requires_confirmation": True,
        "recommended_mode": "new_version" if entity_type in {"comic", "assessment", "report", "character"} else "copy",
    }
