from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.anime_studio.storage import AnimeMediaStorage
from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.models.assets import (
    InstitutionalAsset,
    InstitutionalAssetAudit,
    InstitutionalAssetFile,
    InstitutionalAssetStatus,
    InstitutionalAssetType,
    InstitutionalAssetVersion,
    InstitutionalAssetVisibility,
    InstitutionalLicenseType,
)
from app.models.operations import BackgroundJob

ProgressCallback = Callable[[int, str, dict[str, Any] | None], Awaitable[None]]


def generated_media_contract(kind: str, duration_ms: int) -> dict[str, Any]:
    duration_seconds = max(duration_ms / 1000, 0.5)
    if kind == "image":
        return {"media_kind": "image", "suffix": ".png", "mime_type": "image/png"}
    if kind in {"animation", "lip_sync"}:
        return {
            "media_kind": "video",
            "suffix": ".mp4",
            "mime_type": "video/mp4",
            "duration_seconds": duration_seconds,
        }
    return {
        "media_kind": "audio",
        "suffix": ".wav",
        "mime_type": "audio/wav",
        "duration_seconds": duration_seconds,
    }


async def _run_ffmpeg(kind: str, duration_ms: int, output: Path) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg nao esta instalado no worker de midia")
    duration = max(duration_ms / 1000, 0.5)
    if kind == "image":
        args = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x312e81:s=1280x720",
            "-frames:v",
            "1",
            str(output),
        ]
    elif kind in {"animation", "lip_sync"}:
        args = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x312e81:s=1280x720:d={duration}",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    else:
        frequencies = {"voice": 440, "music": 262, "sfx": 880}
        args = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequencies.get(kind, 440)}:duration={duration}",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    process = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace")[-2000:])


async def generate_anime_media_job(
    job: BackgroundJob, progress: ProgressCallback
) -> dict[str, Any]:
    snapshot = dict(job.input_snapshot or {})
    kind = str(snapshot["kind"])
    duration_ms = int(snapshot.get("duration_ms") or 5000)
    contract = generated_media_contract(kind, duration_ms)
    await progress(15, "Preparando provedor interno de fallback", {"kind": kind})
    settings = get_settings()
    storage = AnimeMediaStorage(
        settings.institutional_asset_storage_path,
        settings.max_anime_media_size_mb * 1024 * 1024,
    )
    saved = None
    with tempfile.TemporaryDirectory(prefix="educode-anime-generation-") as temporary:
        output = Path(temporary) / f"anime-{kind}-{str(job.id)[:8]}{contract['suffix']}"
        await _run_ffmpeg(kind, duration_ms, output)
        await progress(70, "Validando e armazenando artefato", None)
        saved = storage.save_generated(
            output,
            job.organization_id,
            media_kind=str(contract["media_kind"]),
            file_name=output.name,
            mime_type=str(contract["mime_type"]),
        )
    try:
        async with AsyncSessionFactory() as session:
            asset = InstitutionalAsset(
                organization_id=job.organization_id,
                asset_type=InstitutionalAssetType.OTHER,
                name=f"Anime {kind} {str(job.id)[:8]}",
                description="Artefato gerado pelo provedor interno, aguardando revisao humana.",
                category="Midia Anime Gerada",
                status=InstitutionalAssetStatus.IN_REVIEW,
                visibility=InstitutionalAssetVisibility.PROJECT_ONLY,
                metadata_json={**snapshot, "provider": "educode_internal_ffmpeg"},
                compatibility=["anime", str(contract["media_kind"]), kind],
                license_type=InstitutionalLicenseType.AUTHORIZED_USE,
                original_author="EduCode Internal Media Provider",
                rights_confirmed=True,
                created_by_user_id=job.requested_by_user_id,
            )
            session.add(asset)
            await session.flush()
            asset_file = InstitutionalAssetFile(
                asset_id=asset.id,
                file_name=saved.file_name,
                mime_type=saved.mime_type,
                storage_key=saved.storage_key,
                checksum_sha256=saved.checksum_sha256,
                size_bytes=saved.size_bytes,
                width=1280 if contract["media_kind"] in {"image", "video"} else None,
                height=720 if contract["media_kind"] in {"image", "video"} else None,
                view_type=f"anime_generated_{kind}",
                is_primary=True,
                is_original=False,
            )
            session.add(asset_file)
            asset.versions.append(
                InstitutionalAssetVersion(
                    version_number=1,
                    snapshot_json={
                        "job_id": str(job.id),
                        "provider": "educode_internal_ffmpeg",
                        **snapshot,
                    },
                    change_description="Artefato audiovisual gerado para revisao humana",
                    created_by_user_id=job.requested_by_user_id,
                )
            )
            await session.flush()
            session.add(
                InstitutionalAssetAudit(
                    organization_id=job.organization_id,
                    asset_id=asset.id,
                    actor_user_id=job.requested_by_user_id,
                    action="anime_media_generated",
                    details={
                        "job_id": str(job.id),
                        "kind": kind,
                        "provider": "educode_internal_ffmpeg",
                    },
                )
            )
            await session.commit()
            result = {
                "output_asset_id": str(asset.id),
                "output_asset_file_id": str(asset_file.id),
                "provider": "educode_internal_ffmpeg",
                "media_kind": contract["media_kind"],
                "mime_type": contract["mime_type"],
                "review_required": True,
            }
    except Exception:
        if saved is not None:
            storage.delete(saved.storage_key)
        raise
    await progress(95, "Artefato pronto para revisao humana", None)
    return result
