from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.anime_studio.schemas import (
    AnimeAudioTrackCreate,
    AnimeAudioTrackRead,
    AnimeAudioTrackUpdate,
    AnimeCaptionCreate,
    AnimeCaptionRead,
    AnimeCaptionUpdate,
    AnimeMediaGenerationCreate,
    AnimeMediaGenerationRead,
    AnimeMediaGenerationReview,
    AnimeProjectCreate,
    AnimeProjectRead,
    AnimeProjectSummary,
    AnimeProjectUpdate,
    AnimeRenderCreate,
    AnimeRenderRead,
    AnimeRenderReview,
    AnimeSceneCreate,
    AnimeSceneRead,
    AnimeSceneSplit,
    AnimeSceneSplitRead,
    AnimeSceneUpdate,
    AnimeStoryboardImport,
    AnimeStoryboardImportRead,
    AnimeTimelineReorder,
)
from app.anime_studio.services import (
    archive_project,
    create_audio_track,
    create_caption,
    create_project,
    create_scene,
    delete_audio_track,
    delete_caption,
    delete_scene,
    get_project,
    import_comic_storyboard,
    list_media_generations,
    list_projects,
    reorder_timeline,
    request_media_generation,
    request_render,
    require_editor,
    restore_render_version,
    review_media_generation,
    review_render,
    split_scene,
    update_audio_track,
    update_caption,
    update_project,
    update_scene,
)
from app.api.actor_context import ActorContext, get_project_session, resolve_actor_context

router = APIRouter(prefix="/anime-studio", tags=["anime-studio"])


@router.get("/projects", response_model=list[AnimeProjectSummary])
async def get_projects(
    include_archived: bool = Query(default=False),
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    require_editor(actor)
    return await list_projects(
        session, organization_id=actor.organization_id, include_archived=include_archived
    )


@router.post("/projects", response_model=AnimeProjectRead, status_code=status.HTTP_201_CREATED)
async def post_project(
    data: AnimeProjectCreate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await create_project(session, actor=actor, data=data)


@router.get("/projects/{project_id}", response_model=AnimeProjectRead)
async def get_project_detail(
    project_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    require_editor(actor)
    return await get_project(session, organization_id=actor.organization_id, project_id=project_id)


@router.patch("/projects/{project_id}", response_model=AnimeProjectRead)
async def patch_project(
    project_id: UUID,
    data: AnimeProjectUpdate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await update_project(session, actor=actor, project_id=project_id, data=data)


@router.delete("/projects/{project_id}", response_model=AnimeProjectSummary)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await archive_project(session, actor=actor, project_id=project_id)


@router.post(
    "/projects/{project_id}/scenes",
    response_model=AnimeSceneRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_scene(
    project_id: UUID,
    data: AnimeSceneCreate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await create_scene(session, actor=actor, project_id=project_id, data=data)


@router.put("/projects/{project_id}/timeline", response_model=AnimeProjectRead)
async def put_timeline(
    project_id: UUID,
    data: AnimeTimelineReorder,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await reorder_timeline(session, actor=actor, project_id=project_id, data=data)


@router.post(
    "/projects/{project_id}/scenes/{scene_id}/split",
    response_model=AnimeSceneSplitRead,
)
async def post_scene_split(
    project_id: UUID,
    scene_id: UUID,
    data: AnimeSceneSplit,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    first, second = await split_scene(
        session, actor=actor, project_id=project_id, scene_id=scene_id, data=data
    )
    return {"first": first, "second": second}


@router.post(
    "/projects/{project_id}/storyboard/from-comic",
    response_model=AnimeStoryboardImportRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_storyboard_from_comic(
    project_id: UUID,
    data: AnimeStoryboardImport,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await import_comic_storyboard(session, actor=actor, project_id=project_id, data=data)


@router.get(
    "/projects/{project_id}/media-generations",
    response_model=list[AnimeMediaGenerationRead],
)
async def get_media_generations(
    project_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await list_media_generations(session, actor=actor, project_id=project_id)


@router.post(
    "/projects/{project_id}/media-generations",
    response_model=AnimeMediaGenerationRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_media_generation(
    project_id: UUID,
    data: AnimeMediaGenerationCreate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await request_media_generation(session, actor=actor, project_id=project_id, data=data)


@router.post(
    "/projects/{project_id}/media-generations/{job_id}/review",
    response_model=AnimeMediaGenerationRead,
)
async def post_media_generation_review(
    project_id: UUID,
    job_id: UUID,
    data: AnimeMediaGenerationReview,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await review_media_generation(
        session, actor=actor, project_id=project_id, job_id=job_id, data=data
    )


@router.patch("/projects/{project_id}/scenes/{scene_id}", response_model=AnimeSceneRead)
async def patch_scene(
    project_id: UUID,
    scene_id: UUID,
    data: AnimeSceneUpdate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await update_scene(
        session, actor=actor, project_id=project_id, scene_id=scene_id, data=data
    )


@router.delete("/projects/{project_id}/scenes/{scene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_scene(
    project_id: UUID,
    scene_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    await delete_scene(session, actor=actor, project_id=project_id, scene_id=scene_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/audio-tracks",
    response_model=AnimeAudioTrackRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_audio_track(
    project_id: UUID,
    data: AnimeAudioTrackCreate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await create_audio_track(session, actor=actor, project_id=project_id, data=data)


@router.patch("/projects/{project_id}/audio-tracks/{track_id}", response_model=AnimeAudioTrackRead)
async def patch_audio_track(
    project_id: UUID,
    track_id: UUID,
    data: AnimeAudioTrackUpdate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await update_audio_track(
        session, actor=actor, project_id=project_id, track_id=track_id, data=data
    )


@router.delete(
    "/projects/{project_id}/audio-tracks/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_audio_track(
    project_id: UUID,
    track_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    await delete_audio_track(session, actor=actor, project_id=project_id, track_id=track_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/captions",
    response_model=AnimeCaptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_caption(
    project_id: UUID,
    data: AnimeCaptionCreate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await create_caption(session, actor=actor, project_id=project_id, data=data)


@router.patch("/projects/{project_id}/captions/{cue_id}", response_model=AnimeCaptionRead)
async def patch_caption(
    project_id: UUID,
    cue_id: UUID,
    data: AnimeCaptionUpdate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await update_caption(
        session, actor=actor, project_id=project_id, cue_id=cue_id, data=data
    )


@router.delete("/projects/{project_id}/captions/{cue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_caption(
    project_id: UUID,
    cue_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    await delete_caption(session, actor=actor, project_id=project_id, cue_id=cue_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/projects/{project_id}/renders",
    response_model=AnimeRenderRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_render(
    project_id: UUID,
    data: AnimeRenderCreate,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await request_render(session, actor=actor, project_id=project_id, data=data)


@router.post("/projects/{project_id}/renders/{render_id}/review", response_model=AnimeRenderRead)
async def post_render_review(
    project_id: UUID,
    render_id: UUID,
    data: AnimeRenderReview,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await review_render(
        session,
        actor=actor,
        project_id=project_id,
        render_id=render_id,
        data=data,
    )


@router.post(
    "/projects/{project_id}/renders/{render_id}/restore",
    response_model=AnimeProjectRead,
)
async def post_render_restore(
    project_id: UUID,
    render_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
):
    return await restore_render_version(
        session,
        actor=actor,
        project_id=project_id,
        render_id=render_id,
    )
