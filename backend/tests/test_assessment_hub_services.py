from __future__ import annotations

import uuid

from app.assessment_hub.enums import QuestionType
from app.assessment_hub.schemas import (
    AssemblySimulationInput,
    CandidateQuestion,
    DimensionScoreInput,
    DimensionSummaryInput,
    ItemAnalyticsInput,
    ItemObservation,
)
from app.assessment_hub.services import (
    apply_review_policy,
    assemble_assessment,
    calculate_item_analytics,
    feedback_message,
    score_response,
    summarize_dimensions,
)


def test_single_choice_scoring() -> None:
    result = score_response(QuestionType.SINGLE_CHOICE, {"value": "B"}, {"value": "B"}, 2.0)
    assert result.score == 2.0
    assert result.is_correct is True
    assert result.requires_human_review is False


def test_hq_multiple_choice_payload_does_not_accept_wrong_or_empty_answer() -> None:
    correct = {"correct_option_ids": ["A"]}

    wrong = score_response(
        QuestionType.MULTIPLE_CHOICE,
        correct,
        {"selected_option_ids": ["B"]},
        1.0,
    )
    empty = score_response(
        QuestionType.MULTIPLE_CHOICE,
        correct,
        {},
        1.0,
    )

    assert wrong.score == 0.0
    assert wrong.is_correct is False
    assert empty.score == 0.0
    assert empty.is_correct is False


def test_hq_true_false_payload_does_not_coerce_missing_values() -> None:
    wrong = score_response(
        QuestionType.TRUE_FALSE,
        {"correct": True},
        {"answer": False},
        1.0,
    )
    missing = score_response(
        QuestionType.TRUE_FALSE,
        {"correct": False},
        {},
        1.0,
    )

    assert wrong.is_correct is False
    assert missing.is_correct is False


def test_hq_fill_blanks_supports_partial_score() -> None:
    result = score_response(
        QuestionType.FILL_BLANKS,
        {"answers": ["decomposicao", "algoritmo"]},
        {"answers": ["decomposicao", "abstracao"]},
        4.0,
    )

    assert result.score == 2.0
    assert result.is_correct is False
    assert result.explanation == "Resposta objetiva parcialmente correta."


def test_hq_matching_and_ordering_use_structured_payloads() -> None:
    matching = score_response(
        QuestionType.MATCHING,
        {"pairs": [{"left": "A", "right": "1"}, {"left": "B", "right": "2"}]},
        {"pairs": [{"left": "B", "right": "2"}, {"left": "A", "right": "1"}]},
        2.0,
    )
    ordering = score_response(
        QuestionType.ORDERING,
        {"items": ["primeiro", "segundo"]},
        {"items": ["segundo", "primeiro"]},
        2.0,
    )

    assert matching.score == 2.0
    assert matching.is_correct is True
    assert ordering.score == 0.0
    assert ordering.is_correct is False


def test_existing_hq_pedagogical_categories_fail_safe_to_human_review() -> None:
    result = score_response(
        "COMPUTATIONAL_THINKING",
        {},
        {"text": "Minha estrategia"},
        3.0,
    )

    assert result.score is None
    assert result.requires_human_review is True


def test_teacher_review_policy_prevents_automatic_final_score() -> None:
    automatic = score_response(
        QuestionType.TRUE_FALSE,
        {"correct": True},
        {"answer": True},
        2.0,
    )

    reviewed = apply_review_policy(automatic, "ASSISTED")

    assert reviewed.score is None
    assert reviewed.is_correct is None
    assert reviewed.requires_human_review is True
    assert reviewed.correction_type == "ASSISTED"


def test_feedback_message_uses_approved_template() -> None:
    result = score_response(
        QuestionType.TRUE_FALSE,
        {"correct": True},
        {"answer": False},
        1.0,
    )

    assert feedback_message(
        result,
        {"incorrect": "Revise a pagina indicada da HQ."},
    ) == "Revise a pagina indicada da HQ."


def test_essay_requires_review() -> None:
    result = score_response(QuestionType.ESSAY, {}, {"value": "texto"}, 5.0)
    assert result.score is None
    assert result.requires_human_review is True


def test_numeric_tolerance() -> None:
    result = score_response(
        QuestionType.NUMERIC,
        {"value": 10, "tolerance": 0.1},
        {"value": 10.05},
        1.0,
    )
    assert result.is_correct is True


def test_deterministic_assembly() -> None:
    candidates = [
        CandidateQuestion(
            question_version_id=uuid.uuid4(),
            question_type=QuestionType.SINGLE_CHOICE,
            difficulty=0.4,
            skill_codes=["EF06MA07"],
        ),
        CandidateQuestion(
            question_version_id=uuid.uuid4(),
            question_type=QuestionType.NUMERIC,
            difficulty=0.6,
            skill_codes=["ABSTRACAO"],
        ),
        CandidateQuestion(
            question_version_id=uuid.uuid4(),
            question_type=QuestionType.TRUE_FALSE,
            difficulty=0.5,
            skill_codes=["EF06MA07", "ABSTRACAO"],
        ),
    ]
    payload = AssemblySimulationInput(
        target_count=2,
        target_average_difficulty=0.5,
        required_skill_codes=["EF06MA07", "ABSTRACAO"],
        candidates=candidates,
        seed=15,
    )
    first = assemble_assessment(payload)
    second = assemble_assessment(payload)
    assert first.selected_question_ids == second.selected_question_ids
    assert first.missing_skill_codes == []


def test_item_analytics() -> None:
    payload = ItemAnalyticsInput(
        predicted_difficulty=0.3,
        observations=[
            ItemObservation(
                correct=index < 4,
                score_ratio=1 if index < 4 else 0,
                attempts=1,
                hints=0,
                duration_seconds=30,
            )
            for index in range(10)
        ],
    )
    result = calculate_item_analytics(payload)
    assert result.sample_size == 10
    assert result.observed_difficulty == 0.6
    assert result.classification == "MAIS_DIFICIL_QUE_PREVISTO"


def test_dimension_summary() -> None:
    result = summarize_dimensions(
        DimensionSummaryInput(
            dimensions=[
                DimensionScoreInput(
                    dimension_code="D1",
                    earned_score=8,
                    maximum_score=10,
                    weight=2,
                ),
                DimensionScoreInput(
                    dimension_code="D2",
                    earned_score=5,
                    maximum_score=10,
                    weight=1,
                ),
            ]
        )
    )
    assert result.weighted_percentage == 70.0
    assert result.scoring_version == "15.0.0"
