import pytest
from pydantic import ValidationError

from app.intervention_orchestration.schemas import (
    InterventionTransition,
    ProposalReview,
)


def test_rejection_requires_explanation():
    with pytest.raises(ValidationError):
        ProposalReview(decision="rejected", review_notes="")
    assert (
        ProposalReview(
            decision="rejected",
            review_notes="Não adequado ao contexto da turma.",
        ).decision
        == "rejected"
    )


def test_cancel_requires_explanation():
    with pytest.raises(ValidationError):
        InterventionTransition(target_status="canceled", notes="")
    assert (
        InterventionTransition(
            target_status="canceled",
            notes="Atividade substituída.",
        ).target_status
        == "canceled"
    )


def test_edited_actions_are_limited_to_known_types():
    with pytest.raises(ValidationError):
        ProposalReview(
            decision="approved",
            edited_materials=[
                {"type": "automatic_grade_change", "title": "Alterar nota"}
            ],
        )
