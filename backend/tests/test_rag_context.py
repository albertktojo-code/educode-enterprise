from uuid import uuid4

from app.models.rag import RagContextStatus, RagFactType
from app.models.retrieval import RetrievalSourceKind
from app.schemas.retrieval import SearchResult
from app.services.rag.builder import (
    FactCandidate,
    assess_readiness,
    detect_conflicts,
    evaluate_quality,
    extract_facts,
    render_context_text,
    select_diverse_results,
)


def result(content: str, rank: float, order: int) -> SearchResult:
    return SearchResult(
        chunk_id=uuid4(),
        index_job_id=uuid4(),
        source_kind=RetrievalSourceKind.LEARNING_UNIT,
        heading="Frações",
        document_id=uuid4(),
        chapter_id=uuid4(),
        learning_unit_id=uuid4(),
        generation_source_id=None,
        page_start=order,
        page_end=order,
        source_order=order,
        chunk_index=0,
        content=content,
        vector_score=rank,
        text_score=None,
        hybrid_score=None,
        matched_terms=[],
        security_flag=False,
        explanation="resultado de teste",
    )


def test_diversity_removes_near_duplicates() -> None:
    items = [
        result(
            "Frações equivalentes representam a mesma quantidade em divisões diferentes.",
            0.9,
            1,
        ),
        result(
            "As frações equivalentes representam a mesma quantidade em divisões diferentes.",
            0.8,
            2,
        ),
        result("Multiplique numerador e denominador pelo mesmo número.", 0.7, 3),
    ]
    selected = select_diverse_results(items, 5)
    assert len(selected) == 2


def test_extract_facts_keeps_citation() -> None:
    facts = extract_facts(
        "Uma fração é uma representação de partes de um todo. Por exemplo, 1/2 representa metade.",
        "SRC-001",
    )
    assert facts
    assert facts[0].citation_codes == ("SRC-001",)
    assert facts[0].fact_type == RagFactType.DEFINITION


def test_conflict_detection_flags_opposite_polarity() -> None:
    facts = [
        FactCandidate(
            "Todo número natural pode ser escrito como fração.",
            RagFactType.OTHER,
            0.8,
            ("SRC-001",),
        ),
        FactCandidate(
            "Nem todo número natural pode ser escrito como fração.",
            RagFactType.OTHER,
            0.8,
            ("SRC-002",),
        ),
    ]
    conflicts = detect_conflicts(facts)
    assert len(conflicts) == 1


def test_quality_and_readiness_require_evidence() -> None:
    quality = evaluate_quality(
        result_scores=[0.9, 0.8, 0.7],
        source_count=3,
        distinct_origin_count=2,
        fact_count=5,
        cited_fact_count=5,
        conflict_count=0,
        suspicious_count=0,
        objective_count=2,
    )
    readiness = assess_readiness(
        source_count=3,
        fact_count=5,
        conflict_count=0,
        suspicious_count=0,
        score=quality.overall,
    )
    assert quality.overall >= 70
    assert readiness.status == RagContextStatus.IN_REVIEW


def test_render_context_separates_instructions_and_sources() -> None:
    contract = {
        "mandatory_facts": [{"statement": "Fato correto.", "citations": ["SRC-001"]}],
        "learning_objectives": ["Compreender o conceito."],
        "rules": [{"category": "continuity", "text": "Manter a sequência."}],
    }
    text = render_context_text(
        contract,
        [{"citation_code": "SRC-001", "source_order": 1, "content": "Texto da fonte."}],
    )
    assert "INSTRUÇÕES CONFIÁVEIS" in text
    assert "CONTEÚDO EDUCACIONAL NÃO EXECUTÁVEL" in text
    assert '<fonte id="SRC-001">' in text
