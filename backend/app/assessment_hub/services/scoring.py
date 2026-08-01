from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

from ..enums import CorrectionType, QuestionType
from ..schemas import ScoreResult


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.strip().casefold())


def _first_present(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _normalized_set(value: Any) -> set[str]:
    return {
        normalized
        for item in _as_list(value)
        if (normalized := _normalize_text(item))
    }


def _normalized_sequence(value: Any) -> list[str]:
    return [
        normalized
        for item in _as_list(value)
        if (normalized := _normalize_text(item))
    ]


def _normalized_pairs(value: Any) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        pairs = value.items()
    elif isinstance(value, list):
        pairs = []
        for item in value:
            if not isinstance(item, dict):
                continue
            left = _first_present(item, "left", "key", "source", "id")
            right = _first_present(item, "right", "value", "target", "selected")
            if left is not None and right is not None:
                pairs.append((left, right))
    else:
        pairs = []
    normalized = [
        (_normalize_text(left), _normalize_text(right))
        for left, right in pairs
        if _normalize_text(left) and _normalize_text(right)
    ]
    return sorted(normalized)


def _coerce_question_type(question_type: QuestionType | str) -> QuestionType:
    raw = getattr(question_type, "value", question_type)
    aliases = {
        "SHORT_ANSWER": QuestionType.SHORT_TEXT,
        # These HQ categories describe the pedagogical domain, not an
        # automatically scorable interaction. Existing records therefore fail
        # safely into the canonical human-review flow.
        "COMPUTATIONAL_THINKING": QuestionType.ESSAY,
        "MATHEMATICS": QuestionType.ESSAY,
    }
    if str(raw) in aliases:
        return aliases[str(raw)]
    try:
        return QuestionType(str(raw))
    except ValueError as exc:
        raise ValueError(f"Tipo de questao nao suportado: {raw}") from exc


def _automatic_result(
    *,
    score: float,
    max_score: float,
    correct: bool,
    partial: bool = False,
) -> ScoreResult:
    if partial:
        explanation = "Resposta objetiva parcialmente correta."
    else:
        explanation = (
            "Resposta objetiva correta."
            if correct
            else "Resposta objetiva incorreta."
        )
    return ScoreResult(
        score=round(score, 4),
        max_score=max_score,
        is_correct=correct,
        requires_human_review=False,
        correction_type=CorrectionType.AUTOMATIC.value,
        explanation=explanation,
    )


def apply_review_policy(
    result: ScoreResult,
    correction_mode: str | None,
) -> ScoreResult:
    mode = str(correction_mode or "AUTOMATIC").upper()
    if mode == "AUTOMATIC" or result.requires_human_review:
        return result
    if mode not in {"HUMAN", "RUBRIC", "ASSISTED"}:
        raise ValueError(f"Modo de correcao nao suportado: {correction_mode}")
    return result.model_copy(
        update={
            "score": None,
            "is_correct": None,
            "requires_human_review": True,
            "correction_type": (
                CorrectionType.ASSISTED.value
                if mode == "ASSISTED"
                else CorrectionType.HUMAN.value
            ),
            "explanation": "Resposta aguardando decisao final do professor.",
        }
    )


def feedback_message(
    result: ScoreResult,
    templates: dict[str, Any] | None,
) -> str:
    configured = templates if isinstance(templates, dict) else {}
    if result.requires_human_review:
        key = "requires_review"
    else:
        key = "correct" if result.is_correct else "incorrect"
    message = configured.get(key)
    return str(message) if message else result.explanation


def score_response(
    question_type: QuestionType | str,
    correct_answer: dict[str, Any],
    response: dict[str, Any],
    max_score: float,
) -> ScoreResult:
    if max_score <= 0:
        raise ValueError("max_score deve ser maior que zero.")

    canonical_type = _coerce_question_type(question_type)

    if canonical_type in {QuestionType.ESSAY, QuestionType.PROJECT, QuestionType.MULTIMEDIA}:
        return ScoreResult(
            score=None,
            max_score=max_score,
            is_correct=None,
            requires_human_review=True,
            correction_type=CorrectionType.HUMAN.value,
            explanation="Resposta encaminhada para revisao humana com rubrica.",
        )

    if canonical_type == QuestionType.SINGLE_CHOICE:
        expected = _first_present(
            correct_answer,
            "value",
            "correct_option_id",
        )
        if expected is None:
            expected_values = _as_list(correct_answer.get("correct_option_ids"))
            expected = expected_values[0] if expected_values else None
        received = _first_present(response, "value", "selected_option_id")
        if received is None:
            received_values = _as_list(response.get("selected_option_ids"))
            received = received_values[0] if received_values else None
        correct = (
            expected is not None
            and received is not None
            and _normalize_text(expected) == _normalize_text(received)
        )
    elif canonical_type == QuestionType.MULTIPLE_CHOICE:
        expected = _normalized_set(
            _first_present(
                correct_answer,
                "correct_option_ids",
                "values",
                "value",
            )
        )
        received = _normalized_set(
            _first_present(
                response,
                "selected_option_ids",
                "values",
                "value",
            )
        )
        correct = bool(expected) and expected == received
    elif canonical_type == QuestionType.TRUE_FALSE:
        expected = _first_present(correct_answer, "correct", "value")
        received = _first_present(response, "answer", "value")
        correct = (
            isinstance(expected, bool)
            and isinstance(received, bool)
            and expected is received
        )
    elif canonical_type == QuestionType.NUMERIC:
        expected_raw = correct_answer.get("value")
        received_raw = response.get("value")
        if expected_raw is None:
            raise ValueError("Gabarito numerico sem valor esperado.")
        if received_raw is None:
            correct = False
            return _automatic_result(
                score=0.0,
                max_score=max_score,
                correct=correct,
            )
        expected = float(expected_raw)
        received = float(received_raw)
        tolerance = float(correct_answer.get("tolerance", 0))
        correct = math.isclose(expected, received, abs_tol=max(0.0, tolerance), rel_tol=0)
    elif canonical_type == QuestionType.SHORT_TEXT:
        accepted = _normalized_set(
            _first_present(
                correct_answer,
                "accepted",
                "accepted_answers",
                "value",
                "answer",
            )
        )
        received = _normalize_text(
            _first_present(response, "text", "value", "answer")
        )
        correct = bool(accepted) and bool(received) and received in accepted
    elif canonical_type == QuestionType.MATCHING:
        expected_pairs = _normalized_pairs(correct_answer.get("pairs"))
        received_pairs = _normalized_pairs(response.get("pairs"))
        correct = bool(expected_pairs) and expected_pairs == received_pairs
    elif canonical_type == QuestionType.ORDERING:
        expected_items = _normalized_sequence(
            _first_present(correct_answer, "items", "ordered_ids")
        )
        received_items = _normalized_sequence(
            _first_present(response, "items", "ordered_ids")
        )
        correct = bool(expected_items) and expected_items == received_items
    elif canonical_type == QuestionType.FILL_BLANKS:
        expected_values = _normalized_sequence(correct_answer.get("answers"))
        received_values = _normalized_sequence(response.get("answers"))
        matches = sum(
            left == right
            for left, right in zip(expected_values, received_values, strict=False)
        )
        ratio = matches / len(expected_values) if expected_values else 0.0
        correct = bool(expected_values) and math.isclose(ratio, 1.0)
        return _automatic_result(
            score=max_score * ratio,
            max_score=max_score,
            correct=correct,
            partial=0 < ratio < 1,
        )
    elif canonical_type in {QuestionType.CROSSWORD, QuestionType.WORD_SEARCH}:
        expected_words = _normalized_set(correct_answer.get("words"))
        if not expected_words:
            expected_words = _normalized_set(
                [
                    item.get("answer")
                    for item in _as_list(correct_answer.get("entries"))
                    if isinstance(item, dict)
                ]
            )
        received_words = _normalized_set(response.get("words"))
        ratio = (
            len(expected_words.intersection(received_words)) / len(expected_words)
            if expected_words
            else 0.0
        )
        correct = bool(expected_words) and math.isclose(ratio, 1.0)
        return _automatic_result(
            score=max_score * ratio,
            max_score=max_score,
            correct=correct,
            partial=0 < ratio < 1,
        )
    else:  # pragma: no cover
        raise ValueError(f"Tipo de questao nao suportado: {canonical_type}")

    return _automatic_result(
        score=max_score if correct else 0.0,
        max_score=max_score,
        correct=correct,
    )
