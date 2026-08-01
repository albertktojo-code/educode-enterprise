from datetime import UTC, datetime, timedelta

from app.assessment_review.policies import (
    aggregate_skill_feedback,
    appeal_is_within_deadline,
    calculate_rubric_score,
    canonical_hash,
    determine_review_requirement,
    reconcile_scores,
    validate_rubric_criteria,
)


def criteria():
    return [
        {"code": "C1", "name": "Conceito", "maximum_score": 6, "levels": []},
        {"code": "C2", "name": "Estratégia", "maximum_score": 4, "levels": []},
    ]


def test_rubric_validation_accepts_valid_total():
    assert validate_rubric_criteria(criteria(), 10) == []


def test_rubric_validation_detects_duplicate_and_total():
    invalid = [
        {"code": "C1", "name": "A", "maximum_score": 2},
        {"code": "C1", "name": "B", "maximum_score": 2},
    ]
    errors = validate_rubric_criteria(invalid, 10)
    assert "DUPLICATE_CRITERION_CODE:C1" in errors
    assert "CRITERIA_TOTAL_MUST_MATCH_MAXIMUM_SCORE" in errors


def test_calculate_rubric_score_bounds_values():
    result = calculate_rubric_score(criteria(), {"C1": 7, "C2": 2})
    assert result["total_score"] == 8
    assert result["maximum_score"] == 10
    assert result["percentage"] == 80


def test_review_requirement_for_discursive_item():
    required, reasons = determine_review_requirement(
        question_type="DISCURSIVE", automatic_confidence=0.98
    )
    assert required is True
    assert "QUESTION_TYPE_REQUIRES_HUMAN_REVIEW" in reasons


def test_review_requirement_for_low_confidence():
    required, reasons = determine_review_requirement(
        question_type="MULTIPLE_CHOICE", automatic_confidence=0.4
    )
    assert required is True
    assert "AUTOMATIC_CONFIDENCE_BELOW_THRESHOLD" in reasons


def test_reconcile_scores_requests_moderation_on_large_spread():
    result = reconcile_scores([2, 9], 10)
    assert result["final_score"] == 5.5
    assert result["requires_moderation"] is True


def test_aggregate_skill_feedback():
    result = aggregate_skill_feedback(
        [
            {
                "awarded_score": 4,
                "maximum_score": 5,
                "skill_scores": {"DECOMPOSICAO": {"name": "Decomposição", "weight": 1}},
            },
            {
                "awarded_score": 2,
                "maximum_score": 5,
                "skill_scores": {"DECOMPOSICAO": {"name": "Decomposição", "weight": 1}},
            },
        ]
    )
    assert result[0]["score"] == 0.6
    assert result[0]["classification"] == "ADEQUADO"


def test_appeal_deadline():
    published = datetime.now(UTC) - timedelta(days=3)
    assert appeal_is_within_deadline(published_at=published, appeal_days=5)
    assert not appeal_is_within_deadline(published_at=published, appeal_days=2)


def test_canonical_hash_is_stable():
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})
