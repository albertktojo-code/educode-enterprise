from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_roles
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.assets import (
    AssetCollection,
    AssetCollectionItem,
    InstitutionalAsset,
    InstitutionalAssetAudit,
    InstitutionalAssetFile,
    InstitutionalAssetStatus,
    InstitutionalAssetTag,
    InstitutionalAssetType,
    InstitutionalAssetVariant,
    InstitutionalAssetVersion,
    InstitutionalAssetVisibility,
    InstitutionalLicenseType,
)
from app.models.auth import Membership, OrganizationRole, User
from app.models.comic import GeneratedComic
from app.models.creative import CreativeItem, CreativeItemKind, CreativeStatus, CreativeVisibility, CreativeVersion
from app.schemas.assets import (
    AssetCatalogResponse,
    AssetFileRead,
    AssetCollectionCreate,
    AssetCollectionRead,
    AssetStatusRequest,
    AssetVariantInput,
    AssetVariantRead,
    GeneratedCharacterSaveRequest,
    GeneratedCharacterSaveResponse,
    InstitutionalAssetCreate,
    InstitutionalAssetRead,
    InstitutionalAssetUpdate,
)
from app.services.assets.storage import InstitutionalAssetStorage, InvalidCreativeAssetError

router = APIRouter(tags=["Biblioteca institucional"])
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)
TEACHER_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.TEACHER)
settings = get_settings()
storage = InstitutionalAssetStorage(settings.institutional_asset_storage_path, settings.max_institutional_asset_size_mb * 1024 * 1024)


def oid(m: Membership) -> UUID:
    return m.organization_id


async def load_asset(session: AsyncSession, organization_id: UUID, asset_id: UUID) -> InstitutionalAsset | None:
    return await session.scalar(select(InstitutionalAsset).where(InstitutionalAsset.id == asset_id, InstitutionalAsset.organization_id == organization_id).options(selectinload(InstitutionalAsset.files), selectinload(InstitutionalAsset.variants), selectinload(InstitutionalAsset.versions), selectinload(InstitutionalAsset.tags)))


def render(asset: InstitutionalAsset) -> InstitutionalAssetRead:
    return InstitutionalAssetRead(
        id=asset.id, organization_id=asset.organization_id, asset_type=asset.asset_type,
        name=asset.name, description=asset.description, category=asset.category,
        subcategory=asset.subcategory, status=asset.status, visibility=asset.visibility,
        current_version=asset.current_version, metadata_json=asset.metadata_json,
        compatibility=asset.compatibility, age_groups=asset.age_groups,
        subject_codes=asset.subject_codes, canonical_prompt=asset.canonical_prompt,
        negative_prompt=asset.negative_prompt, immutable_traits=asset.immutable_traits,
        license_type=asset.license_type, original_author=asset.original_author,
        attribution_text=asset.attribution_text, usage_restrictions=asset.usage_restrictions,
        rights_confirmed=asset.rights_confirmed, is_real_person=asset.is_real_person,
        source_comic_id=asset.source_comic_id, source_page_id=asset.source_page_id,
        source_panel_id=asset.source_panel_id, created_by_user_id=asset.created_by_user_id,
        approved_by_user_id=asset.approved_by_user_id, published_at=asset.published_at,
        created_at=asset.created_at, updated_at=asset.updated_at,
        files=[AssetFileRead.model_validate(item) for item in asset.files],
        variants=[AssetVariantRead.model_validate(item) for item in asset.variants],
        tags=[tag.tag for tag in asset.tags],
    )


async def audit(session: AsyncSession, membership: Membership, user: User, action: str, asset_id: UUID | None, **details: object) -> None:
    session.add(InstitutionalAssetAudit(organization_id=oid(membership), asset_id=asset_id, actor_user_id=user.id, action=action, details=details))


@router.get("/admin/assets/catalog", response_model=AssetCatalogResponse)
async def catalog(_: Membership = Depends(require_roles(*ADMIN_ROLES))) -> AssetCatalogResponse:
    return AssetCatalogResponse(types=[x.value for x in InstitutionalAssetType], statuses=[x.value for x in InstitutionalAssetStatus], visibilities=[x.value for x in InstitutionalAssetVisibility], license_types=[x.value for x in InstitutionalLicenseType], compatibility_options=["hq", "anime", "storyboard", "quiz", "game", "presentation", "print", "video"])


@router.get("/admin/assets", response_model=list[InstitutionalAssetRead])
async def list_admin_assets(q: str = "", asset_type: InstitutionalAssetType | None = None, status: InstitutionalAssetStatus | None = None, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))) -> list[InstitutionalAssetRead]:
    stmt = select(InstitutionalAsset).where(InstitutionalAsset.organization_id == oid(membership)).options(selectinload(InstitutionalAsset.files), selectinload(InstitutionalAsset.variants), selectinload(InstitutionalAsset.versions), selectinload(InstitutionalAsset.tags)).order_by(InstitutionalAsset.updated_at.desc())
    if asset_type: stmt = stmt.where(InstitutionalAsset.asset_type == asset_type)
    if status: stmt = stmt.where(InstitutionalAsset.status == status)
    if q: stmt = stmt.where(or_(InstitutionalAsset.name.ilike(f"%{q}%"), InstitutionalAsset.description.ilike(f"%{q}%"), InstitutionalAsset.category.ilike(f"%{q}%")))
    return [render(a) for a in (await session.scalars(stmt)).unique().all()]


@router.post("/admin/assets", response_model=InstitutionalAssetRead, status_code=201)
async def create_asset(data: InstitutionalAssetCreate, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)) -> InstitutionalAssetRead:
    if not data.rights_confirmed:
        raise HTTPException(422, "Confirme os direitos de uso antes de cadastrar o elemento")
    asset = InstitutionalAsset(organization_id=oid(membership), created_by_user_id=user.id, **data.model_dump(exclude={"tags"}))
    asset.tags = [InstitutionalAssetTag(tag=t.strip().lower()) for t in sorted(set(data.tags)) if t.strip()]
    session.add(asset); await session.flush()
    asset.versions.append(InstitutionalAssetVersion(version_number=1, snapshot_json=data.model_dump(mode="json"), change_description="Cadastro inicial", created_by_user_id=user.id))
    await audit(session, membership, user, "asset_created", asset.id, name=asset.name)
    await session.commit()
    return render((await load_asset(session, oid(membership), asset.id)) or asset)


@router.patch("/admin/assets/{asset_id}", response_model=InstitutionalAssetRead)
async def update_asset(asset_id: UUID, data: InstitutionalAssetUpdate, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)) -> InstitutionalAssetRead:
    asset = await load_asset(session, oid(membership), asset_id)
    if not asset: raise HTTPException(404, "Elemento não encontrado")
    values=data.model_dump(mode="json", exclude_unset=True, exclude={"tags", "change_description"})
    for key,value in values.items(): setattr(asset,key,value)
    if data.tags is not None:
        await session.execute(delete(InstitutionalAssetTag).where(InstitutionalAssetTag.asset_id == asset.id))
        asset.tags=[InstitutionalAssetTag(tag=t.strip().lower()) for t in sorted(set(data.tags)) if t.strip()]
    asset.current_version += 1
    asset.versions.append(InstitutionalAssetVersion(version_number=asset.current_version, snapshot_json={**values, "tags": data.tags or [t.tag for t in asset.tags]}, change_description=data.change_description, created_by_user_id=user.id))
    await audit(session, membership, user, "asset_updated", asset.id, version=asset.current_version)
    await session.commit()
    return render((await load_asset(session, oid(membership), asset.id)) or asset)


@router.post("/admin/assets/{asset_id}/status", response_model=InstitutionalAssetRead)
async def set_status(asset_id: UUID, data: AssetStatusRequest, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)) -> InstitutionalAssetRead:
    asset=await load_asset(session,oid(membership),asset_id)
    if not asset: raise HTTPException(404,"Elemento não encontrado")
    if data.status in {InstitutionalAssetStatus.APPROVED, InstitutionalAssetStatus.PUBLISHED} and not asset.rights_confirmed:
        raise HTTPException(422,"Não é possível aprovar ou publicar sem direitos confirmados")
    asset.status=data.status
    if data.status in {InstitutionalAssetStatus.APPROVED, InstitutionalAssetStatus.PUBLISHED}: asset.approved_by_user_id=user.id
    if data.status == InstitutionalAssetStatus.PUBLISHED: asset.published_at=datetime.now(UTC)
    await audit(session,membership,user,"asset_status_changed",asset.id,status=data.status.value,notes=data.notes)
    await session.commit()
    return render((await load_asset(session,oid(membership),asset.id)) or asset)


@router.post("/admin/assets/{asset_id}/files", response_model=InstitutionalAssetRead)
async def upload_asset_file(asset_id: UUID, file: UploadFile = File(...), view_type: str = Form("reference"), is_primary: bool = Form(False), variant_id: UUID | None = Form(None), session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)) -> InstitutionalAssetRead:
    asset=await load_asset(session,oid(membership),asset_id)
    if not asset: raise HTTPException(404,"Elemento não encontrado")
    try: saved=await storage.save(file,oid(membership))
    except InvalidCreativeAssetError as exc: raise HTTPException(422,str(exc)) from exc
    duplicate=await session.scalar(select(InstitutionalAssetFile).join(InstitutionalAsset).where(InstitutionalAsset.organization_id==oid(membership),InstitutionalAssetFile.checksum_sha256==saved.checksum_sha256))
    if duplicate:
        storage.delete(saved.storage_key)
        raise HTTPException(409,"Este arquivo já existe na biblioteca institucional")
    if is_primary:
        for existing in asset.files: existing.is_primary=False
    asset.files.append(InstitutionalAssetFile(variant_id=variant_id,file_name=file.filename or "asset",mime_type=saved.mime_type,storage_key=saved.storage_key,checksum_sha256=saved.checksum_sha256,size_bytes=saved.size_bytes,view_type=view_type,is_primary=is_primary))
    await audit(session,membership,user,"asset_file_uploaded",asset.id,file_name=file.filename)
    await session.commit()
    return render((await load_asset(session,oid(membership),asset.id)) or asset)


@router.post("/admin/assets/{asset_id}/variants", response_model=AssetVariantRead, status_code=201)
async def create_variant(asset_id: UUID, data: AssetVariantInput, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES)), user: User = Depends(get_current_user)) -> AssetVariantRead:
    asset=await load_asset(session,oid(membership),asset_id)
    if not asset: raise HTTPException(404,"Elemento não encontrado")
    if data.is_default:
        for v in asset.variants: v.is_default=False
    variant=InstitutionalAssetVariant(asset_id=asset.id,**data.model_dump()); session.add(variant)
    await audit(session,membership,user,"asset_variant_created",asset.id,name=variant.name)
    await session.commit(); await session.refresh(variant)
    return AssetVariantRead.model_validate(variant)


@router.get("/admin/asset-collections", response_model=list[AssetCollectionRead])
async def list_collections(session: AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ADMIN_ROLES))) -> list[AssetCollectionRead]:
    rows=(await session.scalars(select(AssetCollection).where(AssetCollection.organization_id==oid(membership)).options(selectinload(AssetCollection.items)).order_by(AssetCollection.name))).all()
    return [AssetCollectionRead(id=c.id,organization_id=c.organization_id,name=c.name,description=c.description,is_kit=c.is_kit,metadata_json=c.metadata_json,asset_ids=[i.asset_id for i in c.items],created_at=c.created_at) for c in rows]


@router.post("/admin/asset-collections", response_model=AssetCollectionRead, status_code=201)
async def create_collection(data:AssetCollectionCreate,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*ADMIN_ROLES)),user:User=Depends(get_current_user))->AssetCollectionRead:
    collection=AssetCollection(organization_id=oid(membership),name=data.name,description=data.description,is_kit=data.is_kit,metadata_json=data.metadata_json,created_by_user_id=user.id)
    collection.items=[AssetCollectionItem(asset_id=a,position=i) for i,a in enumerate(data.asset_ids)]
    session.add(collection); await session.commit(); await session.refresh(collection)
    return AssetCollectionRead(id=collection.id,organization_id=collection.organization_id,name=collection.name,description=collection.description,is_kit=collection.is_kit,metadata_json=collection.metadata_json,asset_ids=data.asset_ids,created_at=collection.created_at)


@router.get("/admin/assets/files/{file_id}")
async def download_admin_asset_file(file_id: UUID, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*ADMIN_ROLES))) -> FileResponse:
    row = await session.scalar(select(InstitutionalAssetFile).join(InstitutionalAsset).where(InstitutionalAssetFile.id == file_id, InstitutionalAsset.organization_id == oid(membership)))
    if not row: raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(storage.resolve(row.storage_key), media_type=row.mime_type, filename=row.file_name)


@router.get("/creative-assets/files/{file_id}")
async def download_published_asset_file(file_id: UUID, session: AsyncSession = Depends(get_db_session), membership: Membership = Depends(require_roles(*TEACHER_ROLES))) -> FileResponse:
    row = await session.scalar(select(InstitutionalAssetFile).join(InstitutionalAsset).where(InstitutionalAssetFile.id == file_id, InstitutionalAsset.organization_id == oid(membership), InstitutionalAsset.status == InstitutionalAssetStatus.PUBLISHED))
    if not row: raise HTTPException(404, "Arquivo não encontrado")
    return FileResponse(storage.resolve(row.storage_key), media_type=row.mime_type, filename=row.file_name)


@router.get("/creative-assets", response_model=list[InstitutionalAssetRead])
async def teacher_catalog(asset_type:InstitutionalAssetType|None=None,q:str="",session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*TEACHER_ROLES)))->list[InstitutionalAssetRead]:
    stmt=select(InstitutionalAsset).where(InstitutionalAsset.organization_id==oid(membership),InstitutionalAsset.status==InstitutionalAssetStatus.PUBLISHED).options(selectinload(InstitutionalAsset.files),selectinload(InstitutionalAsset.variants),selectinload(InstitutionalAsset.tags))
    if asset_type: stmt=stmt.where(InstitutionalAsset.asset_type==asset_type)
    if q: stmt=stmt.where(or_(InstitutionalAsset.name.ilike(f"%{q}%"),InstitutionalAsset.category.ilike(f"%{q}%")))
    return [render(a) for a in (await session.scalars(stmt.order_by(InstitutionalAsset.name))).unique().all()]


@router.post("/comics/{comic_id}/characters/save",response_model=GeneratedCharacterSaveResponse,status_code=201)
async def save_generated_character(comic_id:UUID,data:GeneratedCharacterSaveRequest,session:AsyncSession=Depends(get_db_session),membership:Membership=Depends(require_roles(*TEACHER_ROLES)),user:User=Depends(get_current_user))->GeneratedCharacterSaveResponse:
    comic=await session.scalar(select(GeneratedComic).where(GeneratedComic.id==comic_id,GeneratedComic.organization_id==oid(membership)))
    if not comic: raise HTTPException(404,"HQ não encontrada")
    profile={"personality":data.personality,"speaking_style":data.speaking_style,"pedagogical_role":data.pedagogical_role,"immutable_traits":data.immutable_traits,"source":{"comic_id":str(comic_id),"page_id":str(data.page_id) if data.page_id else None,"panel_id":str(data.panel_id) if data.panel_id else None}}
    visibility=CreativeVisibility.PRIVATE if data.destination=="personal" else CreativeVisibility.TEAM
    item=CreativeItem(organization_id=oid(membership),created_by_user_id=user.id,created_by_name_snapshot=user.full_name,kind=CreativeItemKind.CHARACTER,name=data.name,description=data.description,canonical_prompt=data.canonical_prompt,negative_prompt=data.negative_prompt,profile_data=profile,visibility=visibility,status=CreativeStatus.ACTIVE,rights_confirmed=data.rights_confirmed,original_author=user.full_name,license_notes="Personagem derivado de HQ criada no EduCode")
    session.add(item); await session.flush()
    item.versions.append(CreativeVersion(version_number=1,profile_snapshot=profile,change_description="Personagem salvo a partir da HQ",created_by_user_id=user.id))
    institutional_id=None
    status="saved"
    if data.destination=="institutional_review":
        inst=InstitutionalAsset(organization_id=oid(membership),asset_type=InstitutionalAssetType.CHARACTER,name=data.name,description=data.description,category="Personagens gerados",status=InstitutionalAssetStatus.IN_REVIEW,visibility=InstitutionalAssetVisibility.ORGANIZATION,metadata_json=profile,canonical_prompt=data.canonical_prompt,negative_prompt=data.negative_prompt,immutable_traits=data.immutable_traits,license_type=InstitutionalLicenseType.AUTHORIZED_USE,original_author=user.full_name,rights_confirmed=data.rights_confirmed,source_comic_id=comic_id,source_page_id=data.page_id,source_panel_id=data.panel_id,source_creative_item_id=item.id,created_by_user_id=user.id)
        session.add(inst); await session.flush(); institutional_id=inst.id; status="submitted_for_review"
        inst.versions.append(InstitutionalAssetVersion(version_number=1,snapshot_json=profile,change_description="Submissão de personagem gerado",created_by_user_id=user.id))
    await session.commit()
    return GeneratedCharacterSaveResponse(creative_item_id=item.id,institutional_asset_id=institutional_id,name=item.name,destination=data.destination,status=status)
