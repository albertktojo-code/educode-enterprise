from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.rag import (
    RagConflictStatus,
    RagContext,
    RagContextConflict,
    RagContextFact,
    RagContextRule,
    RagContextSource,
)
from app.schemas.rag import (
    RagConflictUpdate,
    RagContextAssemble,
    RagContextRead,
    RagContextSummary,
    RagContextUpdate,
    RagFactCreate,
    RagFactRead,
    RagFactUpdate,
    RagRuleCreate,
    RagRuleRead,
    RagSourceRead,
    RagSourceUpdate,
    RagTraceabilityItem,
    RagTraceabilityResponse,
)
from app.services.rag.orchestrator import (
    RagAssemblyError,
    approve_context,
    assemble_context,
    get_context,
    refresh_context_artifacts,
)

router = APIRouter(prefix="/rag-contexts", tags=["Contextos RAG"])

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


@router.get("", response_model=list[RagContextSummary])
async def list_contexts(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[RagContextSummary]:
    contexts = list(
        (
            await session.scalars(
                select(RagContext)
                .where(RagContext.organization_id == org_id(membership))
                .order_by(RagContext.updated_at.desc())
            )
        ).all()
    )
    summaries: list[RagContextSummary] = []
    for context in contexts:
        source_count = int(
            (
                await session.scalar(
                    select(func.count(RagContextSource.id)).where(
                        RagContextSource.rag_context_id == context.id,
                        RagContextSource.is_included.is_(True),
                    )
                )
            )
            or 0
        )
        fact_count = int(
            (
                await session.scalar(
                    select(func.count(RagContextFact.id)).where(
                        RagContextFact.rag_context_id == context.id
                    )
                )
            )
            or 0
        )
        conflict_count = int(
            (
                await session.scalar(
                    select(func.count(RagContextConflict.id)).where(
                        RagContextConflict.rag_context_id == context.id,
                        RagContextConflict.status == RagConflictStatus.OPEN,
                    )
                )
            )
            or 0
        )
        summaries.append(
            RagContextSummary(
                id=context.id,
                generation_project_id=context.generation_project_id,
                title=context.title,
                query=context.query,
                search_mode=context.search_mode,
                status=context.status,
                context_version=context.context_version,
                quality_score=context.quality_score,
                source_count=source_count,
                fact_count=fact_count,
                open_conflict_count=conflict_count,
                updated_at=context.updated_at,
            )
        )
    return summaries


@router.post("/assemble", response_model=RagContextRead, status_code=201)
async def create_context(
    data: RagContextAssemble,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> RagContextRead:
    try:
        context = await assemble_context(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            data=data,
        )
    except RagAssemblyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RagContextRead.model_validate(context)


@router.get("/{context_id}", response_model=RagContextRead)
async def read_context(
    context_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> RagContextRead:
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    return RagContextRead.model_validate(context)


@router.patch("/{context_id}", response_model=RagContextRead)
async def update_context(
    context_id: UUID,
    data: RagContextUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> RagContextRead:
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(context, field, value)
    await session.commit()
    refreshed = await get_context(
        session, organization_id=org_id(membership), context_id=context_id
    )
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    return RagContextRead.model_validate(refreshed)


@router.post("/{context_id}/rebuild", response_model=RagContextRead)
async def rebuild_context(
    context_id: UUID,
    data: RagContextAssemble,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> RagContextRead:
    existing = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    if existing.generation_project_id != data.generation_project_id:
        raise HTTPException(status_code=422, detail="O projeto do contexto não pode ser alterado")
    try:
        context = await assemble_context(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            data=data,
            existing_context=existing,
        )
    except RagAssemblyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RagContextRead.model_validate(context)


@router.post("/{context_id}/approve", response_model=RagContextRead)
async def approve(
    context_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> RagContextRead:
    try:
        context = await approve_context(
            session,
            organization_id=org_id(membership),
            context_id=context_id,
            user_id=user.id,
        )
    except RagAssemblyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RagContextRead.model_validate(context)


@router.patch("/{context_id}/sources/{source_id}", response_model=RagSourceRead)
async def update_source(
    context_id: UUID,
    source_id: UUID,
    data: RagSourceUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> RagSourceRead:
    source = await session.scalar(
        select(RagContextSource)
        .join(RagContext, RagContext.id == RagContextSource.rag_context_id)
        .where(
            RagContextSource.id == source_id,
            RagContextSource.rag_context_id == context_id,
            RagContext.organization_id == org_id(membership),
        )
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Fonte do contexto não encontrada")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    refresh_context_artifacts(context)
    await session.commit()
    await session.refresh(source)
    return RagSourceRead.model_validate(source)


@router.post("/{context_id}/facts", response_model=RagFactRead, status_code=201)
async def create_fact(
    context_id: UUID,
    data: RagFactCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> RagFactRead:
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    fact = RagContextFact(
        rag_context_id=context.id,
        statement=data.statement,
        fact_type=data.fact_type,
        confidence=data.confidence,
        citation_codes=data.citation_codes,
        is_mandatory=data.is_mandatory,
        order_index=len(context.facts),
    )
    session.add(fact)
    await session.flush()
    context.facts.append(fact)
    refresh_context_artifacts(context)
    await session.commit()
    await session.refresh(fact)
    return RagFactRead.model_validate(fact)


@router.patch("/{context_id}/facts/{fact_id}", response_model=RagFactRead)
async def update_fact(
    context_id: UUID,
    fact_id: UUID,
    data: RagFactUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> RagFactRead:
    fact = await session.scalar(
        select(RagContextFact)
        .join(RagContext, RagContext.id == RagContextFact.rag_context_id)
        .where(
            RagContextFact.id == fact_id,
            RagContextFact.rag_context_id == context_id,
            RagContext.organization_id == org_id(membership),
        )
    )
    if fact is None:
        raise HTTPException(status_code=404, detail="Fato não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(fact, field, value)
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    refresh_context_artifacts(context)
    await session.commit()
    await session.refresh(fact)
    return RagFactRead.model_validate(fact)


@router.post("/{context_id}/rules", response_model=RagRuleRead, status_code=201)
async def create_rule(
    context_id: UUID,
    data: RagRuleCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> RagRuleRead:
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    rule = RagContextRule(
        rag_context_id=context.id,
        category=data.category,
        rule_text=data.rule_text,
        priority=data.priority,
        order_index=len(context.rules),
    )
    session.add(rule)
    await session.flush()
    context.rules.append(rule)
    refresh_context_artifacts(context)
    await session.commit()
    await session.refresh(rule)
    return RagRuleRead.model_validate(rule)


@router.patch("/{context_id}/conflicts/{conflict_id}", response_model=RagContextRead)
async def resolve_conflict(
    context_id: UUID,
    conflict_id: UUID,
    data: RagConflictUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> RagContextRead:
    conflict = await session.scalar(
        select(RagContextConflict)
        .join(RagContext, RagContext.id == RagContextConflict.rag_context_id)
        .where(
            RagContextConflict.id == conflict_id,
            RagContextConflict.rag_context_id == context_id,
            RagContext.organization_id == org_id(membership),
        )
    )
    if conflict is None:
        raise HTTPException(status_code=404, detail="Conflito não encontrado")
    conflict.status = data.status
    conflict.resolution_notes = data.resolution_notes
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is not None:
        refresh_context_artifacts(context)
    await session.commit()
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    return RagContextRead.model_validate(context)


@router.get("/{context_id}/traceability", response_model=RagTraceabilityResponse)
async def traceability(
    context_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> RagTraceabilityResponse:
    context = await get_context(session, organization_id=org_id(membership), context_id=context_id)
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    source_by_code = {source.citation_code: source for source in context.sources}
    items = [
        RagTraceabilityItem(
            fact_id=fact.id,
            statement=fact.statement,
            citations=[
                RagSourceRead.model_validate(source_by_code[code])
                for code in fact.citation_codes
                if code in source_by_code
            ],
        )
        for fact in context.facts
    ]
    return RagTraceabilityResponse(context_id=context.id, items=items)


@router.delete("/{context_id}", status_code=204)
async def delete_context(
    context_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    context = await session.scalar(
        select(RagContext).where(
            RagContext.id == context_id,
            RagContext.organization_id == org_id(membership),
        )
    )
    if context is None:
        raise HTTPException(status_code=404, detail="Contexto RAG não encontrado")
    await session.delete(context)
    await session.commit()
    return Response(status_code=204)
