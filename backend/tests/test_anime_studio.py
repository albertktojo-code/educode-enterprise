import shutil
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.anime_studio.generation import _run_ffmpeg, generated_media_contract
from app.anime_studio.models import AnimeProject
from app.anime_studio.rendering import _scene_filter, _srt_timestamp
from app.anime_studio.schemas import (
    AnimeAudioTrackCreate,
    AnimeAudioTrackUpdate,
    AnimeCaptionCreate,
    AnimeMediaGenerationCreate,
    AnimeProjectCreate,
    AnimeSceneSplit,
    AnimeStoryboardImport,
    AnimeTimelineReorder,
)
from app.anime_studio.services import (
    estimate_media_generation_cost,
    render_snapshot,
    storyboard_scene_inputs,
)
from app.anime_studio.storage import AnimeMediaStorage, InvalidAnimeMediaError


def test_project_contract_supports_landscape_and_vertical_video() -> None:
    landscape = AnimeProjectCreate(title="Algoritmos em movimento")
    vertical = AnimeProjectCreate(
        title="Decomposição em um minuto",
        aspect_ratio="9:16",
        width=1080,
        height=1920,
        fps=30,
    )
    assert landscape.aspect_ratio == "16:9"
    assert (vertical.width, vertical.height, vertical.fps) == (1080, 1920, 30)


def test_caption_requires_positive_time_window() -> None:
    with pytest.raises(ValidationError):
        AnimeCaptionCreate(
            cue_order=1,
            start_ms=3000,
            end_ms=2000,
            text="Janela inválida",
        )


def test_audio_contract_supports_accessibility_and_mixing() -> None:
    track = AnimeAudioTrackCreate(
        track_kind="audio_description",
        label="Audiodescrição da cena",
        transcript="A personagem aponta para um diagrama.",
        start_ms=1200,
        volume=0.85,
        fade_in_ms=250,
    )
    assert track.track_kind == "audio_description"
    assert track.volume == 0.85


def test_audio_mix_update_supports_cuts_fades_volume_and_mute() -> None:
    mix = AnimeAudioTrackUpdate(
        start_ms=1200,
        duration_ms=5000,
        trim_start_ms=500,
        volume=0.7,
        fade_in_ms=250,
        fade_out_ms=400,
        is_muted=True,
    )
    assert mix.duration_ms == 5000
    assert mix.trim_start_ms == 500
    assert mix.volume == 0.7
    assert mix.fade_in_ms == 250
    assert mix.fade_out_ms == 400
    assert mix.is_muted is True


def test_storyboard_import_maps_hq_panel_into_timed_anime_scene() -> None:
    comic_id, page_id, panel_id = uuid4(), uuid4(), uuid4()
    request = AnimeStoryboardImport(comic_id=comic_id)
    inputs, skipped = storyboard_scene_inputs(
        {
            "comic_id": str(request.comic_id),
            "scenes": [
                {
                    "sequence_number": 2,
                    "page_id": str(page_id),
                    "panel_id": str(panel_id),
                    "scene_summary": "Ada encontra uma pista",
                    "estimated_duration_seconds": 7,
                    "shot_type": "close_up",
                    "camera_direction": "zoom_in",
                    "transition": "dissolve",
                    "dialogue": [{"speaker": "Ada", "text": "Observe o padrao."}],
                    "pedagogical_goal": "Reconhecer padroes",
                    "ct_pillar_codes": ["pattern_recognition"],
                }
            ],
        },
        start_position=4,
    )
    assert skipped == 0
    assert inputs[0].position == 4
    assert inputs[0].duration_ms == 7000
    assert inputs[0].camera_settings == {"shot_type": "close_up", "movement": "zoom_in"}
    assert "Ada: Observe o padrao." in inputs[0].screenplay_text
    assert inputs[0].source_comic_panel_id == panel_id


def test_storyboard_import_skips_panels_already_on_timeline() -> None:
    panel_id = uuid4()
    inputs, skipped = storyboard_scene_inputs(
        {"scenes": [{"page_id": str(uuid4()), "panel_id": str(panel_id)}]},
        excluded_panel_ids={panel_id},
    )
    assert inputs == []
    assert skipped == 1


def test_media_generation_contract_supports_all_audiovisual_kinds() -> None:
    scene_id = uuid4()
    for kind in ("image", "animation", "voice", "lip_sync", "music", "sfx"):
        request = AnimeMediaGenerationCreate(
            scene_id=scene_id,
            kind=kind,
            prompt="Direcao criativa segura",
            duration_ms=8000,
        )
        assert request.kind == kind


def test_timeline_reorder_rejects_duplicate_scene_ids() -> None:
    scene_id = uuid4()
    with pytest.raises(ValidationError):
        AnimeTimelineReorder(scene_ids=[scene_id, scene_id])


def test_scene_split_requires_two_renderable_segments() -> None:
    split = AnimeSceneSplit(split_at_ms=2500, second_title="Continuação")
    assert split.split_at_ms == 2500
    with pytest.raises(ValidationError):
        AnimeSceneSplit(split_at_ms=200)


def test_media_generation_cost_uses_kind_and_duration() -> None:
    assert estimate_media_generation_cost("image", 30000) == 0.04
    assert estimate_media_generation_cost("voice", 10000) == 0.06
    assert estimate_media_generation_cost("lip_sync", 5000) == 0.06


def test_generated_media_contract_selects_real_file_formats() -> None:
    assert generated_media_contract("image", 5000)["mime_type"] == "image/png"
    assert generated_media_contract("animation", 5000)["media_kind"] == "video"
    assert generated_media_contract("voice", 5000)["suffix"] == ".wav"


@pytest.mark.asyncio
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg not installed")
async def test_internal_provider_generates_valid_image_video_and_audio(tmp_path) -> None:
    outputs = {
        "image": tmp_path / "image.png",
        "animation": tmp_path / "animation.mp4",
        "voice": tmp_path / "voice.wav",
    }
    for kind, output in outputs.items():
        await _run_ffmpeg(kind, 500, output)
        assert output.is_file()
        assert output.stat().st_size > 0


def test_storage_saves_generated_artifact_with_signature_validation(tmp_path) -> None:
    storage = AnimeMediaStorage(tmp_path / "storage", max_size_bytes=1024)
    source = tmp_path / "voice.wav"
    source.write_bytes(b"RIFF" + (8).to_bytes(4, "little") + b"WAVEfmt ")
    saved = storage.save_generated(
        source,
        uuid4(),
        media_kind="audio",
        file_name="voice.wav",
        mime_type="audio/wav",
    )
    assert not source.exists()
    assert storage.resolve(saved.storage_key).is_file()
    assert saved.mime_type == "audio/wav"


def test_render_snapshot_is_versioned_and_references_canonical_assets() -> None:
    project_id = uuid4()
    visual_id = uuid4()
    audio_id = uuid4()
    project = SimpleNamespace(
        id=project_id,
        revision=4,
        title="Padrões no espaço",
        width=1920,
        height=1080,
        fps=24,
        language="pt-BR",
        scenes=[
            SimpleNamespace(
                id=uuid4(),
                position=1,
                title="A descoberta",
                duration_ms=5000,
                visual_asset_file_id=visual_id,
                transition_settings={"type": "fade"},
            )
        ],
        audio_tracks=[
            SimpleNamespace(
                id=uuid4(),
                track_kind="narration",
                asset_file_id=audio_id,
                start_ms=0,
                duration_ms=5000,
                trim_start_ms=0,
                volume=1.0,
                fade_in_ms=100,
                fade_out_ms=100,
                is_muted=False,
            )
        ],
        captions=[],
    )
    data = SimpleNamespace(
        model_dump=lambda **_: {
            "burn_captions": True,
            "caption_language": "pt-BR",
            "quality": "preview",
            "normalize_audio": True,
        }
    )
    snapshot = render_snapshot(project, data)
    assert snapshot["project"]["revision"] == 4
    assert snapshot["scenes"][0]["visual_asset_file_id"] == str(visual_id)
    assert snapshot["audio_tracks"][0]["asset_file_id"] == str(audio_id)


def test_ffmpeg_helpers_create_accessible_timestamps_and_safe_frame() -> None:
    assert _srt_timestamp(3_661_042) == "01:01:01,042"
    video_filter = _scene_filter(1920, 1080, 24)
    assert "force_original_aspect_ratio=decrease" in video_filter
    assert "format=yuv420p" in video_filter


def test_models_register_only_the_new_audiovisual_tables() -> None:
    names = {table.name for table in AnimeProject.metadata.sorted_tables}
    assert {
        "anime_projects",
        "anime_scenes",
        "anime_audio_tracks",
        "anime_caption_cues",
        "anime_renders",
    }.issubset(names)


def test_storage_resolves_only_local_keys_and_deletes_artifacts(tmp_path) -> None:
    storage = AnimeMediaStorage(tmp_path, max_size_bytes=1024)
    storage_key = f"{uuid4()}/anime/media.mp4"
    media_path = storage.resolve(storage_key)
    media_path.parent.mkdir(parents=True)
    media_path.write_bytes(b"render")

    storage.delete(storage_key)
    assert not media_path.exists()
    with pytest.raises(InvalidAnimeMediaError):
        storage.resolve("../outside.mp4")


def test_save_render_uses_cross_filesystem_safe_move(tmp_path, monkeypatch) -> None:
    storage = AnimeMediaStorage(tmp_path / "storage", max_size_bytes=1024)
    source = tmp_path / "temporary-render.mp4"
    source.write_bytes(b"rendered-video")
    moved: list[tuple[object, object]] = []

    def fake_move(source_path, destination_path):
        moved.append((source_path, destination_path))
        destination_path.write_bytes(source_path.read_bytes())
        source_path.unlink()
        return destination_path

    monkeypatch.setattr("app.anime_studio.storage.shutil.move", fake_move)
    saved = storage.save_render(source, uuid4(), file_name="anime-e2e.mp4")

    assert moved
    assert not source.exists()
    assert storage.resolve(saved.storage_key).read_bytes() == b"rendered-video"
    assert saved.file_name == "anime-e2e.mp4"
    assert saved.size_bytes == len(b"rendered-video")
