from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.comic import ComicVersionScope
from app.models.studio import (
    ArtDirectionPreset,
    PublicationPreparation,
    TeacherStudioDraft,
)
from app.schemas.comic import ComicRead
from app.schemas.studio import (
    ArtDirectionPresetRead,
    CanvasBulkUpdate,
    PackageCreateRequest,
    PageCreateRequest,
    PageReorderRequest,
    PedagogicalPackageRead,
    PublicationPreparationRead,
    RecommendPagesRequest,
    TeacherStudioDraftCreate,
    TeacherStudioDraftRead,
    TeacherStudioDraftUpdate,
)
from app.services.comics.manager import (
    ComicManagerError,
    create_version_after_change,
    load_comic,
)
from app.services.teacher_studio import (
    STUDIO_TEMPLATES,
    SYSTEM_ART_PRESETS,
    add_page,
    apply_canvas_bulk,
    create_package,
    duplicate_page,
    get_draft,
    get_package,
    publication_checklist,
    recommend_page_plan,
)

router = APIRouter(prefix="/teacher-studio", tags=["Estúdio do Professor"])

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


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


@router.get("/templates")
async def list_templates(_: Membership = Depends(require_roles(*READ_ROLES))) -> list[dict[str, object]]:
    return STUDIO_TEMPLATES


@router.get("/art-presets", response_model=list[ArtDirectionPresetRead])
async def list_art_presets(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[ArtDirectionPresetRead]:
    custom = list((await session.scalars(select(ArtDirectionPreset).where(
        ArtDirectionPreset.is_active.is_(True),
        (ArtDirectionPreset.organization_id == org_id(membership)) | (ArtDirectionPreset.organization_id.is_(None)),
    ).order_by(ArtDirectionPreset.name))).all())
    result = [ArtDirectionPresetRead.model_validate(item) for item in SYSTEM_ART_PRESETS]
    result.extend(ArtDirectionPresetRead.model_validate(item) for item in custom)
    return result


@router.get("/drafts", response_model=list[TeacherStudioDraftRead])
async def list_drafts(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[TeacherStudioDraftRead]:
    drafts = list((await session.scalars(
        select(TeacherStudioDraft)
        .where(TeacherStudioDraft.organization_id == org_id(membership))
        .order_by(TeacherStudioDraft.updated_at.desc())
    )).all())
    return [TeacherStudioDraftRead.model_validate(item) for item in drafts]


@router.post("/drafts", response_model=TeacherStudioDraftRead, status_code=201)
async def create_draft(
    data: TeacherStudioDraftCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> TeacherStudioDraftRead:
    draft = TeacherStudioDraft(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        generation_project_id=data.generation_project_id,
        rag_context_id=data.rag_context_id,
        title=data.title,
        creation_mode=data.creation_mode,
        primary_material=data.primary_material,
        subject_name=data.subject_name,
        school_year=data.school_year,
        topic=data.topic,
        objective=data.objective,
        wizard_data=data.wizard_data,
        selected_outputs=[item.value for item in data.selected_outputs],
        page_plan=[item.model_dump(mode="json") for item in data.page_plan],
        art_direction=data.art_direction.model_dump(mode="json"),
        accessibility_options=data.accessibility_options,
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return TeacherStudioDraftRead.model_validate(draft)


@router.get("/drafts/{draft_id}", response_model=TeacherStudioDraftRead)
async def read_draft(
    draft_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> TeacherStudioDraftRead:
    draft = await get_draft(session, org_id(membership), draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado")
    return TeacherStudioDraftRead.model_validate(draft)


@router.patch("/drafts/{draft_id}", response_model=TeacherStudioDraftRead)
async def update_draft(
    draft_id: UUID,
    data: TeacherStudioDraftUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> TeacherStudioDraftRead:
    draft = await get_draft(session, org_id(membership), draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado")
    values = data.model_dump(exclude_unset=True)
    for field, value in values.items():
        if field == "selected_outputs" and value is not None:
            value = [item.value for item in value]
        elif field == "art_direction" and data.art_direction is not None:
            value = data.art_direction.model_dump(mode="json")
        elif field == "page_plan" and data.page_plan is not None:
            value = [item.model_dump(mode="json") for item in data.page_plan]
        setattr(draft, field, value)
    await session.commit()
    await session.refresh(draft)
    return TeacherStudioDraftRead.model_validate(draft)


@router.post("/drafts/{draft_id}/recommend-pages", response_model=list[dict[str, object]])
async def recommend_pages(
    draft_id: UUID,
    data: RecommendPagesRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> list[dict[str, object]]:
    draft = await get_draft(session, org_id(membership), draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado")
    draft.page_plan = recommend_page_plan(data)
    await session.commit()
    return draft.page_plan


@router.post("/drafts/{draft_id}/packages", response_model=PedagogicalPackageRead, status_code=201)
async def generate_package(
    draft_id: UUID,
    data: PackageCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> PedagogicalPackageRead:
    draft = await get_draft(session, org_id(membership), draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado")
    try:
        package = await create_package(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            user_name=user.full_name,
            draft=draft,
            request=data,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await session.commit()
    refreshed = await get_package(session, org_id(membership), package.id)
    return PedagogicalPackageRead.model_validate(refreshed or package)


@router.get("/packages", response_model=list[PedagogicalPackageRead])
async def list_packages(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[PedagogicalPackageRead]:
    from app.models.studio import PedagogicalPackage
    from sqlalchemy.orm import selectinload

    packages = list((await session.scalars(
        select(PedagogicalPackage)
        .where(PedagogicalPackage.organization_id == org_id(membership))
        .options(selectinload(PedagogicalPackage.materials), selectinload(PedagogicalPackage.publication_preparations))
        .order_by(PedagogicalPackage.updated_at.desc())
    )).all())
    return [PedagogicalPackageRead.model_validate(item) for item in packages]


@router.get("/packages/{package_id}", response_model=PedagogicalPackageRead)
async def read_package(
    package_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> PedagogicalPackageRead:
    package = await get_package(session, org_id(membership), package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Pacote não encontrado")
    return PedagogicalPackageRead.model_validate(package)


@router.post("/packages/{package_id}/prepare-publication", response_model=PublicationPreparationRead)
async def prepare_publication(
    package_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> PublicationPreparationRead:
    package = await get_package(session, org_id(membership), package_id)
    if package is None:
        raise HTTPException(status_code=404, detail="Pacote não encontrado")
    comic = None
    if package.comic_id is not None:
        comic = await load_comic(session, organization_id=org_id(membership), comic_id=package.comic_id)
    readiness, checklist = publication_checklist(package, comic)
    preparation = PublicationPreparation(
        organization_id=org_id(membership),
        package_id=package.id,
        requested_by_user_id=user.id,
        readiness=readiness,
        checklist=checklist,
        manifest={"outputs": package.outputs, "comic_id": str(package.comic_id) if package.comic_id else None, "version": "educode.publication.v1"},
    )
    session.add(preparation)
    package.preparation_report = {"readiness": readiness.value, "checklist": checklist}
    await session.commit()
    await session.refresh(preparation)
    return PublicationPreparationRead.model_validate(preparation)


@router.post("/comics/{comic_id}/canvas", response_model=ComicRead)
async def save_canvas(
    comic_id: UUID,
    data: CanvasBulkUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    try:
        updated = await apply_canvas_bulk(session, comic=comic, data=data, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ComicRead.model_validate(updated)


@router.post("/comics/{comic_id}/pages", response_model=ComicRead, status_code=201)
async def create_comic_page(
    comic_id: UUID,
    data: PageCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    await add_page(session, comic, data)
    updated = await create_version_after_change(session, organization_id=org_id(membership), comic_id=comic.id, user_id=user.id, scope=ComicVersionScope.PAGE, description="Nova página adicionada")
    return ComicRead.model_validate(updated)


@router.post("/comics/{comic_id}/pages/{page_id}/duplicate", response_model=ComicRead)
async def duplicate_comic_page(
    comic_id: UUID,
    page_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    try:
        await duplicate_page(session, comic, page_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    updated = await create_version_after_change(session, organization_id=org_id(membership), comic_id=comic.id, user_id=user.id, scope=ComicVersionScope.PAGE, description="Página duplicada")
    return ComicRead.model_validate(updated)


@router.delete("/comics/{comic_id}/pages/{page_id}", response_model=ComicRead)
async def delete_comic_page(
    comic_id: UUID,
    page_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    page = next((item for item in comic.pages if item.id == page_id), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    if len(comic.pages) <= 1:
        raise HTTPException(status_code=422, detail="A HQ precisa manter ao menos uma página")
    await session.delete(page)
    await session.flush()
    remaining = [item for item in comic.pages if item.id != page_id]
    for temporary, item in enumerate(remaining, start=101):
        item.page_number = temporary
    await session.flush()
    for number, item in enumerate(sorted(remaining, key=lambda value: value.page_number), start=1):
        item.page_number = number
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PAGE,
        description="Página excluída",
    )
    return ComicRead.model_validate(updated)


@router.post("/comics/{comic_id}/pages/reorder", response_model=ComicRead)
async def reorder_comic_pages(
    comic_id: UUID,
    data: PageReorderRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise HTTPException(status_code=404, detail="HQ não encontrada")
    page_map = {page.id: page for page in comic.pages}
    if set(data.page_ids) != set(page_map):
        raise HTTPException(status_code=422, detail="Informe todas as páginas")
    for temporary, page in enumerate(comic.pages, start=101):
        page.page_number = temporary
    await session.flush()
    for number, page_id in enumerate(data.page_ids, start=1):
        page_map[page_id].page_number = number
    await session.flush()
    updated = await create_version_after_change(session, organization_id=org_id(membership), comic_id=comic.id, user_id=user.id, scope=ComicVersionScope.COMIC, description="Páginas reorganizadas")
    return ComicRead.model_validate(updated)
