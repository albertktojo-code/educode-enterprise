from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comic import (
    ComicPanel,
    ComicRegenerationProposal,
    ComicReviewApproval,
    ComicReviewComment,
    ComicVersion,
    ComicVersionScope,
    EditOperationStatus,
    GeneratedComic,
    GenerationScope,
    ProposalStatus,
    ReviewCommentStatus,
    ReviewDecision,
    ReviewSpecialty,
)
from app.schemas.comic import (
    NarrativeMapItem,
    NarrativeMapRead,
    RegenerationProposalRequest,
)
from app.services.comics.generator import regenerate_panel_content
from app.services.comics.manager import (
    ComicManagerError,
    _apply_locked_regeneration,
    _generated_from_model,
    create_version_after_change,
    load_comic,
    restore_version,
)

TONE_LABELS = {
    "funny": "Mais engraçada",
    "emotional": "Mais emocionante",
    "mysterious": "Mais misteriosa",
    "dramatic": "Mais dramática",
    "surprising": "Mais surpreendente",
}


def _find_panel(comic: GeneratedComic, panel_id: UUID | None) -> ComicPanel | None:
    if panel_id is None:
        return None
    return next(
        (panel for page in comic.pages for panel in page.panels if panel.id == panel_id),
        None,
    )


def narrative_map(comic: GeneratedComic) -> NarrativeMapRead:
    items: list[NarrativeMapItem] = []
    pacing_values: list[str] = []
    clues: list[str] = []
    resolved_clues: list[str] = []
    for page in sorted(comic.pages, key=lambda item: item.page_number):
        for panel in sorted(page.panels, key=lambda item: item.reading_order):
            text = " ".join(balloon.text for balloon in panel.balloons)
            word_count = len(text.split())
            final_state = panel.final_state if isinstance(panel.final_state, dict) else {}
            panel_clues = (
                [str(value) for value in final_state.get("clues", []) if str(value).strip()]
                if isinstance(final_state.get("clues", []), list)
                else []
            )
            if panel.plot_function == "clue" and not panel_clues:
                panel_clues = [panel.next_panel_hook or panel.narrative_goal]
            clues.extend(panel_clues)
            if panel.plot_function in {"plot_twist", "resolution"}:
                resolved_clues.extend(clues)
            open_questions = (
                [
                    str(value)
                    for value in final_state.get("open_questions", [])
                    if str(value).strip()
                ]
                if isinstance(final_state.get("open_questions", []), list)
                else []
            )
            pacing_values.append(panel.pacing or "moderate")
            items.append(
                NarrativeMapItem(
                    page_number=page.page_number,
                    panel_id=panel.id,
                    reading_order=panel.reading_order,
                    plot_function=panel.plot_function or "development",
                    pacing=panel.pacing or "moderate",
                    emotion=panel.emotion or "curiosity",
                    narrative_goal=panel.narrative_goal,
                    open_questions=open_questions,
                    clues=panel_clues,
                    word_count=word_count,
                    over_text_limit=word_count > panel.text_word_limit,
                )
            )
    pacing_warnings: list[str] = []
    if len(set(pacing_values)) <= 1 and len(pacing_values) > 3:
        pacing_warnings.append("Todos os quadros usam o mesmo ritmo narrativo.")
    if sum(item.over_text_limit for item in items) > 0:
        pacing_warnings.append("Há quadros com texto acima do limite configurado.")
    unresolved = sorted(set(clues) - set(resolved_clues))
    return NarrativeMapRead(
        comic_id=comic.id,
        items=items,
        pacing_warnings=pacing_warnings,
        unresolved_clues=unresolved,
    )


async def create_regeneration_proposals(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    user_id: UUID,
    data: RegenerationProposalRequest,
) -> list[ComicRegenerationProposal]:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    panel = _find_panel(comic, data.panel_id)
    if panel is None:
        raise ComicManagerError("Selecione um quadro para comparar alternativas")
    if "panel" in panel.locked_elements:
        raise ComicManagerError("O quadro inteiro está bloqueado")

    tones = data.tones or ["funny", "emotional", "mysterious"]
    proposals: list[ComicRegenerationProposal] = []
    base = _generated_from_model(panel)
    for index in range(data.alternative_count):
        tone = tones[index % len(tones)]
        label = TONE_LABELS.get(tone, f"Alternativa {index + 1}")
        instruction = " · ".join(
            value
            for value in [data.change_instruction, f"tom {tone}", "preservar fatos pedagógicos"]
            if value
        )
        payload = regenerate_panel_content(
            base,
            scope=data.scope.value,
            instruction=instruction,
            preserve_dialogue=data.preserve_dialogue,
            preserve_scene=data.preserve_scene,
        )
        payload["emotion"] = tone
        proposal = ComicRegenerationProposal(
            comic_id=comic.id,
            requested_by_user_id=user_id,
            scope=data.scope,
            target_page_id=data.page_id,
            target_panel_id=panel.id,
            label=label,
            tone=tone,
            instruction=instruction,
            proposal_payload=dict(payload),
        )
        session.add(proposal)
        proposals.append(proposal)
    await session.commit()
    for proposal in proposals:
        await session.refresh(proposal)
    return proposals


async def accept_regeneration_proposal(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    proposal_id: UUID,
    user_id: UUID,
) -> GeneratedComic:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    proposal = await session.scalar(
        select(ComicRegenerationProposal).where(
            ComicRegenerationProposal.id == proposal_id,
            ComicRegenerationProposal.comic_id == comic.id,
        )
    )
    if proposal is None:
        raise ComicManagerError("Alternativa não encontrada")
    if proposal.status != ProposalStatus.PROPOSED:
        raise ComicManagerError("A alternativa já foi processada")
    panel = _find_panel(comic, proposal.target_panel_id)
    if panel is None:
        raise ComicManagerError("Quadro da alternativa não encontrado")
    payload = proposal.proposal_payload
    if not isinstance(payload, dict):
        raise ComicManagerError("Conteúdo da alternativa inválido")
    _apply_locked_regeneration(panel, cast(Any, payload), proposal.scope)
    proposal.status = ProposalStatus.ACCEPTED
    proposal.accepted_at = datetime.now(UTC)
    siblings = list(
        (
            await session.scalars(
                select(ComicRegenerationProposal).where(
                    ComicRegenerationProposal.comic_id == comic.id,
                    ComicRegenerationProposal.target_panel_id == panel.id,
                    ComicRegenerationProposal.status == ProposalStatus.PROPOSED,
                    ComicRegenerationProposal.id != proposal.id,
                )
            )
        ).all()
    )
    for sibling in siblings:
        sibling.status = ProposalStatus.SUPERSEDED
    await session.flush()
    return await create_version_after_change(
        session,
        organization_id=organization_id,
        comic_id=comic.id,
        user_id=user_id,
        scope=(
            ComicVersionScope.PAGE
            if proposal.scope == GenerationScope.PAGE
            else ComicVersionScope.PANEL
        ),
        description=f"Alternativa aceita: {proposal.label}",
        target_page_id=proposal.target_page_id,
        target_panel_id=proposal.target_panel_id,
    )


async def upsert_review_approval(
    session: AsyncSession,
    *,
    comic: GeneratedComic,
    specialty: ReviewSpecialty,
    decision: ReviewDecision,
    notes: str | None,
    user_id: UUID,
    user_name: str,
) -> ComicReviewApproval:
    approval = await session.scalar(
        select(ComicReviewApproval).where(
            ComicReviewApproval.comic_id == comic.id,
            ComicReviewApproval.specialty == specialty,
        )
    )
    if approval is None:
        approval = ComicReviewApproval(
            comic_id=comic.id,
            specialty=specialty,
            decision=decision,
            reviewer_user_id=user_id,
            reviewer_name_snapshot=user_name,
            notes=notes,
        )
        session.add(approval)
    else:
        approval.decision = decision
        approval.reviewer_user_id = user_id
        approval.reviewer_name_snapshot = user_name
        approval.notes = notes
        approval.reviewed_at = datetime.now(UTC)
    state = dict(comic.review_state)
    state[specialty.value] = decision.value
    comic.review_state = state
    await session.commit()
    await session.refresh(approval)
    return approval


async def update_comment_status(
    session: AsyncSession,
    *,
    comment: ComicReviewComment,
    status: ReviewCommentStatus,
) -> ComicReviewComment:
    comment.status = status
    comment.resolved_at = (
        datetime.now(UTC)
        if status in {ReviewCommentStatus.RESOLVED, ReviewCommentStatus.DISMISSED}
        else None
    )
    await session.commit()
    await session.refresh(comment)
    return comment


async def undo_last_operation(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    user_id: UUID,
) -> GeneratedComic:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    operation = next(
        (
            item
            for item in sorted(
                comic.edit_operations, key=lambda value: value.created_at, reverse=True
            )
            if item.status in {EditOperationStatus.APPLIED, EditOperationStatus.REDONE}
        ),
        None,
    )
    if operation is None:
        raise ComicManagerError("Não há operação disponível para desfazer")
    version = next(
        (item for item in comic.versions if item.snapshot_json == operation.before_snapshot),
        None,
    )
    if version is None:
        raise ComicManagerError("A versão anterior da operação não está disponível")
    operation.status = EditOperationStatus.UNDONE
    operation.reverted_at = datetime.now(UTC)
    await session.flush()
    return await restore_version(
        session,
        organization_id=organization_id,
        comic_id=comic.id,
        version_id=version.id,
        user_id=user_id,
        description=f"Desfazer: {operation.operation_type}",
    )


async def redo_last_operation(
    session: AsyncSession,
    *,
    organization_id: UUID,
    comic_id: UUID,
    user_id: UUID,
) -> GeneratedComic:
    comic = await load_comic(session, organization_id=organization_id, comic_id=comic_id)
    if comic is None:
        raise ComicManagerError("HQ não encontrada")
    operation = next(
        (
            item
            for item in sorted(
                comic.edit_operations, key=lambda value: value.created_at, reverse=True
            )
            if item.status == EditOperationStatus.UNDONE
        ),
        None,
    )
    if operation is None:
        raise ComicManagerError("Não há operação disponível para refazer")
    version: ComicVersion | None = next(
        (item for item in comic.versions if item.snapshot_json == operation.after_snapshot),
        None,
    )
    if version is None:
        raise ComicManagerError("A versão posterior da operação não está disponível")
    operation.status = EditOperationStatus.REDONE
    operation.reverted_at = None
    await session.flush()
    return await restore_version(
        session,
        organization_id=organization_id,
        comic_id=comic.id,
        version_id=version.id,
        user_id=user_id,
        description=f"Refazer: {operation.operation_type}",
    )
