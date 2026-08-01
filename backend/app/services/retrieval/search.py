from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retrieval import DocumentChunk
from app.schemas.retrieval import (
    OrderedContextItem,
    SearchMode,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.retrieval.embeddings import DeterministicHashEmbeddingProvider
from app.services.retrieval.ranking import matched_terms, reciprocal_rank_fusion


@dataclass(slots=True)
class Candidate:
    chunk: DocumentChunk
    vector_score: float | None = None
    text_score: float | None = None
    hybrid_score: float | None = None


def _base_query(organization_id: UUID, data: SearchRequest) -> Select[tuple[DocumentChunk]]:
    query = select(DocumentChunk).where(
        DocumentChunk.organization_id == organization_id,
        DocumentChunk.is_active.is_(True),
    )
    for field, value in (
        (DocumentChunk.document_id, data.document_id),
        (DocumentChunk.chapter_id, data.chapter_id),
        (DocumentChunk.learning_unit_id, data.learning_unit_id),
        (DocumentChunk.generation_source_id, data.generation_source_id),
        (DocumentChunk.index_job_id, data.index_job_id),
    ):
        if value is not None:
            query = query.where(field == value)
    return query


async def search_chunks(
    session: AsyncSession, *, organization_id: UUID, data: SearchRequest
) -> SearchResponse:
    candidates: dict[UUID, Candidate] = {}
    vector_ids: list[UUID] = []
    text_ids: list[UUID] = []

    if data.mode in (SearchMode.SEMANTIC, SearchMode.HYBRID):
        query_vector = DeterministicHashEmbeddingProvider().embed_text(data.query)
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        vector_query = _base_query(organization_id, data).add_columns(distance).order_by(distance)
        vector_rows = (await session.execute(vector_query.limit(data.candidate_k))).all()
        for chunk, raw_distance in vector_rows:
            score = max(0.0, min(1.0, 1.0 - float(raw_distance or 0.0)))
            candidates.setdefault(chunk.id, Candidate(chunk=chunk)).vector_score = score
            vector_ids.append(chunk.id)

    if data.mode in (SearchMode.TEXT, SearchMode.HYBRID):
        ts_query = func.websearch_to_tsquery("portuguese", data.query)
        rank = func.ts_rank_cd(DocumentChunk.search_vector, ts_query).label("text_rank")
        text_query = (
            _base_query(organization_id, data)
            .add_columns(rank)
            .where(DocumentChunk.search_vector.op("@@")(ts_query))
            .order_by(rank.desc())
        )
        text_rows = (await session.execute(text_query.limit(data.candidate_k))).all()
        max_rank = max((float(row[1] or 0.0) for row in text_rows), default=1.0)
        for chunk, raw_rank in text_rows:
            score = float(raw_rank or 0.0) / max_rank if max_rank else 0.0
            candidates.setdefault(chunk.id, Candidate(chunk=chunk)).text_score = score
            text_ids.append(chunk.id)

    if data.mode == SearchMode.HYBRID:
        fused = reciprocal_rank_fusion(vector_ids, text_ids)
        for chunk_id, score in fused.items():
            candidates[chunk_id].hybrid_score = score
        ranked = sorted(
            candidates.values(), key=lambda item: item.hybrid_score or 0.0, reverse=True
        )
    elif data.mode == SearchMode.SEMANTIC:
        ranked = sorted(
            candidates.values(), key=lambda item: item.vector_score or 0.0, reverse=True
        )
    else:
        ranked = sorted(candidates.values(), key=lambda item: item.text_score or 0.0, reverse=True)

    selected = ranked[: data.top_k]
    results = [_to_result(candidate, data) for candidate in selected]
    ordered = sorted(selected, key=lambda item: (item.chunk.source_order, item.chunk.chunk_index))
    ordered_context = [
        OrderedContextItem(
            chunk_id=item.chunk.id,
            citation_label=_citation_label(item.chunk),
            source_order=item.chunk.source_order,
            content=item.chunk.content,
        )
        for item in ordered
    ]
    return SearchResponse(
        query=data.query,
        mode=data.mode,
        total_candidates=len(candidates),
        results=results,
        ordered_context=ordered_context,
    )


def _citation_label(chunk: DocumentChunk) -> str:
    if chunk.page_start is None:
        return f"Fonte textual · trecho {chunk.chunk_index + 1}"
    if chunk.page_start == chunk.page_end:
        return f"p. {chunk.page_start}"
    return f"pp. {chunk.page_start}–{chunk.page_end}"


def _to_result(candidate: Candidate, data: SearchRequest) -> SearchResult:
    chunk = candidate.chunk
    terms = matched_terms(data.query, chunk.content)
    reasons: list[str] = []
    if candidate.vector_score is not None:
        reasons.append(f"similaridade vetorial {candidate.vector_score:.3f}")
    if candidate.text_score is not None:
        reasons.append(f"relevância textual {candidate.text_score:.3f}")
    if terms:
        reasons.append("termos encontrados: " + ", ".join(terms[:8]))
    if chunk.security_flag:
        reasons.append("fonte marcada como não executável por segurança")
    return SearchResult(
        chunk_id=chunk.id,
        index_job_id=chunk.index_job_id,
        source_kind=chunk.source_kind,
        heading=chunk.heading,
        document_id=chunk.document_id,
        chapter_id=chunk.chapter_id,
        learning_unit_id=chunk.learning_unit_id,
        generation_source_id=chunk.generation_source_id,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        source_order=chunk.source_order,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        vector_score=candidate.vector_score,
        text_score=candidate.text_score,
        hybrid_score=candidate.hybrid_score,
        matched_terms=terms,
        security_flag=chunk.security_flag,
        explanation="; ".join(reasons) or "Resultado recuperado pelos filtros selecionados.",
    )
