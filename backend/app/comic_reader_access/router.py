from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import QuestionBankItem
from app.models.delivery import MaterialAssignment
from app.services.consolidated_audit import append_domain_audit

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import (
    calculate_progress,
    can_transition_presentation,
    generate_join_code,
    normalize_preferences,
    validate_sequence,
)
from .schemas import (
    AssessmentLinkCreate,
    BookmarkCreate,
    CheckpointUpsert,
    GlossaryTermCreate,
    NarrationTrackCreate,
    PresentationAdvance,
    PresentationCreate,
    PresentationJoin,
    PresentationTransition,
    ReaderPreferenceUpsert,
)
from .services import accessible_releases, is_staff, release_for_actor, release_manifest

router = APIRouter(prefix="/comic-reader", tags=["comic-reader"])
SessionDep = Annotated[AsyncSession, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]


def require_staff(actor: ActorContext) -> None:
    if not is_staff(actor):
        raise HTTPException(403, "Esta operacao exige perfil de professor ou gestor.")


def presentation_payload(item: models.ComicPresentationSession) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "release_id": str(item.release_id),
        "presenter_user_id": str(item.presenter_user_id),
        "title": item.title,
        "join_code": item.join_code,
        "status": item.status,
        "current_page": item.current_page,
        "current_panel": item.current_panel,
        "reveal_step": item.reveal_step,
        "revision": item.revision,
        "allow_audience_join": item.allow_audience_join,
        "sync_audience": item.sync_audience,
        "reveal_mode": item.reveal_mode,
        "settings": item.settings,
        "presenter_note": item.presenter_note,
        "started_at": item.started_at,
        "ended_at": item.ended_at,
        "updated_at": item.updated_at,
    }


async def presentation_or_404(
    session: AsyncSession,
    actor: ActorContext,
    presentation_id: uuid.UUID,
) -> models.ComicPresentationSession:
    item = await session.scalar(
        select(models.ComicPresentationSession).where(
            models.ComicPresentationSession.organization_id == actor.organization_id,
            models.ComicPresentationSession.id == presentation_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Apresentacao nao encontrada.")
    return item


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "16.5", "module": "comic-reader-access"}


@router.get("/releases")
async def list_releases(session: SessionDep, actor: ActorDep):
    releases = await accessible_releases(session, actor=actor)
    return [
        {
            "id": str(item.id),
            "comic_project_id": str(item.comic_project_id),
            "release_number": item.release_number,
            "release_name": item.release_name,
            "release_notes": item.release_notes,
            "status": item.status,
            "published_at": item.published_at,
            "scheduled_at": item.scheduled_at,
        }
        for item in releases
    ]


@router.get("/releases/{release_id}/manifest")
async def get_manifest(
    release_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    release = await release_for_actor(session, actor=actor, release_id=release_id)
    return await release_manifest(session, actor=actor, release=release)


@router.get("/preferences/me")
async def get_preferences(session: SessionDep, actor: ActorDep):
    item = await session.scalar(
        select(models.ComicReaderPreference).where(
            models.ComicReaderPreference.organization_id == actor.organization_id,
            models.ComicReaderPreference.user_id == actor.user_id,
        )
    )
    return normalize_preferences(item.preferences if item else None)


@router.put("/preferences/me")
async def save_preferences(
    data: ReaderPreferenceUpsert,
    session: SessionDep,
    actor: ActorDep,
):
    item = await session.scalar(
        select(models.ComicReaderPreference).where(
            models.ComicReaderPreference.organization_id == actor.organization_id,
            models.ComicReaderPreference.user_id == actor.user_id,
        )
    )
    preferences = normalize_preferences(data.model_dump())
    if item is None:
        item = models.ComicReaderPreference(
            organization_id=actor.organization_id,
            user_id=actor.user_id,
            preferences=preferences,
        )
        session.add(item)
    else:
        item.preferences = preferences
    await session.commit()
    return preferences


@router.get("/releases/{release_id}/checkpoint")
async def get_checkpoint(
    release_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    await release_for_actor(session, actor=actor, release_id=release_id)
    item = await session.scalar(
        select(models.ComicReadingCheckpoint).where(
            models.ComicReadingCheckpoint.organization_id == actor.organization_id,
            models.ComicReadingCheckpoint.release_id == release_id,
            models.ComicReadingCheckpoint.user_id == actor.user_id,
        )
    )
    if item is None:
        return {
            "release_id": str(release_id),
            "page_number": 1,
            "panel_number": 1,
            "completed_panels": 0,
            "progress_percent": 0,
            "elapsed_seconds": 0,
            "last_sequence": 0,
            "reader_mode": "PAGE",
            "state": {},
            "completed_at": None,
        }
    return {
        "release_id": str(release_id),
        "page_number": item.page_number,
        "panel_number": item.panel_number,
        "completed_panels": item.completed_panels,
        "progress_percent": item.progress_percent,
        "elapsed_seconds": item.elapsed_seconds,
        "last_sequence": item.last_sequence,
        "reader_mode": item.reader_mode,
        "state": item.state,
        "completed_at": item.completed_at,
    }


@router.put("/releases/{release_id}/checkpoint")
async def save_checkpoint(
    release_id: uuid.UUID,
    data: CheckpointUpsert,
    session: SessionDep,
    actor: ActorDep,
):
    release = await release_for_actor(session, actor=actor, release_id=release_id)
    manifest = await release_manifest(session, actor=actor, release=release)
    pages = manifest["pages"]
    total_panels = sum(
        len(page.get("panels") or []) for page in pages if isinstance(page, dict)
    )
    progress = calculate_progress(
        current_page=data.page_number,
        current_panel=data.panel_number,
        total_pages=len(pages),
        total_panels=total_panels,
        completed_panels=data.completed_panels,
    )
    item = await session.scalar(
        select(models.ComicReadingCheckpoint).where(
            models.ComicReadingCheckpoint.organization_id == actor.organization_id,
            models.ComicReadingCheckpoint.release_id == release_id,
            models.ComicReadingCheckpoint.user_id == actor.user_id,
        )
    )
    if item is None:
        item = models.ComicReadingCheckpoint(
            organization_id=actor.organization_id,
            release_id=release_id,
            user_id=actor.user_id,
        )
        session.add(item)
    sequence = validate_sequence(item.last_sequence, data.sequence)
    if not sequence["accepted"]:
        raise HTTPException(409, sequence)
    item.page_number = data.page_number
    item.panel_number = data.panel_number
    item.completed_panels = data.completed_panels
    item.progress_percent = progress["progress_percent"]
    item.elapsed_seconds = max(item.elapsed_seconds, data.elapsed_seconds)
    item.last_sequence = data.sequence
    item.reader_mode = data.reader_mode
    item.state = data.state
    if progress["is_complete"]:
        item.completed_at = item.completed_at or datetime.now(UTC)
    await session.commit()
    return {"release_id": str(release_id), "last_sequence": item.last_sequence, **progress}


@router.get("/releases/{release_id}/bookmarks")
async def list_bookmarks(
    release_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    await release_for_actor(session, actor=actor, release_id=release_id)
    items = list(
        (
            await session.scalars(
                select(models.ComicReaderBookmark)
                .where(
                    models.ComicReaderBookmark.organization_id == actor.organization_id,
                    models.ComicReaderBookmark.release_id == release_id,
                    models.ComicReaderBookmark.user_id == actor.user_id,
                )
                .order_by(models.ComicReaderBookmark.created_at.desc())
            )
        ).all()
    )
    return [
        {
            "id": str(item.id),
            "page_number": item.page_number,
            "panel_number": item.panel_number,
            "label": item.label,
            "note": item.note,
            "created_at": item.created_at,
        }
        for item in items
    ]


@router.post("/releases/{release_id}/bookmarks", status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    release_id: uuid.UUID,
    data: BookmarkCreate,
    session: SessionDep,
    actor: ActorDep,
):
    await release_for_actor(session, actor=actor, release_id=release_id)
    item = models.ComicReaderBookmark(
        organization_id=actor.organization_id,
        release_id=release_id,
        user_id=actor.user_id,
        **data.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id)}


@router.delete("/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    item = await session.scalar(
        select(models.ComicReaderBookmark).where(
            models.ComicReaderBookmark.organization_id == actor.organization_id,
            models.ComicReaderBookmark.id == bookmark_id,
            models.ComicReaderBookmark.user_id == actor.user_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Marcador nao encontrado.")
    await session.delete(item)
    await session.commit()


@router.post("/releases/{release_id}/narrations", status_code=status.HTTP_201_CREATED)
async def create_narration(
    release_id: uuid.UUID,
    data: NarrationTrackCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    await release_for_actor(
        session, actor=actor, release_id=release_id, allow_unpublished_for_staff=True
    )
    item = models.ComicNarrationTrack(
        organization_id=actor.organization_id,
        release_id=release_id,
        created_by_user_id=actor.user_id,
        **data.model_dump(),
    )
    session.add(item)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_access",
        action="comic.reader.narration.created",
        entity_type="comic_narration_track",
        entity_id=item.id,
        details={"release_id": str(release_id)},
    )
    await session.commit()
    return {"id": str(item.id), "status": item.status}


@router.delete("/narrations/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_narration(
    track_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    item = await session.scalar(
        select(models.ComicNarrationTrack).where(
            models.ComicNarrationTrack.organization_id == actor.organization_id,
            models.ComicNarrationTrack.id == track_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Narracao nao encontrada.")
    await session.delete(item)
    await session.commit()


@router.post("/releases/{release_id}/glossary", status_code=status.HTTP_201_CREATED)
async def create_glossary(
    release_id: uuid.UUID,
    data: GlossaryTermCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    await release_for_actor(
        session, actor=actor, release_id=release_id, allow_unpublished_for_staff=True
    )
    item = models.ComicGlossaryTerm(
        organization_id=actor.organization_id,
        release_id=release_id,
        normalized_term=" ".join(data.term.lower().split()),
        created_by_user_id=actor.user_id,
        metadata_json=data.metadata,
        **data.model_dump(exclude={"metadata"}),
    )
    session.add(item)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_access",
        action="comic.reader.glossary.created",
        entity_type="comic_glossary_term",
        entity_id=item.id,
        details={"release_id": str(release_id), "term": item.term},
    )
    await session.commit()
    return {"id": str(item.id)}


@router.delete("/glossary/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_glossary(
    term_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    item = await session.scalar(
        select(models.ComicGlossaryTerm).where(
            models.ComicGlossaryTerm.organization_id == actor.organization_id,
            models.ComicGlossaryTerm.id == term_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Termo nao encontrado.")
    await session.delete(item)
    await session.commit()


@router.post(
    "/releases/{release_id}/assessment-links",
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_link(
    release_id: uuid.UUID,
    data: AssessmentLinkCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    await release_for_actor(
        session, actor=actor, release_id=release_id, allow_unpublished_for_staff=True
    )
    question = await session.scalar(
        select(QuestionBankItem).where(
            QuestionBankItem.organization_id == actor.organization_id,
            QuestionBankItem.id == data.question_bank_item_id,
        )
    )
    if question is None:
        raise HTTPException(404, "Questao institucional nao encontrada.")
    if data.assignment_id:
        assignment = await session.scalar(
            select(MaterialAssignment).where(
                MaterialAssignment.organization_id == actor.organization_id,
                MaterialAssignment.id == data.assignment_id,
            )
        )
        if assignment is None:
            raise HTTPException(404, "Atividade institucional nao encontrada.")
    item = models.ComicEmbeddedAssessmentLink(
        organization_id=actor.organization_id,
        release_id=release_id,
        created_by_user_id=actor.user_id,
        metadata_json=data.metadata,
        **data.model_dump(exclude={"metadata"}),
    )
    session.add(item)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_access",
        action="comic.reader.assessment_link.created",
        entity_type="comic_embedded_assessment_link",
        entity_id=item.id,
        details={
            "release_id": str(release_id),
            "question_bank_item_id": str(data.question_bank_item_id),
            "assignment_id": str(data.assignment_id) if data.assignment_id else None,
        },
    )
    await session.commit()
    return {"id": str(item.id)}


@router.delete("/assessment-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment_link(
    link_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    item = await session.scalar(
        select(models.ComicEmbeddedAssessmentLink).where(
            models.ComicEmbeddedAssessmentLink.organization_id == actor.organization_id,
            models.ComicEmbeddedAssessmentLink.id == link_id,
        )
    )
    if item is None:
        raise HTTPException(404, "Vinculo avaliativo nao encontrado.")
    await session.delete(item)
    await session.commit()


@router.post("/presentations", status_code=status.HTTP_201_CREATED)
async def create_presentation(
    data: PresentationCreate,
    session: SessionDep,
    actor: ActorDep,
):
    require_staff(actor)
    await release_for_actor(session, actor=actor, release_id=data.release_id)
    join_code = generate_join_code()
    while await session.scalar(
        select(models.ComicPresentationSession.id).where(
            models.ComicPresentationSession.organization_id == actor.organization_id,
            models.ComicPresentationSession.join_code == join_code,
        )
    ):
        join_code = generate_join_code()
    item = models.ComicPresentationSession(
        organization_id=actor.organization_id,
        presenter_user_id=actor.user_id,
        join_code=join_code,
        **data.model_dump(),
    )
    session.add(item)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_access",
        action="comic.presentation.created",
        entity_type="comic_presentation_session",
        entity_id=item.id,
        details={"release_id": str(item.release_id), "join_code": item.join_code},
    )
    await session.commit()
    await session.refresh(item)
    return presentation_payload(item)


@router.get("/presentations/{presentation_id}")
async def get_presentation(
    presentation_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    item = await presentation_or_404(session, actor, presentation_id)
    if item.presenter_user_id != actor.user_id and not is_staff(actor):
        audience_id = await session.scalar(
            select(models.ComicPresentationAudience.id).where(
                models.ComicPresentationAudience.organization_id == actor.organization_id,
                models.ComicPresentationAudience.presentation_session_id == item.id,
                models.ComicPresentationAudience.user_id == actor.user_id,
                models.ComicPresentationAudience.status == "JOINED",
            )
        )
        if audience_id is None:
            raise HTTPException(403, "Usuario nao participa desta apresentacao.")
    return presentation_payload(item)


@router.post("/presentations/{presentation_id}/transition")
async def transition_presentation(
    presentation_id: uuid.UUID,
    data: PresentationTransition,
    session: SessionDep,
    actor: ActorDep,
):
    item = await presentation_or_404(session, actor, presentation_id)
    if item.presenter_user_id != actor.user_id and not is_staff(actor):
        raise HTTPException(403, "Somente o apresentador pode controlar a sessao.")
    if data.expected_revision is not None and data.expected_revision != item.revision:
        raise HTTPException(
            409,
            {"code": "PRESENTATION_REVISION_CONFLICT", "current_revision": item.revision},
        )
    if not can_transition_presentation(item.status, data.target_status):
        raise HTTPException(409, f"Transicao invalida: {item.status} -> {data.target_status}")
    previous = item.status
    item.status = data.target_status
    item.revision += 1
    if item.status == "LIVE":
        item.started_at = item.started_at or datetime.now(UTC)
    if item.status in {"ENDED", "CANCELLED"}:
        item.ended_at = datetime.now(UTC)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_reader_access",
        action=f"comic.presentation.{item.status.lower()}",
        entity_type="comic_presentation_session",
        entity_id=item.id,
        details={"previous_status": previous, "revision": item.revision},
    )
    await session.commit()
    return presentation_payload(item)


@router.put("/presentations/{presentation_id}/position")
async def advance_presentation(
    presentation_id: uuid.UUID,
    data: PresentationAdvance,
    session: SessionDep,
    actor: ActorDep,
):
    item = await presentation_or_404(session, actor, presentation_id)
    if item.presenter_user_id != actor.user_id and not is_staff(actor):
        raise HTTPException(403, "Somente o apresentador pode controlar a sessao.")
    if item.status not in {"LIVE", "PAUSED"}:
        raise HTTPException(409, "A apresentacao precisa estar ativa.")
    if data.expected_revision is not None and data.expected_revision != item.revision:
        raise HTTPException(
            409,
            {"code": "PRESENTATION_REVISION_CONFLICT", "current_revision": item.revision},
        )
    item.current_page = data.page_number
    item.current_panel = data.panel_number
    item.reveal_step = data.reveal_step
    item.presenter_note = data.presenter_note
    item.revision += 1
    await session.commit()
    return presentation_payload(item)


@router.post("/presentations/join/{join_code}")
async def join_presentation(
    join_code: str,
    data: PresentationJoin,
    session: SessionDep,
    actor: ActorDep,
):
    item = await session.scalar(
        select(models.ComicPresentationSession).where(
            models.ComicPresentationSession.organization_id == actor.organization_id,
            models.ComicPresentationSession.join_code == join_code.upper(),
        )
    )
    if item is None:
        raise HTTPException(404, "Codigo de apresentacao invalido.")
    if not item.allow_audience_join or item.status not in {"LIVE", "PAUSED"}:
        raise HTTPException(409, "A apresentacao nao esta aberta para entrada.")
    await release_for_actor(session, actor=actor, release_id=item.release_id)
    audience = await session.scalar(
        select(models.ComicPresentationAudience).where(
            models.ComicPresentationAudience.organization_id == actor.organization_id,
            models.ComicPresentationAudience.presentation_session_id == item.id,
            models.ComicPresentationAudience.user_id == actor.user_id,
        )
    )
    if audience is None:
        audience = models.ComicPresentationAudience(
            organization_id=actor.organization_id,
            presentation_session_id=item.id,
            user_id=actor.user_id,
        )
        session.add(audience)
    audience.display_name = data.display_name
    audience.local_preferences = normalize_preferences(data.local_preferences)
    audience.status = "JOINED"
    audience.last_seen_at = datetime.now(UTC)
    await session.commit()
    return presentation_payload(item)


@router.get("/presentations/code/{join_code}")
async def presentation_by_code(
    join_code: str,
    session: SessionDep,
    actor: ActorDep,
):
    item = await session.scalar(
        select(models.ComicPresentationSession).where(
            models.ComicPresentationSession.organization_id == actor.organization_id,
            models.ComicPresentationSession.join_code == join_code.upper(),
        )
    )
    if item is None:
        raise HTTPException(404, "Apresentacao nao encontrada.")
    audience = await session.scalar(
        select(models.ComicPresentationAudience).where(
            models.ComicPresentationAudience.organization_id == actor.organization_id,
            models.ComicPresentationAudience.presentation_session_id == item.id,
            models.ComicPresentationAudience.user_id == actor.user_id,
            models.ComicPresentationAudience.status == "JOINED",
        )
    )
    if audience is None and item.presenter_user_id != actor.user_id and not is_staff(actor):
        raise HTTPException(403, "Entre na apresentacao antes de consultar seu estado.")
    if audience is not None:
        audience.last_seen_at = datetime.now(UTC)
        await session.commit()
    return presentation_payload(item)


@router.post("/presentations/{presentation_id}/leave")
async def leave_presentation(
    presentation_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
):
    audience = await session.scalar(
        select(models.ComicPresentationAudience).where(
            models.ComicPresentationAudience.organization_id == actor.organization_id,
            models.ComicPresentationAudience.presentation_session_id == presentation_id,
            models.ComicPresentationAudience.user_id == actor.user_id,
        )
    )
    if audience is not None:
        audience.status = "LEFT"
        audience.last_seen_at = datetime.now(UTC)
        await session.commit()
    return {"left": True}
