from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.anime_studio.models import AnimeProject, AnimeRender
from app.anime_studio.storage import AnimeMediaStorage
from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.models.assets import (
    InstitutionalAsset,
    InstitutionalAssetAudit,
    InstitutionalAssetFile,
    InstitutionalAssetStatus,
    InstitutionalAssetType,
    InstitutionalAssetVariant,
    InstitutionalAssetVersion,
    InstitutionalAssetVisibility,
    InstitutionalLicenseType,
)
from app.models.operations import BackgroundJob

ProgressCallback = Callable[[int, str, dict[str, Any] | None], Awaitable[None]]


def _seconds(milliseconds: int | None, default: float = 0.0) -> float:
    return round((milliseconds or 0) / 1000, 3) if milliseconds is not None else default


def _srt_timestamp(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


async def _run_ffmpeg(arguments: list[str], *, cwd: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        *arguments,
        cwd=str(cwd),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        message = stderr.decode("utf-8", errors="replace")[-4000:]
        raise RuntimeError(f"FFmpeg falhou: {message}")


async def _load_asset_file(
    file_id: UUID, organization_id: UUID
) -> tuple[InstitutionalAssetFile, InstitutionalAsset]:
    async with AsyncSessionFactory() as session:
        row = await session.scalar(
            select(InstitutionalAssetFile)
            .where(InstitutionalAssetFile.id == file_id)
            .options(selectinload(InstitutionalAssetFile.asset))
        )
        if row is None or row.asset.organization_id != organization_id:
            raise RuntimeError("Arquivo institucional fora da organização")
        if not row.asset.rights_confirmed:
            raise RuntimeError(f"Direitos de uso não confirmados para {row.file_name}")
        return row, row.asset


def _scene_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"fps={fps},format=yuv420p"
    )


def rendition_profiles(width: int, height: int) -> list[dict[str, int | str]]:
    profiles: list[dict[str, int | str]] = []
    for target_height in (720, 480):
        if target_height >= height:
            continue
        target_width = max(2, round(width * target_height / height / 2) * 2)
        profiles.append(
            {
                "label": f"{target_height}p",
                "width": target_width,
                "height": target_height,
            }
        )
    return profiles


async def _transcode_rendition(
    source: Path,
    destination: Path,
    *,
    width: int,
    height: int,
) -> None:
    await _run_ffmpeg(
        [
            "-i",
            str(source),
            "-vf",
            f"scale={width}:{height}:flags=lanczos,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "24",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(destination),
        ],
        cwd=destination.parent,
    )


async def _render_scene(
    *,
    source: Path,
    mime_type: str,
    destination: Path,
    duration_ms: int,
    width: int,
    height: int,
    fps: int,
    quality: str,
) -> None:
    duration = str(_seconds(duration_ms))
    preset = {"preview": "veryfast", "standard": "medium", "high": "slow"}.get(quality, "veryfast")
    prefix = ["-loop", "1"] if mime_type.startswith("image/") else []
    await _run_ffmpeg(
        [
            *prefix,
            "-i",
            str(source),
            "-t",
            duration,
            "-vf",
            _scene_filter(width, height, fps),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            preset,
            "-movflags",
            "+faststart",
            str(destination),
        ],
        cwd=destination.parent,
    )


async def _compose_audio(
    *,
    video: Path,
    output: Path,
    tracks: list[dict[str, Any]],
    total_duration_ms: int,
    normalize_audio: bool,
) -> None:
    arguments = ["-i", str(video)]
    filters: list[str] = []
    labels: list[str] = []
    for index, track in enumerate(tracks, start=1):
        arguments.extend(["-i", str(track["path"])])
        duration = track.get("duration_ms")
        chain = [f"[{index}:a]atrim=start={_seconds(track.get('trim_start_ms'))}"]
        if duration:
            chain[0] += f":duration={_seconds(duration)}"
        chain.extend(
            [
                "asetpts=PTS-STARTPTS",
                f"volume={float(track.get('volume', 1.0))}",
            ]
        )
        fade_in = _seconds(track.get("fade_in_ms"))
        fade_out = _seconds(track.get("fade_out_ms"))
        if fade_in > 0:
            chain.append(f"afade=t=in:st=0:d={fade_in}")
        if fade_out > 0 and duration:
            fade_at = max(0.0, _seconds(duration) - fade_out)
            chain.append(f"afade=t=out:st={fade_at}:d={fade_out}")
        delay = int(track.get("start_ms") or 0)
        chain.append(f"adelay={delay}:all=1")
        label = f"a{index}"
        filters.append(",".join(chain) + f"[{label}]")
        labels.append(f"[{label}]")

    total_duration = str(_seconds(total_duration_ms))
    if labels:
        normalize = 1 if normalize_audio else 0
        filters.append(
            "".join(labels)
            + f"amix=inputs={len(labels)}:duration=longest:normalize={normalize},"
            + f"atrim=duration={total_duration},alimiter=limit=0.95[mix]"
        )
        arguments.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "0:v:0",
                "-map",
                "[mix]",
            ]
        )
    else:
        arguments.extend(
            [
                "-f",
                "lavfi",
                "-t",
                total_duration,
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
            ]
        )
    arguments.extend(
        [
            "-t",
            total_duration,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    await _run_ffmpeg(arguments, cwd=output.parent)


async def _burn_captions(video: Path, output: Path, captions: list[dict[str, Any]]) -> None:
    srt = video.parent / "captions.srt"
    srt.write_text(
        "\n\n".join(
            f"{index}\n{_srt_timestamp(cue['start_ms'])} --> "
            f"{_srt_timestamp(cue['end_ms'])}\n"
            f"{(cue.get('speaker') + ': ') if cue.get('speaker') else ''}{cue['text']}"
            for index, cue in enumerate(captions, start=1)
        ),
        encoding="utf-8",
    )
    await _run_ffmpeg(
        [
            "-i",
            str(video),
            "-vf",
            "subtitles=captions.srt:force_style='FontSize=22,Outline=2,Shadow=1,MarginV=28'",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(output),
        ],
        cwd=video.parent,
    )


async def render_anime_job(job: BackgroundJob, progress: ProgressCallback) -> dict[str, Any]:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg não está instalado no worker de mídia")
    render_id = UUID(str(job.input_snapshot["render_id"]))
    settings = get_settings()
    storage = AnimeMediaStorage(
        settings.institutional_asset_storage_path,
        settings.max_anime_media_size_mb * 1024 * 1024,
    )
    saved_storage_keys: list[str] = []
    async with AsyncSessionFactory() as session:
        render = await session.get(AnimeRender, render_id)
        if render is None or render.organization_id != job.organization_id:
            raise RuntimeError("Renderização de anime não encontrada")
        project = await session.scalar(
            select(AnimeProject).where(
                AnimeProject.id == render.project_id,
                AnimeProject.organization_id == job.organization_id,
            )
        )
        if project is None:
            raise RuntimeError("Produção de anime não encontrada")
        render.status = "processing"
        project.status = "rendering"
        snapshot = dict(render.source_snapshot)
        project_snapshot = dict(snapshot["project"])
        scenes_snapshot = list(snapshot.get("scenes", []))
        audio_tracks_snapshot = list(snapshot.get("audio_tracks", []))
        captions_snapshot = list(snapshot.get("captions", []))
        await session.commit()

    try:
        await progress(8, "Validando storyboard e direitos de mídia", None)
        with tempfile.TemporaryDirectory(prefix="educode-anime-") as temporary:
            workdir = Path(temporary)
            scene_outputs: list[Path] = []
            ordered_scenes = sorted(scenes_snapshot, key=lambda item: int(item["position"]))
            for index, scene in enumerate(ordered_scenes, start=1):
                visual_asset_file_id = scene.get("visual_asset_file_id")
                if visual_asset_file_id is None:
                    raise RuntimeError(f"Cena {scene['position']} sem mídia visual")
                source_file, _ = await _load_asset_file(
                    UUID(str(visual_asset_file_id)), project.organization_id
                )
                scene_output = workdir / f"scene-{index:04}.mp4"
                await _render_scene(
                    source=storage.resolve(source_file.storage_key),
                    mime_type=source_file.mime_type,
                    destination=scene_output,
                    duration_ms=int(scene["duration_ms"]),
                    width=int(project_snapshot["width"]),
                    height=int(project_snapshot["height"]),
                    fps=int(project_snapshot["fps"]),
                    quality=str(render.render_settings.get("quality", "preview")),
                )
                scene_outputs.append(scene_output)
                await progress(
                    10 + int(index / len(ordered_scenes) * 40),
                    f"Compondo cena {index} de {len(ordered_scenes)}",
                    {"scene_id": str(scene["id"]), "position": int(scene["position"])},
                )

            concat_manifest = workdir / "scenes.txt"
            concat_manifest.write_text(
                "\n".join(f"file '{path.as_posix()}'" for path in scene_outputs),
                encoding="utf-8",
            )
            silent_video = workdir / "silent.mp4"
            await _run_ffmpeg(
                [
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_manifest),
                    "-c",
                    "copy",
                    str(silent_video),
                ],
                cwd=workdir,
            )
            await progress(58, "Sincronizando diálogos, música e efeitos", None)

            audio_inputs: list[dict[str, Any]] = []
            for track in audio_tracks_snapshot:
                if track.get("is_muted") or track.get("asset_file_id") is None:
                    continue
                audio_file, _ = await _load_asset_file(
                    UUID(str(track["asset_file_id"])), project.organization_id
                )
                if not audio_file.mime_type.startswith("audio/"):
                    raise RuntimeError(f"Faixa {track['id']} não aponta para áudio")
                audio_inputs.append(
                    {
                        "path": storage.resolve(audio_file.storage_key),
                        "start_ms": track.get("start_ms", 0),
                        "duration_ms": track.get("duration_ms"),
                        "trim_start_ms": track.get("trim_start_ms", 0),
                        "volume": track.get("volume", 1.0),
                        "fade_in_ms": track.get("fade_in_ms", 0),
                        "fade_out_ms": track.get("fade_out_ms", 0),
                    }
                )
            total_duration_ms = sum(int(scene["duration_ms"]) for scene in ordered_scenes)
            mixed_video = workdir / "mixed.mp4"
            await _compose_audio(
                video=silent_video,
                output=mixed_video,
                tracks=audio_inputs,
                total_duration_ms=total_duration_ms,
                normalize_audio=bool(render.render_settings.get("normalize_audio", True)),
            )

            language = str(
                render.render_settings.get("caption_language", project_snapshot["language"])
            )
            captions = [
                {
                    "start_ms": int(cue["start_ms"]),
                    "end_ms": int(cue["end_ms"]),
                    "text": str(cue["text"]),
                    "speaker": str(cue.get("speaker", "")),
                }
                for cue in sorted(captions_snapshot, key=lambda item: int(item["cue_order"]))
                if cue["language"] == language
            ]
            final_video = mixed_video
            if bool(render.render_settings.get("burn_captions", True)) and captions:
                await progress(76, "Aplicando legendas acessíveis", None)
                captioned_video = workdir / "captioned.mp4"
                await _burn_captions(mixed_video, captioned_video, captions)
                final_video = captioned_video

            profiles = rendition_profiles(
                int(project_snapshot["width"]),
                int(project_snapshot["height"]),
            )
            rendition_outputs: list[tuple[dict[str, int | str], Path]] = []
            if profiles:
                await progress(82, "Gerando resoluções otimizadas", None)
            for profile in profiles:
                rendition_output = workdir / f"rendition-{profile['label']}.mp4"
                await _transcode_rendition(
                    final_video,
                    rendition_output,
                    width=int(profile["width"]),
                    height=int(profile["height"]),
                )
                rendition_outputs.append((profile, rendition_output))

            await progress(88, "Salvando vídeo na biblioteca institucional", None)
            saved = storage.save_render(
                final_video,
                project.organization_id,
                file_name=f"{project_snapshot['title']}-v{render.revision}.mp4",
            )
            saved_storage_keys.append(saved.storage_key)
            saved_renditions = []
            for profile, output in rendition_outputs:
                rendition = storage.save_render(
                    output,
                    project.organization_id,
                    file_name=(
                        f"{project_snapshot['title']}-v{render.revision}-{profile['label']}.mp4"
                    ),
                )
                saved_storage_keys.append(rendition.storage_key)
                saved_renditions.append((profile, rendition))
            async with AsyncSessionFactory() as output_session:
                stored_render = await output_session.get(AnimeRender, render.id)
                stored_project = await output_session.get(AnimeProject, project.id)
                if stored_render is None or stored_project is None:
                    for storage_key in saved_storage_keys:
                        storage.delete(storage_key)
                    raise RuntimeError("Estado da produção foi removido durante a renderização")
                asset = InstitutionalAsset(
                    organization_id=project.organization_id,
                    asset_type=InstitutionalAssetType.OTHER,
                    name=(
                        f"{project_snapshot['title']} · render {render.revision} · "
                        f"{str(project.id)[:8]}"
                    ),
                    description="Vídeo de anime educacional aguardando revisão humana.",
                    category="Vídeos Anime",
                    status=InstitutionalAssetStatus.IN_REVIEW,
                    visibility=InstitutionalAssetVisibility.PROJECT_ONLY,
                    metadata_json={
                        "anime_project_id": str(project.id),
                        "anime_render_id": str(render.id),
                        "duration_ms": total_duration_ms,
                        "fps": int(project_snapshot["fps"]),
                        "resolution": [
                            int(project_snapshot["width"]),
                            int(project_snapshot["height"]),
                        ],
                        "rendition_profiles": profiles,
                        "captions_burned": bool(
                            render.render_settings.get("burn_captions", True) and captions
                        ),
                    },
                    compatibility=["anime", "video", "presentation"],
                    license_type=InstitutionalLicenseType.AUTHORIZED_USE,
                    original_author="EduCode",
                    rights_confirmed=True,
                    created_by_user_id=render.requested_by_user_id,
                )
                asset.versions.append(
                    InstitutionalAssetVersion(
                        version_number=1,
                        snapshot_json={
                            "anime_project_id": str(project.id),
                            "anime_render_id": str(render.id),
                            "manifest_checksum": render.manifest_checksum,
                            "render_settings": render.render_settings,
                        },
                        change_description="Render audiovisual criado pelo Estúdio Anime",
                        created_by_user_id=render.requested_by_user_id,
                    )
                )
                output_session.add(asset)
                await output_session.flush()
                asset_file = InstitutionalAssetFile(
                    asset_id=asset.id,
                    file_name=saved.file_name,
                    mime_type=saved.mime_type,
                    storage_key=saved.storage_key,
                    checksum_sha256=saved.checksum_sha256,
                    size_bytes=saved.size_bytes,
                    width=int(project_snapshot["width"]),
                    height=int(project_snapshot["height"]),
                    view_type="anime_render",
                    is_primary=True,
                    is_original=False,
                )
                output_session.add(asset_file)
                await output_session.flush()
                rendition_file_ids: list[str] = []
                for profile, rendition in saved_renditions:
                    variant = InstitutionalAssetVariant(
                        asset_id=asset.id,
                        name=str(profile["label"]),
                        variant_type="video_resolution",
                        metadata_json={
                            "width": int(profile["width"]),
                            "height": int(profile["height"]),
                        },
                    )
                    output_session.add(variant)
                    await output_session.flush()
                    rendition_file = InstitutionalAssetFile(
                        asset_id=asset.id,
                        variant_id=variant.id,
                        file_name=rendition.file_name,
                        mime_type=rendition.mime_type,
                        storage_key=rendition.storage_key,
                        checksum_sha256=rendition.checksum_sha256,
                        size_bytes=rendition.size_bytes,
                        width=int(profile["width"]),
                        height=int(profile["height"]),
                        view_type=f"anime_render_{profile['label']}",
                        is_primary=False,
                        is_original=False,
                    )
                    output_session.add(rendition_file)
                    await output_session.flush()
                    rendition_file_ids.append(str(rendition_file.id))
                output_session.add(
                    InstitutionalAssetAudit(
                        organization_id=project.organization_id,
                        asset_id=asset.id,
                        actor_user_id=render.requested_by_user_id,
                        action="anime_render_created",
                        details={
                            "anime_project_id": str(project.id),
                            "anime_render_id": str(render.id),
                        },
                    )
                )
                stored_render.output_asset_id = asset.id
                stored_render.output_asset_file_id = asset_file.id
                stored_render.duration_ms = total_duration_ms
                stored_render.status = "in_review"
                stored_render.error_message = ""
                stored_project.status = "in_review"
                await output_session.commit()
                output_asset_id = asset.id
                saved_storage_keys = []
                output_file_id = asset_file.id
        await progress(96, "Vídeo pronto para revisão humana", None)
        return {
            "render_id": str(render.id),
            "project_id": str(project.id),
            "output_asset_id": str(output_asset_id),
            "output_asset_file_id": str(output_file_id),
            "rendition_file_ids": rendition_file_ids,
            "duration_ms": total_duration_ms,
            "review_required": True,
        }
    except Exception as exc:
        for storage_key in saved_storage_keys:
            storage.delete(storage_key)
        async with AsyncSessionFactory() as error_session:
            failed_render = await error_session.get(AnimeRender, render_id)
            if failed_render is not None:
                failed_render.status = "failed"
                failed_render.error_message = str(exc)[:4000]
                failed_project = await error_session.get(AnimeProject, failed_render.project_id)
                if failed_project is not None:
                    failed_project.status = "draft"
                await error_session.commit()
        raise
