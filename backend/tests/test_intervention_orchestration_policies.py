from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.intervention_orchestration.policies import (
    build_plan,
    can_transition,
    canonical_intervention_type,
    choose_intervention_type,
    choose_recommendation_type,
    confidence_from_evidence,
    intervention_priority,
    score_proxy,
)
from app.intervention_orchestration.router import require_teacher
from app.models.analytics import InterventionStatus, InterventionType


def test_intervention_type_uses_reading_and_assessment_evidence():
    assert (
        choose_intervention_type(
            alert_type="comic_reading_low_progress",
            progress_percent=20,
            score_percent=None,
            accessibility_used=False,
        )
        == InterventionType.REINFORCEMENT
    )
    assert (
        choose_intervention_type(
            alert_type="assessment_low_score",
            progress_percent=80,
            score_percent=35,
            accessibility_used=False,
        )
        == InterventionType.ADAPTED_ACTIVITY
    )


def test_plan_reuses_canonical_resources():
    plan = build_plan(
        release_id="release",
        page_number=2,
        panel_number=3,
        assignment_id="assignment",
        accessible_version_id="accessible",
        teacher_note="Acompanhar",
    )
    assert [item["type"] for item in plan] == [
        "comic_reread",
        "accessible_resource",
        "assignment",
        "teacher_feedback",
    ]


def test_post_hq_signals_cover_adaptive_taxonomy():
    common = {
        "alert_type": "hq_post_learning",
        "progress_percent": 100,
        "score_percent": None,
        "accessibility_used": False,
    }
    assert (
        choose_recommendation_type(
            **common,
            rule_code="HQ_POST:HARD_ACTIVITY:item",
            observed_accuracy=20,
        )
        == "simplified_activity"
    )
    assert (
        choose_recommendation_type(
            **common,
            rule_code="HQ_POST:SKILL_DIFFICULTY:BNCC:EF01",
            observed_accuracy=42,
        )
        == "consolidation"
    )
    assert (
        choose_recommendation_type(
            **common,
            rule_code="HQ_POST:MASTERY_OPPORTUNITY:BNCC:EF01",
            observed_accuracy=95,
        )
        == "advanced_challenge"
    )
    assert (
        canonical_intervention_type("equivalent_activity")
        == InterventionType.ADAPTED_ACTIVITY
    )


def test_activity_variant_is_only_a_teacher_reviewed_proposal():
    plan = build_plan(
        release_id="release",
        page_number=2,
        panel_number=None,
        assignment_id=None,
        accessible_version_id=None,
        teacher_note="",
        recommendation_type="equivalent_activity",
        activity_id="activity",
        question_version_id="question-version",
    )
    variant = next(item for item in plan if item["type"] == "activity_variant")
    assert variant["requires_teacher_selection"] is True
    assert variant["question_version_id"] == "question-version"


def test_intervention_rbac_normalizes_roles_and_rejects_students():
    require_teacher(SimpleNamespace(roles=["teacher"]))
    with pytest.raises(HTTPException) as error:
        require_teacher(SimpleNamespace(roles=["student"]))
    assert error.value.status_code == 403


def test_confidence_priority_and_score_proxy():
    assert confidence_from_evidence(3, True) > confidence_from_evidence(1, False)
    assert intervention_priority("priority", 0.2) == "high"
    assert score_proxy({"assessment_score_percent": 75}) == 0.75
    assert score_proxy({"progress_percent": 40}) == 0.4


def test_workflow_transitions_require_completion_endpoint():
    assert can_transition(
        InterventionStatus.PLANNED,
        InterventionStatus.ACTIVE,
    )
    assert can_transition(
        InterventionStatus.ACTIVE,
        InterventionStatus.COMPLETED,
    )
    assert not can_transition(
        InterventionStatus.COMPLETED,
        InterventionStatus.ACTIVE,
    )
