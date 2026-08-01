from app.comic_review_publish.policies import (
    approval_quorum,
    can_transition_release,
    can_transition_review_session,
    evaluate_checklist,
    publication_readiness,
    stable_release_hash,
)


def test_review_session_transition():
    assert can_transition_review_session("DRAFT", "OPEN")
    assert not can_transition_review_session("CLOSED", "OPEN")


def test_release_transition():
    assert can_transition_release("READY", "PUBLISHED")
    assert not can_transition_release("ARCHIVED", "PUBLISHED")


def test_checklist_blocks_required_pending_item():
    result = evaluate_checklist([
        {"required": True, "status": "PASSED"},
        {"required": True, "status": "PENDING"},
        {"required": False, "status": "PENDING"},
    ])
    assert result["is_blocked"] is True
    assert result["failed_required"] == 1


def test_quorum_requires_roles():
    result = approval_quorum(
        [
            {"decision": "APPROVE", "reviewer_role": "PEDAGOGICAL_REVIEWER"},
            {"decision": "APPROVE", "reviewer_role": "ACCESSIBILITY_REVIEWER"},
        ],
        minimum_approvals=2,
        required_roles=["PEDAGOGICAL_REVIEWER", "ACCESSIBILITY_REVIEWER"],
    )
    assert result["quorum_met"] is True


def test_quorum_is_blocked_by_change_request():
    result = approval_quorum(
        [
            {"decision": "APPROVE", "reviewer_role": "EDITOR"},
            {"decision": "REQUEST_CHANGES", "reviewer_role": "BNCC_REVIEWER"},
        ],
        minimum_approvals=1,
    )
    assert result["quorum_met"] is False


def test_publication_readiness():
    ready = publication_readiness(
        workflow_status="APPROVED",
        unresolved_threads=0,
        open_change_requests=0,
        checklist_blocked=False,
        release_hash="abc",
    )
    assert ready["ready"] is True


def test_release_hash_is_deterministic():
    assert stable_release_hash({"b": 2, "a": 1}) == stable_release_hash({"a": 1, "b": 2})
