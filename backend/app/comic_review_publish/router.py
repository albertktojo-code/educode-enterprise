from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from . import models
from .compat import ActorContext, get_project_session, resolve_actor_context
from .policies import (
    approval_quorum,
    can_transition_release,
    can_transition_review_session,
    evaluate_checklist,
    publication_readiness,
    stable_release_hash,
    summarize_review,
)
from app.services.consolidated_audit import append_domain_audit
from .repositories import list_releases, list_review_sessions, list_threads
from .services import review_readiness
from .schemas import (
    AssignmentCreate,
    ChangeRequestCreate,
    ChecklistCreate,
    CommentCreate,
    DecisionCreate,
    PublicationTargetCreate,
    ReleaseCreate,
    ReviewSessionCreate,
    ReviewSessionRead,
    ThreadCreate,
    ThreadResolution,
    WorkflowCreate,
)

router = APIRouter(prefix="/comic-review-publish", tags=["comic-review-publish"])
SessionDep = Annotated[Any, Depends(get_project_session)]
ActorDep = Annotated[ActorContext, Depends(resolve_actor_context)]

ADMIN_ROLES = {"PLATFORM_ADMIN", "ORG_ADMIN", "ADMIN"}
EDITOR_ROLES = ADMIN_ROLES | {"TEACHER", "COORDINATOR", "PEDAGOGICAL_COORDINATOR", "EDITOR"}
REVIEW_ROLES = EDITOR_ROLES | {"REVIEWER", "ACCESSIBILITY_REVIEWER", "BNCC_REVIEWER"}
PUBLISH_ROLES = ADMIN_ROLES | {"COORDINATOR", "PEDAGOGICAL_COORDINATOR", "EDITOR"}


def require_role(actor: ActorContext, allowed: set[str]) -> None:
    roles = {str(item).upper() for item in actor.roles}
    if not roles.intersection(allowed):
        raise HTTPException(403, "Permissao insuficiente para revisao ou publicacao da HQ.")


async def get_session_or_404(session: Any, organization_id: uuid.UUID, item_id: uuid.UUID):
    item = await session.scalar(
        select(models.ComicEditorialReviewSession).where(
            models.ComicEditorialReviewSession.organization_id == organization_id,
            models.ComicEditorialReviewSession.id == item_id,
        )
    )
    if not item:
        raise HTTPException(404, "Sessao de revisao nao encontrada.")
    return item


async def get_thread_or_404(session: Any, organization_id: uuid.UUID, item_id: uuid.UUID):
    item = await session.scalar(
        select(models.ComicEditorialThread).where(
            models.ComicEditorialThread.organization_id == organization_id,
            models.ComicEditorialThread.id == item_id,
        )
    )
    if not item:
        raise HTTPException(404, "Discussao de revisao nao encontrada.")
    return item


async def get_workflow_or_404(session: Any, organization_id: uuid.UUID, item_id: uuid.UUID):
    item = await session.scalar(
        select(models.ComicEditorialWorkflow).where(
            models.ComicEditorialWorkflow.organization_id == organization_id,
            models.ComicEditorialWorkflow.id == item_id,
        )
    )
    if not item:
        raise HTTPException(404, "Fluxo editorial nao encontrado.")
    return item


async def get_release_or_404(session: Any, organization_id: uuid.UUID, item_id: uuid.UUID):
    item = await session.scalar(
        select(models.ComicEditorialRelease).where(
            models.ComicEditorialRelease.organization_id == organization_id,
            models.ComicEditorialRelease.id == item_id,
        )
    )
    if not item:
        raise HTTPException(404, "Release da HQ nao encontrada.")
    return item


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "sprint": "16.4", "module": "comic-review-publish"}


@router.post("/review-sessions", response_model=ReviewSessionRead, status_code=status.HTTP_201_CREATED)
async def create_review_session(payload: ReviewSessionCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, EDITOR_ROLES)
    item = models.ComicEditorialReviewSession(
        organization_id=actor.organization_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/review-sessions", response_model=list[ReviewSessionRead])
async def review_sessions(session: SessionDep, actor: ActorDep, comic_project_id: uuid.UUID | None = None):
    require_role(actor, REVIEW_ROLES)
    return await list_review_sessions(session, actor.organization_id, comic_project_id)


@router.post("/review-sessions/{session_id}/transition")
async def transition_review_session(
    session_id: uuid.UUID, target_status: str, session: SessionDep, actor: ActorDep
):
    require_role(actor, EDITOR_ROLES)
    item = await get_session_or_404(session, actor.organization_id, session_id)
    target_status = target_status.upper()
    if not can_transition_review_session(item.status, target_status):
        raise HTTPException(409, f"Transicao invalida: {item.status} -> {target_status}")
    item.status = target_status
    if target_status == "OPEN":
        item.opened_at = datetime.now(UTC)
    if target_status in {"CLOSED", "CANCELLED"}:
        item.closed_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(item.id), "status": item.status}


@router.post("/review-sessions/{session_id}/assignments", status_code=status.HTTP_201_CREATED)
async def create_assignment(session_id: uuid.UUID, payload: AssignmentCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, EDITOR_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    item = models.ComicEditorialAssignment(
        organization_id=actor.organization_id,
        review_session_id=session_id,
        assigned_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "status": item.status, "reviewer_role": item.reviewer_role}


@router.post("/review-sessions/{session_id}/threads", status_code=status.HTTP_201_CREATED)
async def create_thread(session_id: uuid.UUID, payload: ThreadCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    data = payload.model_dump(exclude={"body", "metadata"})
    item = models.ComicEditorialThread(
        organization_id=actor.organization_id,
        review_session_id=session_id,
        created_by_user_id=actor.user_id,
        metadata_json=payload.metadata,
        **data,
    )
    session.add(item)
    await session.flush()
    session.add(models.ComicEditorialComment(
        organization_id=actor.organization_id,
        thread_id=item.id,
        body=payload.body,
        created_by_user_id=actor.user_id,
    ))
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "status": item.status, "anchor_type": item.anchor_type}


@router.get("/review-sessions/{session_id}/threads")
async def threads(session_id: uuid.UUID, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    result = await list_threads(session, actor.organization_id, session_id)
    return [
        {
            "id": str(item.id), "title": item.title, "status": item.status,
            "anchor_type": item.anchor_type, "page_id": str(item.page_id) if item.page_id else None,
            "panel_id": str(item.panel_id) if item.panel_id else None,
        }
        for item in result
    ]


@router.post("/threads/{thread_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(thread_id: uuid.UUID, payload: CommentCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    thread = await get_thread_or_404(session, actor.organization_id, thread_id)
    item = models.ComicEditorialComment(
        organization_id=actor.organization_id,
        thread_id=thread.id,
        body=payload.body,
        mentions=[str(item) for item in payload.mentions],
        attachments=payload.attachments,
        created_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "thread_id": str(thread.id)}


@router.post("/threads/{thread_id}/resolve")
async def resolve_thread(thread_id: uuid.UUID, payload: ThreadResolution, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    item = await get_thread_or_404(session, actor.organization_id, thread_id)
    item.status = "RESOLVED"
    item.resolution_note = payload.note
    item.resolved_by_user_id = actor.user_id
    item.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(item.id), "status": item.status}


@router.post("/threads/{thread_id}/reopen")
async def reopen_thread(thread_id: uuid.UUID, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    item = await get_thread_or_404(session, actor.organization_id, thread_id)
    item.status = "REOPENED"
    item.resolved_by_user_id = None
    item.resolved_at = None
    await session.commit()
    return {"id": str(item.id), "status": item.status}


@router.post("/review-sessions/{session_id}/change-requests", status_code=status.HTTP_201_CREATED)
async def create_change_request(
    session_id: uuid.UUID, payload: ChangeRequestCreate, session: SessionDep, actor: ActorDep
):
    require_role(actor, REVIEW_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    item = models.ComicEditorialChangeRequest(
        organization_id=actor.organization_id,
        review_session_id=session_id,
        requested_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "status": item.status}


@router.post("/change-requests/{request_id}/complete")
async def complete_change_request(
    request_id: uuid.UUID, resolution_snapshot: dict[str, Any], session: SessionDep, actor: ActorDep
):
    require_role(actor, EDITOR_ROLES)
    item = await session.scalar(
        select(models.ComicEditorialChangeRequest).where(
            models.ComicEditorialChangeRequest.organization_id == actor.organization_id,
            models.ComicEditorialChangeRequest.id == request_id,
        )
    )
    if not item:
        raise HTTPException(404, "Solicitacao de alteracao nao encontrada.")
    item.status = "IMPLEMENTED"
    item.resolution_snapshot = resolution_snapshot
    item.resolved_by_user_id = actor.user_id
    item.resolved_at = datetime.now(UTC)
    await session.commit()
    return {"id": str(item.id), "status": item.status}


@router.post("/review-sessions/{session_id}/checklists", status_code=status.HTTP_201_CREATED)
async def create_checklist(session_id: uuid.UUID, payload: ChecklistCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, EDITOR_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    evaluation = evaluate_checklist([item.model_dump() for item in payload.items])
    checklist = models.ComicEditorialChecklist(
        organization_id=actor.organization_id,
        review_session_id=session_id,
        name=payload.name,
        version=payload.version,
        completion_percent=evaluation["completion_percent"],
        is_blocked=evaluation["is_blocked"],
        created_by_user_id=actor.user_id,
    )
    session.add(checklist)
    await session.flush()
    for payload_item in payload.items:
        session.add(models.ComicEditorialCheckItem(
            organization_id=actor.organization_id,
            checklist_id=checklist.id,
            **payload_item.model_dump(),
        ))
    await session.commit()
    return {"id": str(checklist.id), **evaluation}


@router.post("/review-sessions/{session_id}/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(session_id: uuid.UUID, payload: WorkflowCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, EDITOR_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    item = models.ComicEditorialWorkflow(
        organization_id=actor.organization_id,
        review_session_id=session_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "status": item.status}


@router.post("/workflows/{workflow_id}/decisions", status_code=status.HTTP_201_CREATED)
async def create_decision(workflow_id: uuid.UUID, payload: DecisionCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    workflow = await get_workflow_or_404(session, actor.organization_id, workflow_id)
    review_session = await get_session_or_404(session, actor.organization_id, workflow.review_session_id)
    snapshot_hash = stable_release_hash({
        "review_session_id": str(review_session.id),
        "comic_version_id": str(review_session.comic_version_id) if review_session.comic_version_id else None,
    })
    existing = await session.scalar(
        select(models.ComicEditorialDecision).where(
            models.ComicEditorialDecision.organization_id == actor.organization_id,
            models.ComicEditorialDecision.workflow_id == workflow_id,
            models.ComicEditorialDecision.reviewer_user_id == actor.user_id,
        )
    )
    if existing:
        existing.decision = payload.decision
        existing.reviewer_role = payload.reviewer_role
        existing.note = payload.note
        existing.snapshot_hash = snapshot_hash
        item = existing
    else:
        item = models.ComicEditorialDecision(
            organization_id=actor.organization_id,
            workflow_id=workflow_id,
            reviewer_user_id=actor.user_id,
            snapshot_hash=snapshot_hash,
            **payload.model_dump(),
        )
        session.add(item)
    await session.flush()
    result = await session.execute(
        select(models.ComicEditorialDecision).where(
            models.ComicEditorialDecision.organization_id == actor.organization_id,
            models.ComicEditorialDecision.workflow_id == workflow_id,
        )
    )
    decisions = [
        {"decision": entry.decision, "reviewer_role": entry.reviewer_role}
        for entry in result.scalars().all()
    ]
    quorum = approval_quorum(
        decisions,
        minimum_approvals=workflow.minimum_approvals,
        required_roles=workflow.required_roles,
    )
    workflow.status = "APPROVED" if quorum["quorum_met"] else (
        "CHANGES_REQUESTED" if quorum["blocking_decisions"] else "IN_REVIEW"
    )
    await session.commit()
    return {"id": str(item.id), "workflow_status": workflow.status, **quorum}


@router.post("/releases", status_code=status.HTTP_201_CREATED)
async def create_release(payload: ReleaseCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, PUBLISH_ROLES)
    review_session = await get_session_or_404(session, actor.organization_id, payload.review_session_id)
    if review_session.comic_project_id != payload.comic_project_id:
        raise HTTPException(409, "A sessao de revisao nao pertence a esta HQ.")
    readiness = await review_readiness(
        session,
        organization_id=actor.organization_id,
        review_session_id=review_session.id,
        snapshot=payload.snapshot,
    )
    if not readiness["ready"]:
        raise HTTPException(
            409,
            {
                "code": "EDITORIAL_RELEASE_BLOCKED",
                "message": "A HQ ainda possui pendencias editoriais.",
                **readiness,
            },
        )
    release_number = (
        await session.scalar(
            select(func.coalesce(func.max(models.ComicEditorialRelease.release_number), 0)).where(
                models.ComicEditorialRelease.organization_id == actor.organization_id,
                models.ComicEditorialRelease.comic_project_id == payload.comic_project_id,
            )
        )
    ) + 1
    item = models.ComicEditorialRelease(
        organization_id=actor.organization_id,
        release_number=release_number,
        release_hash=stable_release_hash(payload.snapshot),
        created_by_user_id=actor.user_id,
        metadata_json=payload.metadata,
        **payload.model_dump(exclude={"metadata"}),
    )
    session.add(item)
    await session.flush()
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_review_publish",
        action="comic.release.created",
        entity_type="comic_editorial_release",
        entity_id=item.id,
        details={
            "review_session_id": str(review_session.id),
            "release_number": item.release_number,
            "release_hash": item.release_hash,
        },
    )
    await session.commit()
    await session.refresh(item)
    return {
        "id": str(item.id), "release_number": item.release_number,
        "release_hash": item.release_hash, "status": item.status,
        "readiness": readiness,
    }


@router.get("/projects/{project_id}/releases")
async def project_releases(project_id: uuid.UUID, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    result = await list_releases(session, actor.organization_id, project_id)
    return [
        {
            "id": str(item.id), "release_number": item.release_number,
            "release_name": item.release_name, "status": item.status,
            "release_hash": item.release_hash,
        }
        for item in result
    ]


@router.post("/releases/{release_id}/targets", status_code=status.HTTP_201_CREATED)
async def add_target(release_id: uuid.UUID, payload: PublicationTargetCreate, session: SessionDep, actor: ActorDep):
    require_role(actor, PUBLISH_ROLES)
    await get_release_or_404(session, actor.organization_id, release_id)
    item = models.ComicEditorialReleaseTarget(
        organization_id=actor.organization_id,
        release_id=release_id,
        created_by_user_id=actor.user_id,
        **payload.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "target_type": item.target_type, "status": item.status}


@router.post("/releases/{release_id}/transition")
async def transition_release(release_id: uuid.UUID, target_status: str, session: SessionDep, actor: ActorDep):
    require_role(actor, PUBLISH_ROLES)
    release = await get_release_or_404(session, actor.organization_id, release_id)
    target_status = target_status.upper()
    if not can_transition_release(release.status, target_status):
        raise HTTPException(409, f"Transicao invalida: {release.status} -> {target_status}")
    if target_status in {"READY", "SCHEDULED", "PUBLISHED"}:
        readiness = await review_readiness(
            session,
            organization_id=actor.organization_id,
            review_session_id=release.review_session_id,
            snapshot=release.snapshot,
        )
        if not readiness["ready"]:
            raise HTTPException(409, {"code": "EDITORIAL_RELEASE_BLOCKED", **readiness})
    if target_status == "PUBLISHED":
        target_count = int(
            await session.scalar(
                select(func.count(models.ComicEditorialReleaseTarget.id)).where(
                    models.ComicEditorialReleaseTarget.organization_id == actor.organization_id,
                    models.ComicEditorialReleaseTarget.release_id == release.id,
                    models.ComicEditorialReleaseTarget.status == "ACTIVE",
                )
            )
            or 0
        )
        if target_count == 0:
            raise HTTPException(409, "Adicione pelo menos um destino antes de publicar.")
    previous_status = release.status
    release.status = target_status
    if target_status == "PUBLISHED":
        release.published_at = datetime.now(UTC)
    if target_status == "WITHDRAWN":
        release.withdrawn_at = datetime.now(UTC)
    await append_domain_audit(
        session,
        actor=actor,
        module_name="comic_review_publish",
        action=f"comic.release.{target_status.lower()}",
        entity_type="comic_editorial_release",
        entity_id=release.id,
        details={"previous_status": previous_status, "target_status": target_status},
    )
    await session.commit()
    return {"id": str(release.id), "status": release.status}


@router.get("/review-sessions/{session_id}/summary")
async def review_summary(session_id: uuid.UUID, session: SessionDep, actor: ActorDep):
    require_role(actor, REVIEW_ROLES)
    await get_session_or_404(session, actor.organization_id, session_id)
    thread_result = await session.execute(
        select(models.ComicEditorialThread).where(
            models.ComicEditorialThread.organization_id == actor.organization_id,
            models.ComicEditorialThread.review_session_id == session_id,
        )
    )
    workflow = await session.scalar(
        select(models.ComicEditorialWorkflow).where(
            models.ComicEditorialWorkflow.organization_id == actor.organization_id,
            models.ComicEditorialWorkflow.review_session_id == session_id,
        )
    )
    decisions = []
    if workflow:
        decision_result = await session.execute(
            select(models.ComicEditorialDecision).where(
                models.ComicEditorialDecision.organization_id == actor.organization_id,
                models.ComicEditorialDecision.workflow_id == workflow.id,
            )
        )
        decisions = [
            {"decision": item.decision, "reviewer_role": item.reviewer_role}
            for item in decision_result.scalars().all()
        ]
    threads_data = [{"status": item.status} for item in thread_result.scalars().all()]
    summary = summarize_review(decisions, threads_data)
    readiness = await review_readiness(
        session,
        organization_id=actor.organization_id,
        review_session_id=session_id,
        snapshot={
            "review_session_id": str(session_id),
            "comic_version_id": None,
        },
    )
    return {**summary, "publication_readiness": readiness}
