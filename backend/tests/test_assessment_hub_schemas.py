from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.assessment_hub.enums import QuestionType
from app.assessment_hub.schemas import QuestionVersionCreate


def test_choice_requires_options() -> None:
    with pytest.raises(ValidationError):
        QuestionVersionCreate(question_type=QuestionType.SINGLE_CHOICE, statement="Pergunta", options=[])


def test_essay_requires_rubric() -> None:
    with pytest.raises(ValidationError):
        QuestionVersionCreate(question_type=QuestionType.ESSAY, statement="Explique", rubric={})


def test_accessible_question_version() -> None:
    payload = QuestionVersionCreate(
        question_type=QuestionType.SINGLE_CHOICE,
        statement="Qual alternativa?",
        options=[{"id": "A", "text": "Um"}, {"id": "B", "text": "Dois"}],
        correct_answer={"value": "B"},
        accessibility={"plain_language": True, "screen_reader": True},
    )
    assert payload.accessibility["screen_reader"] is True
