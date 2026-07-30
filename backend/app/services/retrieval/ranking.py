import re
from uuid import UUID

WORD_PATTERN = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
STOPWORDS = {
    "a",
    "o",
    "as",
    "os",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "em",
    "para",
    "por",
    "um",
    "uma",
    "que",
    "como",
    "qual",
    "quais",
    "com",
    "sem",
    "no",
    "na",
    "nos",
    "nas",
}


def reciprocal_rank_fusion(
    vector_ids: list[UUID], text_ids: list[UUID], *, k: int = 60
) -> dict[UUID, float]:
    scores: dict[UUID, float] = {}
    for ranking in (vector_ids, text_ids):
        for rank, item_id in enumerate(ranking, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


def matched_terms(query: str, content: str) -> list[str]:
    query_terms = {
        term
        for term in WORD_PATTERN.findall(query.casefold())
        if len(term) > 2 and term not in STOPWORDS
    }
    content_terms = set(WORD_PATTERN.findall(content.casefold()))
    return sorted(query_terms & content_terms)
