from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.comic import (
    ComicPage,
    ComicPanel,
    ComicVersion,
    ComicVersionScope,
    GeneratedComic,
    PreviewReviewStatus,
)
from app.schemas.preview import (
    PreviewReviewRequest,
    PreviewReviewResult,
    PreviewValidationRead,
    StoryboardRead,
    StudentPreviewRead,
    VersionComparisonRead,
)
from app.services.comics.manager import create_version_after_change, load_comic
from app.services.comics.preview import (
    build_storyboard,
    compare_version_snapshots,
    validate_preview,
)

router = APIRouter(prefix="/comics", tags=["Storyboard e pré-visualização"])

READ_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
WRITE_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)


def _org_id(membership: Membership) -> UUID:
    return membership.organization_id


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="HQ não encontrada")


def _find_page(comic: GeneratedComic, page_id: UUID) -> ComicPage | None:
    return next((page for page in comic.pages if page.id == page_id), None)


def _find_panel(comic: GeneratedComic, panel_id: UUID) -> ComicPanel | None:
    return next(
        (panel for page in comic.pages for panel in page.panels if panel.id == panel_id),
        None,
    )


def _sync_preview_status(comic: GeneratedComic) -> None:
    pages = list(comic.pages)
    panels = [panel for page in pages for panel in page.panels]
    if pages and panels and all(
        page.preview_review_status in {PreviewReviewStatus.APPROVED, PreviewReviewStatus.LOCKED}
        for page in pages
    ) and all(
        panel.preview_review_status in {PreviewReviewStatus.APPROVED, PreviewReviewStatus.LOCKED}
        for panel in panels
    ):
        comic.preview_status = PreviewReviewStatus.APPROVED
        comic.preview_checked_at = datetime.now(UTC)
    elif any(
        item.preview_review_status == PreviewReviewStatus.CHANGES_REQUESTED
        for item in [*pages, *panels]
    ):
        comic.preview_status = PreviewReviewStatus.CHANGES_REQUESTED
        comic.preview_checked_at = datetime.now(UTC)
    else:
        comic.preview_status = PreviewReviewStatus.IN_REVIEW
        comic.preview_checked_at = datetime.now(UTC)


@router.get("/{comic_id}/storyboard", response_model=StoryboardRead)
async def storyboard(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> StoryboardRead:
    comic = await load_comic(session, organization_id=_org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return StoryboardRead.model_validate(build_storyboard(comic))


@router.get("/{comic_id}/preview-validation", response_model=PreviewValidationRead)
async def preview_validation(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> PreviewValidationRead:
    comic = await load_comic(session, organization_id=_org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return PreviewValidationRead.model_validate(validate_preview(comic))


@router.post("/{comic_id}/pages/{page_id}/preview-review", response_model=PreviewReviewResult)
async def review_page_preview(
    comic_id: UUID,
    page_id: UUID,
    data: PreviewReviewRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> PreviewReviewResult:
    comic = await load_comic(session, organization_id=_org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    page = _find_page(comic, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    status = (
        PreviewReviewStatus.LOCKED
        if data.lock_after_approval
        and data.status == PreviewReviewStatus.APPROVED
        else data.status
    )
    page.preview_review_status = status
    page.preview_reviewed_by_user_id = user.id
    page.preview_reviewed_at = datetime.now(UTC)
    page.preview_review_notes = data.notes
    if status in {PreviewReviewStatus.APPROVED, PreviewReviewStatus.LOCKED}:
        for panel in page.panels:
            if panel.preview_review_status == PreviewReviewStatus.NOT_REVIEWED:
                panel.preview_review_status = PreviewReviewStatus.APPROVED
                panel.preview_reviewed_by_user_id = user.id
                panel.preview_reviewed_at = page.preview_reviewed_at
    _sync_preview_status(comic)
    await session.flush()
    await create_version_after_change(
        session,
        organization_id=_org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PAGE,
        description=f"Revisão da prévia da página {page.page_number}: {status.value}",
        target_page_id=page.id,
        reset_preview=False,
    )
    return PreviewReviewResult(
        comic_id=comic.id,
        target_type="page",
        target_id=page.id,
        status=status,
        reviewed_by_user_id=user.id,
        reviewed_by_name=user.full_name,
        reviewed_at=page.preview_reviewed_at,
        notes=data.notes,
    )


@router.post("/{comic_id}/panels/{panel_id}/preview-review", response_model=PreviewReviewResult)
async def review_panel_preview(
    comic_id: UUID,
    panel_id: UUID,
    data: PreviewReviewRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> PreviewReviewResult:
    comic = await load_comic(session, organization_id=_org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    panel = _find_panel(comic, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado")
    status = (
        PreviewReviewStatus.LOCKED
        if data.lock_after_approval
        and data.status == PreviewReviewStatus.APPROVED
        else data.status
    )
    panel.preview_review_status = status
    panel.preview_reviewed_by_user_id = user.id
    panel.preview_reviewed_at = datetime.now(UTC)
    panel.preview_review_notes = data.notes
    _sync_preview_status(comic)
    await session.flush()
    await create_version_after_change(
        session,
        organization_id=_org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PANEL,
        description=f"Revisão da prévia do quadro {panel.panel_number}: {status.value}",
        target_panel_id=panel.id,
        reset_preview=False,
    )
    return PreviewReviewResult(
        comic_id=comic.id,
        target_type="panel",
        target_id=panel.id,
        status=status,
        reviewed_by_user_id=user.id,
        reviewed_by_name=user.full_name,
        reviewed_at=panel.preview_reviewed_at,
        notes=data.notes,
    )


@router.get("/{comic_id}/version-comparison", response_model=VersionComparisonRead)
async def compare_versions(
    comic_id: UUID,
    from_version: int = Query(ge=1),
    to_version: int = Query(ge=1),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> VersionComparisonRead:
    comic = await load_comic(session, organization_id=_org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    versions: dict[int, ComicVersion] = {
        version.version_number: version
        for version in comic.versions
    }
    before = versions.get(from_version)
    after = versions.get(to_version)
    if before is None or after is None:
        raise HTTPException(status_code=404, detail="Versão solicitada não encontrada")
    return VersionComparisonRead.model_validate(compare_version_snapshots(before, after))


@router.get("/{comic_id}/student-preview", response_model=StudentPreviewRead)
async def student_preview(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> StudentPreviewRead:
    comic = await load_comic(session, organization_id=_org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    pages: list[dict[str, object]] = []
    for page in sorted(comic.pages, key=lambda item: item.page_number):
        panels: list[dict[str, object]] = []
        for panel in sorted(page.panels, key=lambda item: item.reading_order):
            panels.append(
                {
                    "id": str(panel.id),
                    "panel_number": panel.panel_number,
                    "reading_order": panel.reading_order,
                    "shape": panel.shape.value,
                    "position_x": panel.position_x,
                    "position_y": panel.position_y,
                    "width": panel.width,
                    "height": panel.height,
                    "image_asset_path": panel.image_asset_path,
                    "alt_text": panel.alt_text,
                    "balloons": [
                        {
                            "id": str(balloon.id),
                            "sequence_number": balloon.sequence_number,
                            "speaker": balloon.speaker_name_snapshot,
                            "type": balloon.balloon_type.value,
                            "text": balloon.text,
                            "position_x": balloon.position_x,
                            "position_y": balloon.position_y,
                            "width": balloon.width,
                            "height": balloon.height,
                        }
                        for balloon in sorted(panel.balloons, key=lambda item: item.sequence_number)
                    ],
                }
            )
        pages.append(
            {
                "id": str(page.id),
                "page_number": page.page_number,
                "title": page.title,
                "page_role": page.page_role,
                "format": page.page_format.value,
                "orientation": page.orientation.value,
                "reading_direction": page.reading_direction.value,
                "panels": panels,
            }
        )
    direction = comic.pages[0].reading_direction.value if comic.pages else "left_to_right"
    return StudentPreviewRead(
        comic_id=comic.id,
        title=comic.title,
        version=comic.current_version,
        reading_direction=direction,
        pages=pages,
        accessibility={
            "has_alt_text": all(panel.alt_text for page in comic.pages for panel in page.panels),
            "supports_screen_reader": True,
            "supports_high_contrast": True,
            "supports_large_text": True,
        },
    )
