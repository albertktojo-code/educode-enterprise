import uuid

import pytest
from pydantic import ValidationError

from app.assessment_review.schemas import (
    CriterionScoreInput,
    RegradeCreate,
    RubricCriterion,
    RubricVersionCreate,
)


def test_rubric_version_requires_matching_total():
    with pytest.raises(ValidationError):
        RubricVersionCreate(
            maximum_score=10,
            criteria=[RubricCriterion(code="C1", name="Critério", maximum_score=4)],
        )


def test_rubric_version_accepts_unique_criteria():
    item = RubricVersionCreate(
        maximum_score=10,
        criteria=[
            RubricCriterion(code="C1", name="Conceito", maximum_score=6),
            RubricCriterion(code="C2", name="Estratégia", maximum_score=4),
        ],
    )
    assert len(item.criteria) == 2


def test_criterion_score_cannot_exceed_maximum():
    with pytest.raises(ValidationError):
        CriterionScoreInput(
            criterion_code="C1",
            criterion_name="Conceito",
            awarded_score=6,
            maximum_score=5,
        )


def test_regrade_cannot_exceed_maximum():
    with pytest.raises(ValidationError):
        RegradeCreate(
            attempt_id=uuid.uuid4(),
            response_id=uuid.uuid4(),
            proposed_score=11,
            maximum_score=10,
            reason="Correção necessária",
        )
