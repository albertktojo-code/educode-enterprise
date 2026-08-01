from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.models.auth import Membership, OrganizationRole, User
from app.models.platform import BackupRun
from app.services.object_storage import storage_from_settings
from app.services.platform import execute_backup, utcnow


async def run() -> int:
    async with AsyncSessionFactory() as session:
        membership = await session.scalar(
            select(Membership)
            .join(User, User.id == Membership.user_id)
            .where(
                Membership.is_active.is_(True),
                Membership.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN]),
                User.is_superuser.is_(True),
            )
            .limit(1)
        )
        if membership is None:
            print("Nenhum administrador ativo encontrado.")
            return 2
        user = await session.get(User, membership.user_id)
        if user is None:
            print("Usuário administrador não encontrado.")
            return 2
        backup = BackupRun(
            organization_id=membership.organization_id,
            requested_by_user_id=user.id,
            backup_type="full",
            status="processing",
            started_at=utcnow(),
            expires_at=utcnow() + timedelta(days=30),
        )
        session.add(backup)
        await session.commit()
        await session.refresh(backup)
    try:
        settings = get_settings()
        result = await asyncio.to_thread(execute_backup, backup, settings)
        if settings.object_storage_provider == "s3":
            archive_path = result["storage_path"]
            content = await asyncio.to_thread(Path(archive_path).read_bytes)
            replica = await storage_from_settings(settings).put_bytes(
                f"backups/{backup.organization_id}/{Path(archive_path).name}",
                content,
                "application/gzip",
            )
            result["object_storage_replica"] = {
                "key": replica.key,
                "size_bytes": replica.size_bytes,
                "checksum_sha256": replica.checksum_sha256,
            }
            result["manifest"]["object_storage_replica"] = result["object_storage_replica"]
        async with AsyncSessionFactory() as session:
            stored = await session.get(BackupRun, backup.id)
            if stored is None:
                return 3
            stored.status = "completed"
            stored.storage_path = result["storage_path"]
            stored.checksum_sha256 = result["checksum_sha256"]
            stored.size_bytes = result["size_bytes"]
            stored.manifest = result["manifest"]
            stored.completed_at = utcnow()
            await session.commit()
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:
        async with AsyncSessionFactory() as session:
            stored = await session.get(BackupRun, backup.id)
            if stored is not None:
                stored.status = "failed"
                stored.error_code = "BACKUP_FAILED"
                stored.error_message = str(exc)
                stored.completed_at = utcnow()
                await session.commit()
        print(f"Falha no backup: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
