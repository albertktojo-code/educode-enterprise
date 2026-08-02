from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_anime_migration_follows_installed_head_and_has_rollback() -> None:
    source = (BACKEND / "alembic/versions/0056_anime_audiovisual.py").read_text(encoding="utf-8")
    assert 'down_revision: str | None = "0055_delivery_source_invariant"' in source
    assert "def downgrade()" in source
    for table in (
        "anime_projects",
        "anime_scenes",
        "anime_audio_tracks",
        "anime_caption_cues",
        "anime_renders",
    ):
        assert f'"{table}"' in source


def test_anime_reuses_canonical_assets_jobs_and_audit() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    rendering = (BACKEND / "app/anime_studio/rendering.py").read_text(encoding="utf-8")
    assert "InstitutionalAssetFile" in services
    assert 'job_type="anime_render"' in services
    assert "append_domain_audit" in services
    assert "InstitutionalAsset(" in rendering
    assert "review_required" in rendering


def test_rendering_uses_ffmpeg_without_shell_commands() -> None:
    source = (BACKEND / "app/anime_studio/rendering.py").read_text(encoding="utf-8")
    assert "asyncio.create_subprocess_exec" in source
    assert "create_subprocess_shell" not in source
    assert '"libx264"' in source
    assert '"aac"' in source


def test_frontend_has_accessible_responsive_studio() -> None:
    root = BACKEND.parent / "frontend/src/features/animeStudio"
    page = (root / "AnimeStudioPage.tsx").read_text(encoding="utf-8")
    styles = (root / "styles.css").read_text(encoding="utf-8")
    assert "aria-live" in page
    assert 'role="dialog"' in page
    assert "prefers-reduced-motion" in styles
    assert "pointer: coarse" in styles


def test_anime_is_registered_across_api_worker_and_frontend() -> None:
    project_root = BACKEND.parent
    api_router = (BACKEND / "app/api/v1/router.py").read_text(encoding="utf-8")
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    operations = (BACKEND / "app/services/operations.py").read_text(encoding="utf-8")
    worker = (BACKEND / "app/workers/main.py").read_text(encoding="utf-8")
    config = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")
    dockerfile = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    route_registry = (
        project_root / "frontend/src/features/consolidation/routeRegistry.tsx"
    ).read_text(encoding="utf-8")
    layout = (project_root / "frontend/src/components/AppLayout.tsx").read_text(encoding="utf-8")

    assert "api_router.include_router(anime_studio_router)" in api_router
    assert "api_router.include_router(anime_media_router)" in api_router
    assert "anime_studio_models" in registry
    assert '"anime_render"' in operations
    assert "render_anime_job(job, progress)" in worker
    assert "max_anime_media_size_mb" in config
    assert "ffmpeg" in dockerfile
    assert "...normalize(animeStudioRoutes)" in route_registry
    assert 'to: "/anime-studio"' in layout


def test_render_uses_immutable_snapshot_and_tenant_scoped_links() -> None:
    rendering = (BACKEND / "app/anime_studio/rendering.py").read_text(encoding="utf-8")
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")

    assert "ordered_scenes = sorted(scenes_snapshot" in rendering
    assert "for track in audio_tracks_snapshot" in rendering
    assert "sorted(captions_snapshot" in rendering
    assert "InstitutionalAssetVersion(" in rendering
    assert "_validate_project_links" in services
    assert "_validate_comic_sources" in services
    assert "model.organization_id == organization_id" in services
    assert "GeneratedComic.organization_id == organization_id" in services
    assert router.count("require_editor(actor)") >= 2


def test_storyboard_reuses_hq_preview_and_canonical_anime_scenes() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    assert "build_storyboard(comic)" in services
    assert "load_comic(" in services
    assert 'action="anime.storyboard.imported"' in services
    assert '"/projects/{project_id}/storyboard/from-comic"' in router


def test_media_generation_reuses_jobs_quotas_and_human_review() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    assert 'job_type="media_generation"' in services
    assert "estimated_cost=estimated_cost" in services
    assert 'action="anime.media_generation.queued"' in services
    assert "require_reviewer(actor)" in services
    assert '"/projects/{project_id}/media-generations"' in router


def test_anime_media_worker_creates_canonical_reviewable_artifacts() -> None:
    generation = (BACKEND / "app/anime_studio/generation.py").read_text(encoding="utf-8")
    worker = (BACKEND / "app/workers/main.py").read_text(encoding="utf-8")
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    assert "asyncio.create_subprocess_exec" in generation
    assert "InstitutionalAssetFile(" in generation
    assert "InstitutionalAssetStatus.IN_REVIEW" in generation
    assert "generate_anime_media_job(job, progress)" in worker
    assert "scene.visual_asset_file_id = asset_file.id" in services
    assert "AnimeAudioTrack(" in services


def test_audio_mixer_reuses_canonical_tracks_assets_and_tenant_scope() -> None:
    schemas = (BACKEND / "app/anime_studio/schemas.py").read_text(encoding="utf-8")
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    assert "class AnimeAudioTrackUpdate" in schemas
    for field in ("trim_start_ms", "volume", "fade_in_ms", "fade_out_ms", "is_muted"):
        assert field in schemas
    assert "_validate_asset_file" in services
    assert "model.organization_id == organization_id" in services
    assert '"/projects/{project_id}/audio-tracks/{track_id}"' in router


def test_caption_editor_validates_overlap_and_reuses_canonical_cues() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    schemas = (BACKEND / "app/anime_studio/schemas.py").read_text(encoding="utf-8")

    assert "class AnimeCaptionUpdate" in schemas
    assert "_ensure_caption_window_available" in services
    assert "AnimeCaptionCue.start_ms < end_ms" in services
    assert "AnimeCaptionCue.end_ms > start_ms" in services
    assert "AnimeCaptionCue.organization_id == project.organization_id" in services
    assert '"/projects/{project_id}/captions/{cue_id}"' in router


def test_render_versions_reuse_snapshots_jobs_and_human_approval() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    operations = (BACKEND / "app/api/v1/routes_operations.py").read_text(
        encoding="utf-8"
    )

    assert "source_snapshot=snapshot" in services
    assert "async def restore_render_version" in services
    assert 'render.status != "approved"' in services
    assert '"active_render_id": str(render.id)' in services
    assert 'action="anime.render.version_restored"' in services
    assert "AnimeRender.organization_id == actor.organization_id" in services
    assert '"/projects/{project_id}/renders/{render_id}/restore"' in router
    assert '@router.post("/jobs/{job_id}/retry"' in operations


def test_publication_reuses_approved_render_assets_and_classrooms() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    media_router = (BACKEND / "app/anime_studio/media_router.py").read_text(
        encoding="utf-8"
    )

    assert 'render.status != "approved"' in services
    assert '"publication": manifest' in services
    assert "Classroom.organization_id == actor.organization_id" in services
    assert "ClassroomEnrollment.user_id == actor.user_id" in services
    assert "InstitutionalAssetStatus.PUBLISHED" in services
    assert 'action="anime.project.published"' in services
    assert '"/projects/{project_id}/publish"' in router
    assert '"/publications/{project_id}"' in router
    assert '"/publications/{project_id}/media"' in media_router


def test_student_anime_library_is_class_scoped_and_accessible() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")

    assert "async def list_project_publications" in services
    assert "allowed_classrooms.intersection" in services
    assert "ClassroomEnrollment.user_id == actor.user_id" in services
    assert "def transcript_as_webvtt" in services
    assert "async def get_publication_caption_cues" in services
    assert '"/publications"' in router
    assert '"/publications/{project_id}/transcript"' in router
    assert '"/publications/{project_id}/captions.vtt"' in router


def test_anime_renditions_reuse_asset_variants_and_protected_streaming() -> None:
    rendering = (BACKEND / "app/anime_studio/rendering.py").read_text(encoding="utf-8")
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    media_router = (BACKEND / "app/anime_studio/media_router.py").read_text(
        encoding="utf-8"
    )

    assert "def rendition_profiles" in rendering
    assert "async def _transcode_rendition" in rendering
    assert "InstitutionalAssetVariant(" in rendering
    assert 'variant_type="video_resolution"' in rendering
    assert '"rendition_file_ids"' in rendering
    assert "AnimePublicationRendition(" in services
    assert 'view_type.like("anime_render%")' in services
    assert '"/publications/{project_id}/media/{file_id}"' in media_router
    assert "file_id not in allowed_file_ids" in media_router


def test_timeline_editor_reuses_canonical_scene_crud_and_audit() -> None:
    services = (BACKEND / "app/anime_studio/services.py").read_text(encoding="utf-8")
    router = (BACKEND / "app/anime_studio/router.py").read_text(encoding="utf-8")
    assert 'action="anime.timeline.reordered"' in services
    assert 'action="anime.scene.split"' in services
    assert "split_from_scene_id" in services
    assert '"/projects/{project_id}/timeline"' in router
    assert '"/projects/{project_id}/scenes/{scene_id}/split"' in router
