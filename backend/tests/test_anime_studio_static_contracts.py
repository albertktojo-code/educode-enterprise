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
