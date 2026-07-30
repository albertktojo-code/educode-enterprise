from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.retrieval import (
    DocumentChunk,
    RetrievalFeedback,
    RetrievalFeedbackRating,
    RetrievalIndexJob,
    RetrievalIndexStatus,
)
from app.schemas.retrieval import (
    ChunkRead,
    FeedbackCreate,
    FeedbackRead,
    IndexConfig,
    IndexJobRead,
    RetrievalStats,
    SearchRequest,
    SearchResponse,
)
from app.services.retrieval.indexer import (
    RetrievalIndexingError,
    index_generation_source,
    index_learning_unit,
    refresh_stale_statuses,
)
from app.services.retrieval.search import search_chunks

router = APIRouter(prefix="/retrieval", tags=["Recuperação e RAG"])

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


@router.get("/index-jobs", response_model=list[IndexJobRead])
async def list_index_jobs(
    status: RetrievalIndexStatus | None = None,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[IndexJobRead]:
    query = select(RetrievalIndexJob).where(RetrievalIndexJob.organization_id == org_id(membership))
    if status is not None:
        query = query.where(RetrievalIndexJob.status == status)
    jobs = list((await session.scalars(query.order_by(RetrievalIndexJob.updated_at.desc()))).all())
    return [IndexJobRead.model_validate(job) for job in jobs]


@router.post("/index-learning-unit/{learning_unit_id}", response_model=IndexJobRead)
async def create_learning_unit_index(
    learning_unit_id: UUID,
    config: IndexConfig | None = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> IndexJobRead:
    resolved = config or IndexConfig(
        target_chars=settings.retrieval_chunk_target_chars,
        overlap_chars=settings.retrieval_chunk_overlap_chars,
        min_chars=settings.retrieval_chunk_min_chars,
    )
    try:
        job = await index_learning_unit(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            learning_unit_id=learning_unit_id,
            target_chars=resolved.target_chars,
            overlap_chars=resolved.overlap_chars,
            min_chars=resolved.min_chars,
        )
    except RetrievalIndexingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IndexJobRead.model_validate(job)


@router.post("/index-generation-source/{generation_source_id}", response_model=IndexJobRead)
async def create_generation_source_index(
    generation_source_id: UUID,
    config: IndexConfig | None = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> IndexJobRead:
    resolved = config or IndexConfig(
        target_chars=settings.retrieval_chunk_target_chars,
        overlap_chars=settings.retrieval_chunk_overlap_chars,
        min_chars=settings.retrieval_chunk_min_chars,
    )
    try:
        job = await index_generation_source(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            generation_source_id=generation_source_id,
            target_chars=resolved.target_chars,
            overlap_chars=resolved.overlap_chars,
            min_chars=resolved.min_chars,
        )
    except RetrievalIndexingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IndexJobRead.model_validate(job)


@router.get("/chunks", response_model=list[ChunkRead])
async def list_chunks(
    index_job_id: UUID | None = None,
    learning_unit_id: UUID | None = None,
    active_only: bool = True,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[ChunkRead]:
    query = select(DocumentChunk).where(DocumentChunk.organization_id == org_id(membership))
    if index_job_id is not None:
        query = query.where(DocumentChunk.index_job_id == index_job_id)
    if learning_unit_id is not None:
        query = query.where(DocumentChunk.learning_unit_id == learning_unit_id)
    if active_only:
        query = query.where(DocumentChunk.is_active.is_(True))
    chunks = list(
        (
            await session.scalars(
                query.order_by(DocumentChunk.source_order, DocumentChunk.chunk_index).limit(limit)
            )
        ).all()
    )
    return [ChunkRead.model_validate(chunk) for chunk in chunks]


@router.delete("/index-jobs/{job_id}/chunks", status_code=204)
async def delete_index_chunks(
    job_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    job = await session.scalar(
        select(RetrievalIndexJob).where(
            RetrievalIndexJob.id == job_id,
            RetrievalIndexJob.organization_id == org_id(membership),
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Processo de indexação não encontrado")
    await session.execute(delete(DocumentChunk).where(DocumentChunk.index_job_id == job.id))
    job.status = RetrievalIndexStatus.NOT_INDEXED
    job.progress = 0
    job.current_step = "Índice removido"
    job.active_chunk_count = 0
    job.security_flag_count = 0
    job.source_checksum = None
    await session.commit()
    return Response(status_code=204)


@router.post("/search", response_model=SearchResponse)
async def retrieve(
    data: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> SearchResponse:
    return await search_chunks(session, organization_id=org_id(membership), data=data)


@router.post("/feedback", response_model=FeedbackRead, status_code=201)
async def create_feedback(
    data: FeedbackCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
    user: User = Depends(get_current_user),
) -> FeedbackRead:
    chunk = await session.scalar(
        select(DocumentChunk).where(
            DocumentChunk.id == data.chunk_id,
            DocumentChunk.organization_id == org_id(membership),
        )
    )
    if chunk is None:
        raise HTTPException(status_code=404, detail="Trecho recuperado não encontrado")
    feedback = RetrievalFeedback(
        organization_id=org_id(membership),
        chunk_id=chunk.id,
        user_id=user.id,
        query_text=data.query_text,
        search_mode=data.search_mode.value,
        rating=data.rating,
        notes=data.notes,
    )
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return FeedbackRead.model_validate(feedback)


@router.get("/stats", response_model=RetrievalStats)
async def retrieval_stats(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> RetrievalStats:
    organization_id = org_id(membership)
    await refresh_stale_statuses(session, organization_id=organization_id)

    async def count_jobs(status: RetrievalIndexStatus | None = None) -> int:
        query = select(func.count(RetrievalIndexJob.id)).where(
            RetrievalIndexJob.organization_id == organization_id
        )
        if status is not None:
            query = query.where(RetrievalIndexJob.status == status)
        return int((await session.scalar(query)) or 0)

    async def count_feedback(rating: RetrievalFeedbackRating | None = None) -> int:
        query = select(func.count(RetrievalFeedback.id)).where(
            RetrievalFeedback.organization_id == organization_id
        )
        if rating is not None:
            query = query.where(RetrievalFeedback.rating == rating)
        return int((await session.scalar(query)) or 0)

    active_chunks = int(
        (
            await session.scalar(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.organization_id == organization_id,
                    DocumentChunk.is_active.is_(True),
                )
            )
        )
        or 0
    )
    flagged_chunks = int(
        (
            await session.scalar(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.organization_id == organization_id,
                    DocumentChunk.is_active.is_(True),
                    DocumentChunk.security_flag.is_(True),
                )
            )
        )
        or 0
    )
    return RetrievalStats(
        total_jobs=await count_jobs(),
        indexed_jobs=await count_jobs(RetrievalIndexStatus.INDEXED),
        processing_jobs=await count_jobs(RetrievalIndexStatus.PROCESSING),
        stale_jobs=await count_jobs(RetrievalIndexStatus.STALE),
        failed_jobs=await count_jobs(RetrievalIndexStatus.FAILED),
        active_chunks=active_chunks,
        flagged_chunks=flagged_chunks,
        feedback_total=await count_feedback(),
        relevant_feedback=await count_feedback(RetrievalFeedbackRating.RELEVANT),
        partial_feedback=await count_feedback(RetrievalFeedbackRating.PARTIAL),
        irrelevant_feedback=await count_feedback(RetrievalFeedbackRating.IRRELEVANT),
    )
