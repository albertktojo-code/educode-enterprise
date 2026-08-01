from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.adaptive_evolution.enums import (
    AdaptationType,
    DifficultyClassification,
    ErrorType,
    HintLevel,
    ProgressionAction,
)
from app.adaptive_evolution.schemas import (
    AccessibleVersionGenerateInput,
    FeedbackAdaptInput,
    HintSelectionInput,
    IndividualDifficultyInput,
    ObservedDifficultyInput,
    ProgressionEvaluationInput,
    SpacedReviewInput,
)
from app.adaptive_evolution.services import (
    adapt_feedback,
    calculate_individual_difficulty,
    calculate_next_review,
    calculate_observed_difficulty,
    evaluate_progression,
    generate_accessible_version,
    select_next_hint,
)


def test_selects_first_unused_published_hint() -> None:
    first = SimpleNamespace(
        id=uuid.uuid4(), level_order=1, version=1, level=HintLevel.ORIENTATION.value, status="PUBLISHED"
    )
    second = SimpleNamespace(
        id=uuid.uuid4(), level_order=2, version=1, level=HintLevel.STRATEGY.value, status="PUBLISHED"
    )
    result = select_next_hint(
        [first, second],
        HintSelectionInput(used_hint_ids=[first.id], incorrect_attempts=1),
    )
    assert result.selected_hint_id == second.id
    assert result.selected_level == HintLevel.STRATEGY
    assert result.exhausted is False


def test_spaced_review_reduces_interval_when_high_hint_used() -> None:
    result = calculate_next_review(
        SpacedReviewInput(
            mastery_score=0.75,
            confidence_score=0.70,
            result_score=0.82,
            hint_level_used=4,
        )
    )
    assert 1 <= result.interval_days <= 8
    assert result.priority >= 1


def test_feedback_uses_decomposition_guidance() -> None:
    result = adapt_feedback(
        FeedbackAdaptInput(
            is_correct=False,
            mastery_level="EM_DESENVOLVIMENTO",
            error_type=ErrorType.DECOMPOSITION,
            attempt_number=2,
            skill_name="Decomposição de problemas",
        )
    )
    assert "partes menores" in result.content
    assert result.next_action == ProgressionAction.REINFORCE


def test_individual_difficulty_limits_large_jump() -> None:
    result = calculate_individual_difficulty(
        IndividualDifficultyInput(
            mastery_score=1,
            confidence_score=1,
            recent_performance=1,
            prerequisite_mastery=1,
            previous_difficulty_score=0.10,
        )
    )
    assert result.difficulty_score <= 0.30
    assert result.requires_teacher_review is True


def test_observed_difficulty_flags_resource_harder_than_predicted() -> None:
    result = calculate_observed_difficulty(
        ObservedDifficultyInput(
            predicted_difficulty=0.25,
            attempts_count=60,
            correct_count=15,
            average_attempts=3.0,
            average_hint_level=3.5,
            abandonment_rate=0.20,
            average_time_seconds=240,
            expected_time_seconds=120,
        )
    )
    assert result.observed_difficulty is not None
    assert result.observed_difficulty > result.predicted_difficulty
    assert result.classification in {
        DifficultyClassification.SLIGHTLY_HARDER,
        DifficultyClassification.MUCH_HARDER,
    }


def test_progression_rule_requires_all_conditions() -> None:
    result = evaluate_progression(
        {
            "minimum_mastery_score": 0.70,
            "minimum_confidence": 0.60,
            "minimum_evidences": 3,
            "required_prerequisites": True,
            "maximum_high_level_hints": 1,
        },
        ProgressionAction.ADVANCE,
        False,
        ProgressionEvaluationInput(
            mastery_score=0.80,
            confidence_score=0.75,
            evidences_count=5,
            prerequisites_met=True,
            high_level_hints_used=0,
            recent_performance=0.85,
        ),
    )
    assert result.matched is True
    assert result.action == ProgressionAction.ADVANCE


def test_accessible_version_preserves_pedagogical_snapshot() -> None:
    source_id = uuid.uuid4()
    result = generate_accessible_version(
        AccessibleVersionGenerateInput(
            source_resource_type="QUESTION",
            source_resource_id=source_id,
            title="Problema com frações",
            content="Identifique as informações e posteriormente efetue o cálculo solicitado.",
            adaptation_type=AdaptationType.PLAIN_LANGUAGE,
            learning_objective="Resolver problemas com frações.",
            expected_answer="1/2",
            assessment_criteria=["Representar a fração", "Justificar a resposta"],
        )
    )
    assert "depois" in result.content.lower()
    assert result.pedagogical_snapshot["expected_answer"] == "1/2"
    assert result.status == "NEEDS_REVIEW"
