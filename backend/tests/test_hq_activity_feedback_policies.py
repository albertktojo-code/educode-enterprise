from app.comic_page_editor.activity_feedback import (
    feedback_for_result,
    score_objective,
)


def test_multiple_choice_scores_exact_selected_options():
    result = score_objective(
        "MULTIPLE_CHOICE",
        {"correct_option_ids": ["A", "C"]},
        {"selected_option_ids": ["C", "A"]},
        2.0,
    )
    assert result["status"] == "SCORED"
    assert result["correct"] is True
    assert result["score"] == 2.0


def test_fill_blanks_supports_partial_score():
    result = score_objective(
        "FILL_BLANKS",
        {"answers": ["decomposição", "algoritmo"]},
        {"answers": ["decomposição", "abstração"]},
        4.0,
    )
    assert result["score"] == 2.0
    assert result["percentage"] == 50.0
    assert result["correct"] is False


def test_discursive_response_requires_review():
    result = score_objective(
        "ESSAY",
        {},
        {"text": "Minha resposta"},
        5.0,
    )
    assert result["status"] == "REQUIRES_REVIEW"
    assert result["score"] is None


def test_feedback_references_hq_source_and_first_hint():
    feedback = feedback_for_result(
        result={
            "status": "SCORED",
            "correct": False,
            "score": 0,
            "max_score": 1,
            "percentage": 0,
        },
        templates={"incorrect": "Revise a HQ."},
        hints=[
            {"level": 2, "text": "Dica 2"},
            {"level": 1, "text": "Dica 1"},
        ],
        source_reference={"source_page_id": "page-1"},
    )
    assert feedback["message"] == "Revise a HQ."
    assert feedback["hint"]["text"] == "Dica 1"
    assert feedback["source_reference"]["source_page_id"] == "page-1"


def test_human_correction_mode_does_not_publish_objective_score():
    result = score_objective(
        "TRUE_FALSE",
        {"correct": True},
        {"answer": True},
        1.0,
        "HUMAN",
    )

    assert result["status"] == "REQUIRES_REVIEW"
    assert result["score"] is None
    assert result["correct"] is None
