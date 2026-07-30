from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.comic import (
    ComicBalloon,
    ComicPage,
    ComicPanel,
    ComicReviewComment,
    ComicStatus,
    ComicVersion,
    ComicVersionScope,
    GeneratedComic,
    GenerationRunStatus,
    PanelStatus,
)
from app.schemas.comic import (
    AutosaveRequest,
    CanvasExport,
    CanvasReadinessRead,
    ComicBalloonCreate,
    ComicBalloonUpdate,
    ComicCreate,
    ComicPageUpdate,
    ComicPanelUpdate,
    ComicRead,
    ComicRegenerationProposalRead,
    ComicReviewApprovalRead,
    ComicReviewCommentRead,
    ComicSummary,
    ComicUpdate,
    ComicVersionRead,
    ContinuityIssue,
    ContinuityReport,
    LayoutTemplateRead,
    NarrativeMapRead,
    PanelLockRequest,
    PanelReorderRequest,
    RegenerateRequest,
    RegenerationPolicyRead,
    RegenerationProposalRequest,
    ReviewApprovalUpsert,
    ReviewCommentCreate,
    ReviewCommentUpdate,
    ServerDraftRead,
    StabilityReportRead,
    VersionRestoreRequest,
)
from app.services.comics.layouts import list_layout_templates
from app.services.comics.manager import (
    ComicManagerError,
    canvas_export,
    create_comic,
    create_version_after_change,
    load_comic,
    regenerate,
    resize_page,
    restore_version,
    snapshot_comic,
    validate_comic,
)
from app.services.comics.stability import (
    analyze_stability,
    canvas_readiness,
    regeneration_policy,
)
from app.services.comics.review import (
    accept_regeneration_proposal,
    create_regeneration_proposals,
    narrative_map,
    redo_last_operation,
    undo_last_operation,
    update_comment_status,
    upsert_review_approval,
)

router = APIRouter(prefix="/comics", tags=["HQs estruturadas"])

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


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="HQ não encontrada")


def _assert_edit_revision(comic: GeneratedComic, expected_revision: int | None) -> None:
    if expected_revision is not None and expected_revision != comic.edit_revision:
        editor = comic.last_editor_name_snapshot or "outro usuário"
        raise HTTPException(
            status_code=409,
            detail=(
                f"A HQ foi alterada por {editor}. "
                f"Revisão atual do servidor: {comic.edit_revision}. "
                "Atualize o editor e compare as mudanças antes de salvar."
            ),
        )


def _find_page(comic: GeneratedComic, page_id: UUID) -> ComicPage | None:
    return next((page for page in comic.pages if page.id == page_id), None)


def _find_panel(comic: GeneratedComic, panel_id: UUID) -> ComicPanel | None:
    return next(
        (panel for page in comic.pages for panel in page.panels if panel.id == panel_id),
        None,
    )


def _find_balloon(comic: GeneratedComic, balloon_id: UUID) -> ComicBalloon | None:
    return next(
        (
            balloon
            for page in comic.pages
            for panel in page.panels
            for balloon in panel.balloons
            if balloon.id == balloon_id
        ),
        None,
    )


@router.get("/layout-templates", response_model=list[LayoutTemplateRead])
async def layout_templates(
    _: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[LayoutTemplateRead]:
    return [LayoutTemplateRead.model_validate(item) for item in list_layout_templates()]


@router.get("", response_model=list[ComicSummary])
async def list_comics(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[ComicSummary]:
    comics = list(
        (
            await session.scalars(
                select(GeneratedComic)
                .where(GeneratedComic.organization_id == org_id(membership))
                .order_by(GeneratedComic.updated_at.desc())
            )
        ).all()
    )
    summaries: list[ComicSummary] = []
    for comic in comics:
        page_count = int(
            (
                await session.scalar(
                    select(func.count(ComicPage.id)).where(ComicPage.comic_id == comic.id)
                )
            )
            or 0
        )
        panel_count = int(
            (
                await session.scalar(
                    select(func.count(ComicPanel.id))
                    .join(ComicPage, ComicPage.id == ComicPanel.page_id)
                    .where(ComicPage.comic_id == comic.id)
                )
            )
            or 0
        )
        summaries.append(
            ComicSummary(
                id=comic.id,
                generation_project_id=comic.generation_project_id,
                rag_context_id=comic.rag_context_id,
                title=comic.title,
                synopsis=comic.synopsis,
                status=comic.status,
                current_version=comic.current_version,
                page_count=page_count,
                panel_count=panel_count,
                continuity_score=comic.continuity_score,
                pedagogical_score=comic.pedagogical_score,
                updated_at=comic.updated_at,
            )
        )
    return summaries


@router.post("", response_model=ComicRead, status_code=201)
async def generate_comic(
    data: ComicCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    try:
        comic = await create_comic(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            user_name=user.full_name,
            data=data,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ComicRead.model_validate(comic)


@router.get("/{comic_id}", response_model=ComicRead)
async def read_comic(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return ComicRead.model_validate(comic)


@router.patch("/{comic_id}", response_model=ComicRead)
async def update_comic(
    comic_id: UUID,
    data: ComicUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
    expected_revision: int | None = Header(default=None, alias="If-Match-Revision"),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    _assert_edit_revision(comic, expected_revision)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(comic, field, value)
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.COMIC,
        description="Edição das configurações gerais da HQ",
    )
    return ComicRead.model_validate(updated)


@router.patch("/{comic_id}/pages/{page_id}", response_model=ComicRead)
async def update_page(
    comic_id: UUID,
    page_id: UUID,
    data: ComicPageUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
    expected_revision: int | None = Header(default=None, alias="If-Match-Revision"),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    _assert_edit_revision(comic, expected_revision)
    page = _find_page(comic, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    payload = data.model_dump(exclude_unset=True)
    panel_count = payload.pop("panel_count", None)
    requested_template = payload.pop("layout_template", None)
    layout_template = str(requested_template or page.layout_template)
    for field, value in payload.items():
        setattr(page, field, value)
    if panel_count is not None or requested_template is not None:
        await resize_page(
            session,
            comic=comic,
            page=page,
            panel_count=int(panel_count or page.panel_count),
            layout_template=layout_template,
        )
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PAGE,
        description=f"Edição da página {page.page_number}",
        target_page_id=page.id,
    )
    return ComicRead.model_validate(updated)


@router.post("/{comic_id}/pages/{page_id}/reorder", response_model=ComicRead)
async def reorder_panels(
    comic_id: UUID,
    page_id: UUID,
    data: PanelReorderRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    page = _find_page(comic, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    panel_map = {panel.id: panel for panel in page.panels}
    if set(data.panel_ids) != set(panel_map):
        raise HTTPException(status_code=422, detail="Informe todos os quadros da página")
    for temporary, panel in enumerate(page.panels, start=101):
        panel.reading_order = temporary
        panel.panel_number = temporary
    await session.flush()
    for order, panel_id in enumerate(data.panel_ids, start=1):
        panel_map[panel_id].reading_order = order
        panel_map[panel_id].panel_number = order
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PAGE,
        description=f"Reordenação dos quadros da página {page.page_number}",
        target_page_id=page.id,
    )
    return ComicRead.model_validate(updated)


@router.patch("/{comic_id}/panels/{panel_id}", response_model=ComicRead)
async def update_panel(
    comic_id: UUID,
    panel_id: UUID,
    data: ComicPanelUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
    expected_revision: int | None = Header(default=None, alias="If-Match-Revision"),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    _assert_edit_revision(comic, expected_revision)
    panel = _find_panel(comic, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(panel, field, value)
    panel.status = PanelStatus.NEEDS_REVIEW
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PANEL,
        description="Edição granular de quadro",
        target_panel_id=panel.id,
    )
    return ComicRead.model_validate(updated)


@router.post("/{comic_id}/panels/{panel_id}/duplicate", response_model=ComicRead)
async def duplicate_panel(
    comic_id: UUID,
    panel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    source = _find_panel(comic, panel_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado")
    page = _find_page(comic, source.page_id)
    if page is None or len(page.panels) >= 8:
        raise HTTPException(status_code=422, detail="A página já atingiu o limite de oito quadros")
    for temporary, panel in enumerate(page.panels, start=101):
        panel.reading_order = temporary
        panel.panel_number = temporary
    await session.flush()
    ordered = sorted(page.panels, key=lambda item: item.reading_order)
    insertion = next(index for index, panel in enumerate(ordered) if panel.id == source.id) + 1
    duplicate = ComicPanel(
        page_id=page.id,
        panel_number=insertion + 1,
        reading_order=insertion + 1,
        shape=source.shape,
        size_category=source.size_category,
        position_x=source.position_x,
        position_y=min(100.0, source.position_y + 4),
        width=source.width,
        height=source.height,
        border_style=source.border_style,
        border_width=source.border_width,
        rotation=source.rotation,
        z_index=source.z_index,
        is_full_bleed=source.is_full_bleed,
        clipping_mode=source.clipping_mode,
        narrative_goal=source.narrative_goal,
        pedagogical_goal=source.pedagogical_goal,
        ct_pillar_codes=list(source.ct_pillar_codes),
        scene_description=source.scene_description,
        previous_panel_summary=source.previous_panel_summary,
        next_panel_hook=source.next_panel_hook,
        initial_state=dict(source.initial_state),
        final_state=dict(source.final_state),
        emotion=source.emotion,
        plot_function="development",
        continuity_notes=["Quadro duplicado; revise a continuidade."],
        status=PanelStatus.NEEDS_REVIEW,
        locked_elements=list(source.locked_elements),
        visual_prompt=dict(source.visual_prompt),
        frozen_assets=dict(source.frozen_assets),
        pacing=source.pacing,
        image_asset_path=source.image_asset_path,
        alt_text=source.alt_text,
        audio_description=source.audio_description,
        text_word_limit=source.text_word_limit,
    )
    session.add(duplicate)
    await session.flush()
    for balloon in source.balloons:
        session.add(
            ComicBalloon(
                panel_id=duplicate.id,
                sequence_number=balloon.sequence_number,
                speaker_character_id=balloon.speaker_character_id,
                speaker_name_snapshot=balloon.speaker_name_snapshot,
                balloon_type=balloon.balloon_type,
                text=balloon.text,
                emotion=balloon.emotion,
                pedagogical_function=balloon.pedagogical_function,
                position_x=balloon.position_x,
                position_y=balloon.position_y,
                width=balloon.width,
                height=balloon.height,
                is_locked=balloon.is_locked,
                layer_config=dict(balloon.layer_config),
            )
        )
    all_panels = ordered[:insertion] + [duplicate] + ordered[insertion:]
    for order, panel in enumerate(all_panels, start=1):
        panel.reading_order = order
        panel.panel_number = order
    page.panel_count = len(all_panels)
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PANEL,
        description="Duplicação de quadro para edição",
        target_panel_id=duplicate.id,
    )
    return ComicRead.model_validate(updated)


@router.delete("/{comic_id}/panels/{panel_id}", status_code=204)
async def delete_panel(
    comic_id: UUID,
    panel_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> Response:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    panel = _find_panel(comic, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado")
    page = _find_page(comic, panel.page_id)
    if page is None or len(page.panels) <= 1:
        raise HTTPException(status_code=422, detail="A página precisa manter pelo menos um quadro")
    await session.delete(panel)
    await session.flush()
    remaining = sorted(
        [item for item in page.panels if item.id != panel_id],
        key=lambda item: item.reading_order,
    )
    for order, item in enumerate(remaining, start=1):
        item.reading_order = order
        item.panel_number = order
    page.panel_count = len(remaining)
    await session.flush()
    await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PAGE,
        description="Exclusão de quadro",
        target_page_id=page.id,
    )
    return Response(status_code=204)


@router.post("/{comic_id}/panels/{panel_id}/balloons", response_model=ComicRead, status_code=201)
async def create_balloon(
    comic_id: UUID,
    panel_id: UUID,
    data: ComicBalloonCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    panel = _find_panel(comic, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado")
    balloon = ComicBalloon(panel_id=panel.id, **data.model_dump())
    session.add(balloon)
    panel.status = PanelStatus.NEEDS_REVIEW
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.BALLOON,
        description="Inclusão de balão",
        target_panel_id=panel.id,
        target_balloon_id=balloon.id,
    )
    return ComicRead.model_validate(updated)


@router.patch("/{comic_id}/balloons/{balloon_id}", response_model=ComicRead)
async def update_balloon(
    comic_id: UUID,
    balloon_id: UUID,
    data: ComicBalloonUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
    expected_revision: int | None = Header(default=None, alias="If-Match-Revision"),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    _assert_edit_revision(comic, expected_revision)
    balloon = _find_balloon(comic, balloon_id)
    if balloon is None:
        raise HTTPException(status_code=404, detail="Balão não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(balloon, field, value)
    panel = _find_panel(comic, balloon.panel_id)
    if panel is not None:
        panel.status = PanelStatus.NEEDS_REVIEW
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.BALLOON,
        description="Edição de balão e diálogo",
        target_panel_id=balloon.panel_id,
        target_balloon_id=balloon.id,
    )
    return ComicRead.model_validate(updated)


@router.delete("/{comic_id}/balloons/{balloon_id}", status_code=204)
async def delete_balloon(
    comic_id: UUID,
    balloon_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> Response:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    balloon = _find_balloon(comic, balloon_id)
    if balloon is None:
        raise HTTPException(status_code=404, detail="Balão não encontrado")
    panel_id = balloon.panel_id
    await session.delete(balloon)
    await session.flush()
    await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.BALLOON,
        description="Exclusão de balão",
        target_panel_id=panel_id,
        target_balloon_id=balloon_id,
    )
    return Response(status_code=204)


@router.post("/{comic_id}/regenerate", response_model=ComicRead)
async def regenerate_content(
    comic_id: UUID,
    data: RegenerateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    try:
        comic = await regenerate(
            session,
            organization_id=org_id(membership),
            comic_id=comic_id,
            user_id=user.id,
            data=data,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ComicRead.model_validate(comic)


@router.get("/{comic_id}/continuity", response_model=ContinuityReport)
async def continuity_report(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> ContinuityReport:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    score, findings = validate_comic(comic)
    issues = [
        ContinuityIssue(
            severity=finding.severity,
            code=finding.code,
            message=finding.message,
            page_id=finding.page_id,
            panel_id=finding.panel_id,
            balloon_id=finding.balloon_id,
        )
        for finding in findings
    ]
    return ContinuityReport(
        comic_id=comic.id,
        score=score,
        is_valid=not any(issue.severity == "error" for issue in issues),
        issue_count=len(issues),
        issues=issues,
    )


@router.post("/{comic_id}/approve", response_model=ComicRead)
async def approve_comic(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    score, findings = validate_comic(comic)
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        raise HTTPException(
            status_code=422,
            detail=(
                "A HQ possui erros de continuidade que precisam ser corrigidos antes da aprovação"
            ),
        )
    required_reviews = {"narrative", "pedagogical", "visual", "accessibility"}
    approved_reviews = {
        key for key, value in comic.review_state.items() if str(value) == "approved"
    }
    missing_reviews = sorted(required_reviews - approved_reviews)
    if missing_reviews:
        raise HTTPException(
            status_code=422,
            detail=("Conclua as aprovações por especialidade: " + ", ".join(missing_reviews)),
        )
    open_comments = [comment for comment in comic.review_comments if comment.status.value == "open"]
    if open_comments:
        raise HTTPException(
            status_code=422,
            detail="Resolva ou descarte os comentários abertos antes da aprovação final",
        )
    comic.status = ComicStatus.APPROVED
    comic.approved_at = datetime.now(UTC)
    comic.continuity_score = score
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.COMIC,
        description="Aprovação pedagógica e narrativa da HQ",
    )
    return ComicRead.model_validate(updated)


@router.get("/{comic_id}/versions", response_model=list[ComicVersionRead])
async def list_versions(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[ComicVersionRead]:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    versions = list(
        (
            await session.scalars(
                select(ComicVersion)
                .where(ComicVersion.comic_id == comic.id)
                .order_by(ComicVersion.version_number.desc())
            )
        ).all()
    )
    return [ComicVersionRead.model_validate(version) for version in versions]


@router.post("/{comic_id}/versions/{version_id}/restore", response_model=ComicRead)
async def restore_comic_version(
    comic_id: UUID,
    version_id: UUID,
    data: VersionRestoreRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    try:
        comic = await restore_version(
            session,
            organization_id=org_id(membership),
            comic_id=comic_id,
            version_id=version_id,
            user_id=user.id,
            description=data.change_description,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ComicRead.model_validate(comic)


@router.get("/{comic_id}/export/json")
async def export_json(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> dict[str, object]:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return snapshot_comic(comic)


@router.get("/{comic_id}/export/canvas", response_model=CanvasExport)
async def export_canvas(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> CanvasExport:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return CanvasExport.model_validate(canvas_export(comic))


@router.post("/{comic_id}/panels/{panel_id}/locks", response_model=ComicRead)
async def set_panel_locks(
    comic_id: UUID,
    panel_id: UUID,
    data: PanelLockRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    panel = _find_panel(comic, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado")
    panel.locked_elements = list(dict.fromkeys(data.locked_elements))
    await session.flush()
    updated = await create_version_after_change(
        session,
        organization_id=org_id(membership),
        comic_id=comic.id,
        user_id=user.id,
        scope=ComicVersionScope.PANEL,
        description="Atualização dos bloqueios granulares do quadro",
        target_panel_id=panel.id,
    )
    return ComicRead.model_validate(updated)


@router.post(
    "/{comic_id}/regeneration-proposals",
    response_model=list[ComicRegenerationProposalRead],
    status_code=201,
)
async def propose_regeneration(
    comic_id: UUID,
    data: RegenerationProposalRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> list[ComicRegenerationProposalRead]:
    try:
        proposals = await create_regeneration_proposals(
            session,
            organization_id=org_id(membership),
            comic_id=comic_id,
            user_id=user.id,
            data=data,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [ComicRegenerationProposalRead.model_validate(item) for item in proposals]


@router.post(
    "/{comic_id}/regeneration-proposals/{proposal_id}/accept",
    response_model=ComicRead,
)
async def accept_proposal(
    comic_id: UUID,
    proposal_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    try:
        comic = await accept_regeneration_proposal(
            session,
            organization_id=org_id(membership),
            comic_id=comic_id,
            proposal_id=proposal_id,
            user_id=user.id,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ComicRead.model_validate(comic)


@router.get("/{comic_id}/narrative-map", response_model=NarrativeMapRead)
async def get_narrative_map(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> NarrativeMapRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return narrative_map(comic)


@router.get("/{comic_id}/comments", response_model=list[ComicReviewCommentRead])
async def list_review_comments(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[ComicReviewCommentRead]:
    comments = list(
        (
            await session.scalars(
                select(ComicReviewComment)
                .where(
                    ComicReviewComment.comic_id == comic_id,
                    ComicReviewComment.organization_id == org_id(membership),
                )
                .order_by(ComicReviewComment.created_at.desc())
            )
        ).all()
    )
    return [ComicReviewCommentRead.model_validate(item) for item in comments]


@router.post("/{comic_id}/comments", response_model=ComicReviewCommentRead, status_code=201)
async def create_review_comment(
    comic_id: UUID,
    data: ReviewCommentCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicReviewCommentRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    comment = ComicReviewComment(
        organization_id=org_id(membership),
        comic_id=comic.id,
        page_id=data.page_id,
        panel_id=data.panel_id,
        balloon_id=data.balloon_id,
        author_user_id=user.id,
        author_name_snapshot=user.full_name,
        specialty=data.specialty,
        body=data.body,
        anchor_x=data.anchor_x,
        anchor_y=data.anchor_y,
        priority=data.priority,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return ComicReviewCommentRead.model_validate(comment)


@router.patch("/{comic_id}/comments/{comment_id}", response_model=ComicReviewCommentRead)
async def change_review_comment(
    comic_id: UUID,
    comment_id: UUID,
    data: ReviewCommentUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> ComicReviewCommentRead:
    comment = await session.scalar(
        select(ComicReviewComment).where(
            ComicReviewComment.id == comment_id,
            ComicReviewComment.comic_id == comic_id,
            ComicReviewComment.organization_id == org_id(membership),
        )
    )
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    updated = await update_comment_status(session, comment=comment, status=data.status)
    return ComicReviewCommentRead.model_validate(updated)


@router.post("/{comic_id}/review-approvals", response_model=ComicReviewApprovalRead)
async def review_approval(
    comic_id: UUID,
    data: ReviewApprovalUpsert,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicReviewApprovalRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    approval = await upsert_review_approval(
        session,
        comic=comic,
        specialty=data.specialty,
        decision=data.decision,
        notes=data.notes,
        user_id=user.id,
        user_name=user.full_name,
    )
    return ComicReviewApprovalRead.model_validate(approval)


@router.post("/{comic_id}/autosave", response_model=ComicRead)
async def autosave_comic(
    comic_id: UUID,
    data: AutosaveRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    if data.expected_edit_revision is not None:
        _assert_edit_revision(comic, data.expected_edit_revision)
    if data.client_revision < comic.autosave_revision:
        raise HTTPException(status_code=409, detail="Há uma revisão mais recente no servidor")
    comic.autosave_revision = data.client_revision + 1
    comic.last_saved_at = datetime.now(UTC)
    comic.last_editor_user_id = user.id
    comic.last_editor_name_snapshot = user.full_name
    comic.last_editor_at = datetime.now(UTC)
    comic.story_state = {**comic.story_state, "last_draft_payload": data.draft_payload}
    await session.commit()
    updated = await load_comic(session, organization_id=org_id(membership), comic_id=comic.id)
    if updated is None:
        raise _not_found()
    return ComicRead.model_validate(updated)


@router.get("/{comic_id}/draft", response_model=ServerDraftRead)
async def read_server_draft(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> ServerDraftRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    payload = comic.story_state.get("last_draft_payload", {})
    return ServerDraftRead(
        comic_id=comic.id,
        autosave_revision=comic.autosave_revision,
        edit_revision=comic.edit_revision,
        last_saved_at=comic.last_saved_at,
        draft_payload=payload if isinstance(payload, dict) else {},
    )


@router.get("/{comic_id}/stability-report", response_model=StabilityReportRead)
async def stability_report(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> StabilityReportRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return StabilityReportRead.model_validate(analyze_stability(comic))


@router.get("/{comic_id}/canvas-readiness", response_model=CanvasReadinessRead)
async def canvas_readiness_report(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> CanvasReadinessRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    report = canvas_readiness(comic)
    comic.canvas_readiness_status = str(report["status"])
    comic.canvas_readiness_checked_at = report["checked_at"]
    await session.commit()
    return CanvasReadinessRead.model_validate(report)


@router.post("/{comic_id}/regeneration-policy", response_model=RegenerationPolicyRead)
async def preview_regeneration_policy(
    comic_id: UUID,
    data: RegenerateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> RegenerationPolicyRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    return RegenerationPolicyRead.model_validate(
        regeneration_policy(
            comic,
            scope=data.scope,
            page_id=data.page_id,
            panel_id=data.panel_id,
            preserve_dialogue=data.preserve_dialogue,
            preserve_scene=data.preserve_scene,
        )
    )


@router.post("/{comic_id}/generation-runs/{run_id}/cancel", response_model=ComicRead)
async def cancel_generation_run(
    comic_id: UUID,
    run_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> ComicRead:
    comic = await load_comic(session, organization_id=org_id(membership), comic_id=comic_id)
    if comic is None:
        raise _not_found()
    run = next((item for item in comic.generation_runs if item.id == run_id), None)
    if run is None:
        raise HTTPException(status_code=404, detail="Execução de geração não encontrada")
    if run.status not in {GenerationRunStatus.PENDING, GenerationRunStatus.RUNNING}:
        raise HTTPException(status_code=422, detail="A execução já foi finalizada e não pode ser cancelada")
    run.status = GenerationRunStatus.CANCELED
    run.finished_at = datetime.now(UTC)
    run.result_summary = {**run.result_summary, "canceled": True}
    await session.commit()
    updated = await load_comic(session, organization_id=org_id(membership), comic_id=comic.id)
    if updated is None:
        raise _not_found()
    return ComicRead.model_validate(updated)


@router.post("/{comic_id}/undo", response_model=ComicRead)
async def undo_comic(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    try:
        comic = await undo_last_operation(
            session,
            organization_id=org_id(membership),
            comic_id=comic_id,
            user_id=user.id,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ComicRead.model_validate(comic)


@router.post("/{comic_id}/redo", response_model=ComicRead)
async def redo_comic(
    comic_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> ComicRead:
    try:
        comic = await redo_last_operation(
            session,
            organization_id=org_id(membership),
            comic_id=comic_id,
            user_id=user.id,
        )
    except ComicManagerError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ComicRead.model_validate(comic)
