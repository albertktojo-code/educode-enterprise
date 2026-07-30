import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChapter, DocumentPage
from app.models.pedagogy import GenerationProject, GenerationSource, LearningUnit
from app.models.retrieval import (
    DocumentChunk,
    RetrievalIndexJob,
    RetrievalIndexStatus,
    RetrievalSourceKind,
)
from app.services.retrieval.chunker import HierarchicalChunker, PageText
from app.services.retrieval.embeddings import DeterministicHashEmbeddingProvider


class RetrievalIndexingError(ValueError):
    pass


def checksum_text(parts: list[str]) -> str:
    return hashlib.sha256("\n\u241e\n".join(parts).encode("utf-8")).hexdigest()


async def _existing_learning_unit_job(
    session: AsyncSession, organization_id: UUID, learning_unit_id: UUID
) -> RetrievalIndexJob | None:
    result = await session.execute(
        select(RetrievalIndexJob).where(
            RetrievalIndexJob.organization_id == organization_id,
            RetrievalIndexJob.source_kind == RetrievalSourceKind.LEARNING_UNIT,
            RetrievalIndexJob.learning_unit_id == learning_unit_id,
        )
    )
    return result.scalars().one_or_none()


async def _existing_generation_source_job(
    session: AsyncSession, organization_id: UUID, generation_source_id: UUID
) -> RetrievalIndexJob | None:
    result = await session.execute(
        select(RetrievalIndexJob).where(
            RetrievalIndexJob.organization_id == organization_id,
            RetrievalIndexJob.source_kind == RetrievalSourceKind.GENERATION_SOURCE,
            RetrievalIndexJob.generation_source_id == generation_source_id,
        )
    )
    return result.scalars().one_or_none()


async def index_learning_unit(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    learning_unit_id: UUID,
    target_chars: int,
    overlap_chars: int,
    min_chars: int,
) -> RetrievalIndexJob:
    unit = await session.scalar(
        select(LearningUnit).where(
            LearningUnit.id == learning_unit_id,
            LearningUnit.organization_id == organization_id,
        )
    )
    if unit is None:
        raise RetrievalIndexingError("Unidade pedagógica não encontrada")
    if not unit.is_confirmed:
        raise RetrievalIndexingError("Confirme a unidade pedagógica antes da indexação")
    if unit.chapter_id is None:
        raise RetrievalIndexingError("A unidade precisa estar vinculada a um capítulo")

    chapter = await session.scalar(
        select(DocumentChapter).where(DocumentChapter.id == unit.chapter_id)
    )
    if chapter is None or not chapter.is_confirmed:
        raise RetrievalIndexingError("Confirme o capítulo antes da indexação")
    document = await session.scalar(select(Document).where(Document.id == chapter.document_id))
    if document is None or document.organization_id != organization_id:
        raise RetrievalIndexingError("Documento de origem não encontrado")

    start_page = unit.start_page or chapter.start_page
    end_page = unit.end_page or chapter.end_page
    pages = list(
        (
            await session.scalars(
                select(DocumentPage)
                .where(
                    DocumentPage.document_id == document.id,
                    DocumentPage.page_number >= start_page,
                    DocumentPage.page_number <= end_page,
                    DocumentPage.character_count > 0,
                )
                .order_by(DocumentPage.page_number)
            )
        ).all()
    )
    if not pages:
        raise RetrievalIndexingError("Nenhuma página textual válida foi encontrada para a unidade")

    page_inputs = [PageText(page_number=page.page_number, text=page.text) for page in pages]
    checksum = checksum_text([f"{page.page_number}:{page.text}" for page in pages])
    job = await _existing_learning_unit_job(session, organization_id, learning_unit_id)
    if job is None:
        job = RetrievalIndexJob(
            organization_id=organization_id,
            created_by_user_id=user_id,
            source_kind=RetrievalSourceKind.LEARNING_UNIT,
            document_id=document.id,
            chapter_id=chapter.id,
            learning_unit_id=unit.id,
            source_title=f"{chapter.title} — {unit.title}",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    await _run_indexing(
        session,
        job=job,
        page_inputs=page_inputs,
        heading=unit.title,
        checksum=checksum,
        target_chars=target_chars,
        overlap_chars=overlap_chars,
        min_chars=min_chars,
        metadata={
            "document_filename": document.original_filename,
            "chapter_title": chapter.title,
            "learning_unit_title": unit.title,
            "confirmed": True,
        },
    )
    return job


async def index_generation_source(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    generation_source_id: UUID,
    target_chars: int,
    overlap_chars: int,
    min_chars: int,
) -> RetrievalIndexJob:
    source = await session.scalar(
        select(GenerationSource).where(GenerationSource.id == generation_source_id)
    )
    if source is None:
        raise RetrievalIndexingError("Fonte do projeto não encontrada")
    project_org = await session.scalar(
        select(GenerationProject.organization_id).where(
            GenerationProject.id == source.generation_project_id
        )
    )
    if project_org != organization_id:
        raise RetrievalIndexingError("Fonte do projeto não encontrada")

    content_parts = [
        part.strip() for part in (source.content_text, source.instructions) if part and part.strip()
    ]
    if not content_parts:
        raise RetrievalIndexingError("A fonte não possui texto ou instruções indexáveis")
    content = "\n\n".join(content_parts)
    checksum = checksum_text(content_parts)
    job = await _existing_generation_source_job(session, organization_id, generation_source_id)
    if job is None:
        job = RetrievalIndexJob(
            organization_id=organization_id,
            created_by_user_id=user_id,
            source_kind=RetrievalSourceKind.GENERATION_SOURCE,
            generation_source_id=source.id,
            document_id=source.document_id,
            chapter_id=source.chapter_id,
            learning_unit_id=source.learning_unit_id,
            source_title=f"Fonte do projeto — {source.source_type.value}",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

    await _run_indexing(
        session,
        job=job,
        page_inputs=[PageText(page_number=None, text=content)],
        heading=job.source_title,
        checksum=checksum,
        target_chars=target_chars,
        overlap_chars=overlap_chars,
        min_chars=min_chars,
        metadata={
            "generation_project_id": str(source.generation_project_id),
            "generation_source_type": source.source_type.value,
            "priority": source.priority,
            "weight": source.weight,
        },
    )
    return job


async def _run_indexing(
    session: AsyncSession,
    *,
    job: RetrievalIndexJob,
    page_inputs: list[PageText],
    heading: str,
    checksum: str,
    target_chars: int,
    overlap_chars: int,
    min_chars: int,
    metadata: dict[str, object],
) -> None:
    job.status = RetrievalIndexStatus.PROCESSING
    job.progress = 10
    job.current_step = "Preparando conteúdo"
    job.error_message = None
    job.chunk_target_chars = target_chars
    job.chunk_overlap_chars = overlap_chars
    job.chunk_min_chars = min_chars
    await session.flush()

    try:
        chunker = HierarchicalChunker(
            target_chars=target_chars,
            overlap_chars=overlap_chars,
            min_chars=min_chars,
        )
        drafts = chunker.split(page_inputs)
        if not drafts:
            raise RetrievalIndexingError("O conteúdo não produziu chunks válidos")

        job.progress = 45
        job.current_step = "Gerando chunks hierárquicos"
        new_revision = job.indexing_revision + 1
        await session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.index_job_id == job.id, DocumentChunk.is_active.is_(True))
            .values(is_active=False)
        )

        provider = DeterministicHashEmbeddingProvider()
        job.progress = 70
        job.current_step = "Gerando embeddings mock"
        for draft in drafts:
            session.add(
                DocumentChunk(
                    organization_id=job.organization_id,
                    index_job_id=job.id,
                    source_kind=job.source_kind,
                    document_id=job.document_id,
                    chapter_id=job.chapter_id,
                    learning_unit_id=job.learning_unit_id,
                    generation_source_id=job.generation_source_id,
                    heading=heading,
                    page_start=draft.page_start,
                    page_end=draft.page_end,
                    source_order=draft.source_order,
                    chunk_index=draft.chunk_index,
                    content=draft.content,
                    content_checksum=draft.content_checksum,
                    character_count=draft.character_count,
                    token_estimate=draft.token_estimate,
                    embedding=provider.embed_text(draft.content),
                    metadata_json=metadata,
                    security_flag=draft.security_flag,
                    security_notes=draft.security_notes,
                    chunking_version=job.chunking_version,
                    embedding_provider=provider.provider_name,
                    embedding_model=provider.model_name,
                    embedding_dimension=provider.dimension,
                    indexing_revision=new_revision,
                    is_active=True,
                )
            )

        job.progress = 95
        job.current_step = "Salvando índice vetorial e textual"
        job.source_checksum = checksum
        job.indexing_revision = new_revision
        job.active_chunk_count = len(drafts)
        job.security_flag_count = sum(1 for draft in drafts if draft.security_flag)
        job.embedding_provider = provider.provider_name
        job.embedding_model = provider.model_name
        job.embedding_dimension = provider.dimension
        job.status = RetrievalIndexStatus.INDEXED
        job.progress = 100
        job.current_step = "Indexação concluída"
        job.indexed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(job)
    except Exception as exc:
        await session.rollback()
        failed_job = await session.get(RetrievalIndexJob, job.id)
        if failed_job is not None:
            failed_job.status = RetrievalIndexStatus.FAILED
            failed_job.progress = 0
            failed_job.current_step = "Falha na indexação"
            failed_job.error_message = str(exc)
            await session.commit()
        raise


async def refresh_stale_statuses(session: AsyncSession, *, organization_id: UUID) -> None:
    jobs = list(
        (
            await session.scalars(
                select(RetrievalIndexJob).where(
                    RetrievalIndexJob.organization_id == organization_id,
                    RetrievalIndexJob.status.in_(
                        (RetrievalIndexStatus.INDEXED, RetrievalIndexStatus.STALE)
                    ),
                )
            )
        ).all()
    )
    changed = False
    for job in jobs:
        current_checksum: str | None = None
        eligible = True
        if job.source_kind == RetrievalSourceKind.LEARNING_UNIT:
            if job.learning_unit_id is None:
                eligible = False
            else:
                unit = await session.get(LearningUnit, job.learning_unit_id)
                if unit is None or not unit.is_confirmed or unit.chapter_id is None:
                    eligible = False
                else:
                    chapter = await session.get(DocumentChapter, unit.chapter_id)
                    if chapter is None or not chapter.is_confirmed:
                        eligible = False
                    else:
                        start_page = unit.start_page or chapter.start_page
                        end_page = unit.end_page or chapter.end_page
                        pages = list(
                            (
                                await session.scalars(
                                    select(DocumentPage)
                                    .where(
                                        DocumentPage.document_id == chapter.document_id,
                                        DocumentPage.page_number >= start_page,
                                        DocumentPage.page_number <= end_page,
                                        DocumentPage.character_count > 0,
                                    )
                                    .order_by(DocumentPage.page_number)
                                )
                            ).all()
                        )
                        current_checksum = checksum_text(
                            [f"{page.page_number}:{page.text}" for page in pages]
                        )
        else:
            if job.generation_source_id is None:
                eligible = False
            else:
                source = await session.get(GenerationSource, job.generation_source_id)
                if source is None:
                    eligible = False
                else:
                    parts = [
                        part.strip()
                        for part in (source.content_text, source.instructions)
                        if part and part.strip()
                    ]
                    eligible = bool(parts)
                    if parts:
                        current_checksum = checksum_text(parts)

        next_status = (
            RetrievalIndexStatus.INDEXED
            if eligible and current_checksum == job.source_checksum
            else RetrievalIndexStatus.STALE
        )
        if job.status != next_status:
            job.status = next_status
            if next_status == RetrievalIndexStatus.STALE:
                job.current_step = "Fonte alterada; reindexação necessária"
            changed = True
    if changed:
        await session.commit()
