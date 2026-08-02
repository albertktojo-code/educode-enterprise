from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anime_studio.media_schemas import AnimeMediaUploadRead
from app.anime_studio.models import AnimeProject
from app.anime_studio.services import get_project_publication, require_editor
from app.anime_studio.storage import AnimeMediaStorage, InvalidAnimeMediaError
from app.api.actor_context import ActorContext, get_project_session, resolve_actor_context
from app.core.config import get_settings
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

router = APIRouter(prefix="/anime-studio", tags=["anime-studio-media"])
settings = get_settings()
storage = AnimeMediaStorage(
    settings.institutional_asset_storage_path,
    settings.max_anime_media_size_mb * 1024 * 1024,
)


@router.post("/media", response_model=AnimeMediaUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    media_kind: Literal["image", "video", "audio"] = Form(...),
    title: str = Form(..., min_length=1, max_length=180),
    rights_confirmed: bool = Form(...),
    project_id: UUID | None = Form(default=None),
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> AnimeMediaUploadRead:
    require_editor(actor)
    if not rights_confirmed:
        raise HTTPException(
            status_code=422,
            detail="Confirme os direitos de uso antes de enviar mídia audiovisual",
        )
    if project_id is not None:
        project = await session.scalar(
            select(AnimeProject).where(
                AnimeProject.id == project_id,
                AnimeProject.organization_id == actor.organization_id,
            )
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Produção de anime não encontrada")
    try:
        saved = await storage.save(file, actor.organization_id, media_kind)
    except InvalidAnimeMediaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    duplicate = await session.scalar(
        select(InstitutionalAssetFile)
        .join(InstitutionalAsset)
        .where(
            InstitutionalAsset.organization_id == actor.organization_id,
            InstitutionalAssetFile.checksum_sha256 == saved.checksum_sha256,
        )
    )
    if duplicate is not None:
        storage.delete(saved.storage_key)
        raise HTTPException(status_code=409, detail="Esta mídia já existe na biblioteca")

    asset = InstitutionalAsset(
        organization_id=actor.organization_id,
        asset_type=InstitutionalAssetType.OTHER,
        name=title.strip(),
        description=f"Mídia {media_kind} vinculada ao Estúdio Anime.",
        category="Mídia Anime",
        status=InstitutionalAssetStatus.DRAFT,
        visibility=InstitutionalAssetVisibility.PROJECT_ONLY,
        metadata_json={
            "media_kind": media_kind,
            "anime_project_id": str(project_id) if project_id else None,
        },
        compatibility=["anime", media_kind],
        license_type=InstitutionalLicenseType.AUTHORIZED_USE,
        rights_confirmed=True,
        created_by_user_id=actor.user_id,
    )
    session.add(asset)
    try:
        await session.flush()
    except Exception:
        await session.rollback()
        storage.delete(saved.storage_key)
        raise
    asset_file = InstitutionalAssetFile(
        asset_id=asset.id,
        file_name=saved.file_name,
        mime_type=saved.mime_type,
        storage_key=saved.storage_key,
        checksum_sha256=saved.checksum_sha256,
        size_bytes=saved.size_bytes,
        view_type=f"anime_{media_kind}",
        is_primary=True,
        is_original=True,
    )
    session.add(asset_file)
    session.add(
        InstitutionalAssetVersion(
            asset_id=asset.id,
            version_number=1,
            snapshot_json={
                "media_kind": media_kind,
                "mime_type": saved.mime_type,
                "checksum_sha256": saved.checksum_sha256,
                "anime_project_id": str(project_id) if project_id else None,
            },
            change_description="Upload pelo Estúdio Anime",
            created_by_user_id=actor.user_id,
        )
    )
    session.add(
        InstitutionalAssetAudit(
            organization_id=actor.organization_id,
            asset_id=asset.id,
            actor_user_id=actor.user_id,
            action="anime_media_uploaded",
            details={
                "media_kind": media_kind,
                "project_id": str(project_id) if project_id else None,
                "file_name": saved.file_name,
            },
        )
    )
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        storage.delete(saved.storage_key)
        raise
    await session.refresh(asset_file)
    return AnimeMediaUploadRead(
        asset_id=asset.id,
        file_id=asset_file.id,
        file_name=asset_file.file_name,
        media_kind=media_kind,
        mime_type=asset_file.mime_type,
        size_bytes=asset_file.size_bytes,
        download_path=f"/anime-studio/media/{asset_file.id}",
    )


@router.get("/media/{file_id}")
async def download_media(
    file_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> FileResponse:
    require_editor(actor)
    row = await session.scalar(
        select(InstitutionalAssetFile)
        .join(InstitutionalAsset)
        .where(
            InstitutionalAssetFile.id == file_id,
            InstitutionalAsset.organization_id == actor.organization_id,
            InstitutionalAssetFile.mime_type.like("%/%"),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    return FileResponse(
        storage.resolve(row.storage_key),
        media_type=row.mime_type,
        filename=row.file_name,
        content_disposition_type="inline",
    )


@router.get("/publications/{project_id}/media")
async def stream_publication(
    project_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> FileResponse:
    publication = await get_project_publication(
        session,
        actor=actor,
        project_id=project_id,
    )
    row = await session.scalar(
        select(InstitutionalAssetFile)
        .join(InstitutionalAsset)
        .where(
            InstitutionalAssetFile.id == publication.asset_file_id,
            InstitutionalAsset.organization_id == actor.organization_id,
            InstitutionalAsset.status == InstitutionalAssetStatus.PUBLISHED,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Vídeo publicado não encontrado")
    return FileResponse(
        storage.resolve(row.storage_key),
        media_type=row.mime_type,
        filename=row.file_name,
        content_disposition_type="inline",
    )


@router.get("/publications/{project_id}/media/{file_id}")
async def stream_publication_rendition(
    project_id: UUID,
    file_id: UUID,
    session: AsyncSession = Depends(get_project_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> FileResponse:
    publication = await get_project_publication(
        session,
        actor=actor,
        project_id=project_id,
    )
    allowed_file_ids = {
        publication.asset_file_id,
        *(rendition.asset_file_id for rendition in publication.renditions),
    }
    if file_id not in allowed_file_ids:
        raise HTTPException(status_code=404, detail="Resolução publicada não encontrada")
    row = await session.scalar(
        select(InstitutionalAssetFile)
        .join(InstitutionalAsset)
        .where(
            InstitutionalAssetFile.id == file_id,
            InstitutionalAsset.organization_id == actor.organization_id,
            InstitutionalAsset.status == InstitutionalAssetStatus.PUBLISHED,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Resolução publicada não encontrada")
    return FileResponse(
        storage.resolve(row.storage_key),
        media_type=row.mime_type,
        filename=row.file_name,
        content_disposition_type="inline",
    )
