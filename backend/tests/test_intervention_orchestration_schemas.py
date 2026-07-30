import pytest
from pydantic import ValidationError

from app.intervention_orchestration.schemas import (
    InterventionTransition,
    ProposalCreate,
    ProposalReview,
)


def test_proposal_defaults_preserve_human_review():
    item = ProposalCreate()
    assert item.use_ai is True
    assert item.due_days == 7
    assert item.target_mastery == 0.75


def test_review_decision_is_normalized():
    item = ProposalReview(decision="APPROVED")
    assert item.decision == "approved"
    with pytest.raises(ValidationError):
        ProposalReview(decision="automatic_apply")


def test_transition_is_restricted():
    assert InterventionTransition(target_status="ACTIVE").target_status == "active"
    with pytest.raises(ValidationError):
        InterventionTransition(target_status="approved")
