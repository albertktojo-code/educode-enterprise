from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.creative import (
    CreativeAsset,
    CreativeBible,
    CreativeItem,
    CreativeItemKind,
    CreativeStatus,
    CreativeVersion,
    CreativeVisibility,
    GenerationProjectCreativeItem,
)
from app.models.pedagogy import GenerationProject
from app.schemas.creative import (
    CreativeAssetRead,
    CreativeBibleInput,
    CreativeBibleRead,
    CreativeCatalogResponse,
    CreativeItemCreate,
    CreativeItemRead,
    CreativeItemUpdate,
    CreativeProjectLinkInput,
    CreativeProjectLinkRead,
)
from app.services.creative.storage import CreativeStorage, InvalidCreativeAssetError

router = APIRouter(prefix="/creative", tags=["Biblioteca Criativa"])
settings = get_settings()
storage = CreativeStorage(
    settings.creative_storage_path,
    settings.max_creative_asset_size_mb * 1024 * 1024,
)

READ_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
    OrganizationRole.MEMBER,
)
WRITE_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)

CHARACTER_ASSET_ROLES = [
    "front_view",
    "side_view",
    "back_view",
    "full_body",
    "face",
    "expression",
    "pose",
    "clothing",
    "accessory",
    "character_sheet",
]
SCENE_ASSET_ROLES = [
    "background",
    "layout",
    "reference_image",
    "map",
    "floorplan",
    "moodboard",
    "scene_sheet",
]
STYLE_ASSET_ROLES = [
    "visual_reference",
    "moodboard",
    "color_palette",
    "typography",
    "sample_page",
    "style_sheet",
]
COGNITIVE_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
EVALUATION_ROLES = ["none", "pretest", "intervention", "posttest", "follow_up"]


def organization_id(membership: Membership) -> UUID:
    return membership.organization_id


def can_manage(item: CreativeItem, membership: Membership) -> bool:
    return membership.role in ADMIN_ROLES or item.created_by_user_id == membership.user_id


async def get_item(
    creative_item_id: UUID,
    membership: Membership,
    session: AsyncSession,
    *,
    require_write: bool = False,
) -> CreativeItem:
    item = await session.scalar(
        select(CreativeItem)
        .where(
            CreativeItem.id == creative_item_id,
            CreativeItem.organization_id == organization_id(membership),
        )
        .options(
            selectinload(CreativeItem.assets),
            selectinload(CreativeItem.versions),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item criativo não encontrado")
    if require_write and not can_manage(item, membership):
        raise HTTPException(
            status_code=403, detail="Apenas o autor ou um administrador pode alterar"
        )
    if (
        not require_write
        and item.visibility == CreativeVisibility.PRIVATE
        and not can_manage(item, membership)
    ):
        raise HTTPException(status_code=404, detail="Item criativo não encontrado")
    return item


def profile_snapshot(item: CreativeItem) -> dict[str, object]:
    return {
        "kind": item.kind.value,
        "name": item.name,
        "description": item.description,
        "canonical_prompt": item.canonical_prompt,
        "negative_prompt": item.negative_prompt,
        "profile_data": item.profile_data,
        "visibility": item.visibility.value,
        "status": item.status.value,
        "rights_confirmed": item.rights_confirmed,
        "original_author": item.original_author,
        "license_notes": item.license_notes,
    }


async def add_version(
    item: CreativeItem,
    user_id: UUID,
    session: AsyncSession,
    change_description: str | None,
) -> None:
    maximum = await session.scalar(
        select(func.max(CreativeVersion.version_number)).where(
            CreativeVersion.creative_item_id == item.id
        )
    )
    session.add(
        CreativeVersion(
            creative_item_id=item.id,
            version_number=(maximum or 0) + 1,
            profile_snapshot=profile_snapshot(item),
            change_description=change_description,
            created_by_user_id=user_id,
        )
    )


async def validate_generation_project(
    generation_project_id: UUID,
    membership: Membership,
    session: AsyncSession,
    *,
    require_write: bool = True,
) -> GenerationProject:
    project = await session.scalar(
        select(GenerationProject).where(
            GenerationProject.id == generation_project_id,
            GenerationProject.organization_id == organization_id(membership),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto de geração não encontrado")
    if require_write and membership.role not in ADMIN_ROLES:
        if project.created_by_user_id != membership.user_id:
            raise HTTPException(
                status_code=403,
                detail="Apenas o autor ou um administrador pode alterar este projeto",
            )
    return project


@router.get("/catalog", response_model=CreativeCatalogResponse)
async def creative_catalog(
    _: Membership = Depends(require_roles(*READ_ROLES)),
) -> CreativeCatalogResponse:
    return CreativeCatalogResponse(
        kinds=[item.value for item in CreativeItemKind],
        character_asset_roles=CHARACTER_ASSET_ROLES,
        scene_asset_roles=SCENE_ASSET_ROLES,
        style_asset_roles=STYLE_ASSET_ROLES,
        cognitive_levels=COGNITIVE_LEVELS,
        evaluation_roles=EVALUATION_ROLES,
    )


@router.get("/items", response_model=list[CreativeItemRead])
async def list_items(
    kind: CreativeItemKind | None = None,
    status: CreativeStatus | None = None,
    q: str | None = Query(default=None, max_length=120),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[CreativeItemRead]:
    conditions = [CreativeItem.organization_id == organization_id(membership)]
    if membership.role not in ADMIN_ROLES:
        conditions.append(
            or_(
                CreativeItem.visibility != CreativeVisibility.PRIVATE,
                CreativeItem.created_by_user_id == membership.user_id,
            )
        )
    if kind is not None:
        conditions.append(CreativeItem.kind == kind)
    if status is not None:
        conditions.append(CreativeItem.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        conditions.append(
            or_(CreativeItem.name.ilike(pattern), CreativeItem.description.ilike(pattern))
        )

    items = list(
        (
            await session.scalars(
                select(CreativeItem)
                .where(*conditions)
                .options(
                    selectinload(CreativeItem.assets),
                    selectinload(CreativeItem.versions),
                )
                .order_by(CreativeItem.kind, CreativeItem.name)
            )
        ).all()
    )
    return [CreativeItemRead.model_validate(item) for item in items]


@router.post("/items", response_model=CreativeItemRead, status_code=201)
async def create_item(
    data: CreativeItemCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> CreativeItemRead:
    duplicate = await session.scalar(
        select(CreativeItem.id).where(
            CreativeItem.organization_id == organization_id(membership),
            CreativeItem.kind == data.kind,
            func.lower(CreativeItem.name) == data.name.strip().lower(),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Já existe um item desse tipo com o mesmo nome")

    item = CreativeItem(
        organization_id=organization_id(membership),
        created_by_user_id=user.id,
        created_by_name_snapshot=user.full_name,
        **data.model_dump(),
    )
    session.add(item)
    await session.flush()
    await add_version(item, user.id, session, "Versão inicial")
    await session.commit()
    return CreativeItemRead.model_validate(await get_item(item.id, membership, session))


@router.get("/items/{creative_item_id}", response_model=CreativeItemRead)
async def read_item(
    creative_item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> CreativeItemRead:
    return CreativeItemRead.model_validate(await get_item(creative_item_id, membership, session))


@router.patch("/items/{creative_item_id}", response_model=CreativeItemRead)
async def update_item(
    creative_item_id: UUID,
    data: CreativeItemUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> CreativeItemRead:
    item = await get_item(creative_item_id, membership, session, require_write=True)
    values = data.model_dump(exclude_unset=True, exclude={"change_description"})
    for field, value in values.items():
        setattr(item, field, value)
    await session.flush()
    await add_version(item, user.id, session, data.change_description or "Perfil atualizado")
    await session.commit()
    return CreativeItemRead.model_validate(await get_item(item.id, membership, session))


@router.delete("/items/{creative_item_id}", status_code=204)
async def delete_item(
    creative_item_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    item = await get_item(creative_item_id, membership, session, require_write=True)
    used = await session.scalar(
        select(GenerationProjectCreativeItem.id).where(
            GenerationProjectCreativeItem.creative_item_id == item.id
        )
    )
    if used is not None:
        raise HTTPException(
            status_code=409,
            detail="O item está vinculado a um projeto. Arquive-o ou remova o vínculo primeiro.",
        )
    keys = [asset.storage_key for asset in item.assets]
    await session.delete(item)
    await session.commit()
    for storage_key in keys:
        storage.delete(storage_key)
    return Response(status_code=204)


@router.post("/items/{creative_item_id}/assets", response_model=CreativeAssetRead, status_code=201)
async def upload_asset(
    creative_item_id: UUID,
    file: UploadFile = File(...),
    asset_role: str = Form(default="reference"),
    pdf_page_number: int | None = Form(default=None),
    is_primary: bool = Form(default=False),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> CreativeAssetRead:
    item = await get_item(creative_item_id, membership, session, require_write=True)
    try:
        stored = await storage.save(file, organization_id(membership))
    except InvalidCreativeAssetError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if is_primary:
        for asset in item.assets:
            asset.is_primary = False

    asset = CreativeAsset(
        creative_item_id=item.id,
        file_name=file.filename or Path(stored.storage_key).name,
        mime_type=stored.mime_type,
        storage_key=stored.storage_key,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        asset_role=asset_role.strip() or "reference",
        pdf_page_number=pdf_page_number,
        is_primary=is_primary,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return CreativeAssetRead.model_validate(asset)


@router.get("/assets/{asset_id}/download")
async def download_asset(
    asset_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> FileResponse:
    asset = await session.scalar(
        select(CreativeAsset)
        .join(CreativeItem, CreativeItem.id == CreativeAsset.creative_item_id)
        .where(
            CreativeAsset.id == asset_id,
            CreativeItem.organization_id == organization_id(membership),
        )
        .options(selectinload(CreativeAsset.creative_item))
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Arquivo criativo não encontrado")
    item = asset.creative_item
    if item.visibility == CreativeVisibility.PRIVATE and not can_manage(item, membership):
        raise HTTPException(status_code=404, detail="Arquivo criativo não encontrado")
    path = storage.resolve(asset.storage_key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo físico não encontrado")
    return FileResponse(path, media_type=asset.mime_type, filename=asset.file_name)


@router.delete("/assets/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    asset = await session.scalar(
        select(CreativeAsset)
        .where(CreativeAsset.id == asset_id)
        .options(selectinload(CreativeAsset.creative_item))
    )
    if asset is None or asset.creative_item.organization_id != organization_id(membership):
        raise HTTPException(status_code=404, detail="Arquivo criativo não encontrado")
    if not can_manage(asset.creative_item, membership):
        raise HTTPException(status_code=403, detail="Permissão insuficiente")
    storage_key = asset.storage_key
    await session.delete(asset)
    await session.commit()
    storage.delete(storage_key)
    return Response(status_code=204)


@router.get(
    "/generation-projects/{generation_project_id}/items",
    response_model=list[CreativeProjectLinkRead],
)
async def list_project_items(
    generation_project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[CreativeProjectLinkRead]:
    await validate_generation_project(
        generation_project_id, membership, session, require_write=False
    )
    links = list(
        (
            await session.scalars(
                select(GenerationProjectCreativeItem)
                .where(GenerationProjectCreativeItem.generation_project_id == generation_project_id)
                .options(selectinload(GenerationProjectCreativeItem.creative_item))
                .order_by(GenerationProjectCreativeItem.position)
            )
        ).all()
    )
    return [
        CreativeProjectLinkRead(
            id=link.id,
            creative_item_id=link.creative_item_id,
            creative_version_id=link.creative_version_id,
            narrative_role=link.narrative_role,
            position=link.position,
            is_primary=link.is_primary,
            name=link.creative_item.name,
            kind=link.creative_item.kind,
        )
        for link in links
    ]


@router.put(
    "/generation-projects/{generation_project_id}/items",
    response_model=list[CreativeProjectLinkRead],
)
async def replace_project_items(
    generation_project_id: UUID,
    data: list[CreativeProjectLinkInput],
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> list[CreativeProjectLinkRead]:
    await validate_generation_project(generation_project_id, membership, session)
    creative_ids = [item.creative_item_id for item in data]
    if len(creative_ids) != len(set(creative_ids)):
        raise HTTPException(status_code=422, detail="Não repita itens criativos no mesmo projeto")
    if creative_ids:
        found = set(
            (
                await session.scalars(
                    select(CreativeItem.id).where(
                        CreativeItem.id.in_(creative_ids),
                        CreativeItem.organization_id == organization_id(membership),
                        CreativeItem.status != CreativeStatus.ARCHIVED,
                    )
                )
            ).all()
        )
        if found != set(creative_ids):
            raise HTTPException(status_code=422, detail="Um ou mais itens criativos são inválidos")

    await session.execute(
        delete(GenerationProjectCreativeItem).where(
            GenerationProjectCreativeItem.generation_project_id == generation_project_id
        )
    )
    for entry in data:
        session.add(
            GenerationProjectCreativeItem(
                generation_project_id=generation_project_id,
                **entry.model_dump(),
            )
        )
    await session.commit()
    return await list_project_items(generation_project_id, session, membership)


@router.get(
    "/generation-projects/{generation_project_id}/bible",
    response_model=CreativeBibleRead | None,
)
async def read_creative_bible(
    generation_project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> CreativeBibleRead | None:
    await validate_generation_project(
        generation_project_id, membership, session, require_write=False
    )
    bible = await session.scalar(
        select(CreativeBible).where(CreativeBible.generation_project_id == generation_project_id)
    )
    return CreativeBibleRead.model_validate(bible) if bible else None


@router.put(
    "/generation-projects/{generation_project_id}/bible",
    response_model=CreativeBibleRead,
)
async def upsert_creative_bible(
    generation_project_id: UUID,
    data: CreativeBibleInput,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> CreativeBibleRead:
    await validate_generation_project(generation_project_id, membership, session)
    bible = await session.scalar(
        select(CreativeBible).where(CreativeBible.generation_project_id == generation_project_id)
    )
    if bible is None:
        bible = CreativeBible(
            generation_project_id=generation_project_id,
            updated_by_user_id=user.id,
            **data.model_dump(),
        )
        session.add(bible)
    else:
        for field, value in data.model_dump().items():
            setattr(bible, field, value)
        bible.updated_by_user_id = user.id
    await session.commit()
    await session.refresh(bible)
    return CreativeBibleRead.model_validate(bible)
