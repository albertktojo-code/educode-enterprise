from app.intervention_orchestration.policies import (
    comparable_outcome,
    safe_student_actions,
)


def test_assessment_is_compared_only_with_assessment():
    result = comparable_outcome(
        {
            "assessment_score_percent": 40,
            "progress_percent": 80,
        },
        {
            "assessment_score_percent": 70,
            "progress_percent": 90,
        },
        target_mastery=0.75,
        minimum_improvement=0.03,
    )
    assert result["metric"] == "assessment_score_percent"
    assert result["gain"] == 0.3
    assert result["improved"] is True
    assert result["target_met"] is False


def test_missing_comparable_metric_does_not_create_false_gain():
    result = comparable_outcome(
        {"assessment_score_percent": 45},
        {"progress_percent": 90},
        target_mastery=0.75,
        minimum_improvement=0.03,
    )
    assert result["comparable"] is False
    assert result["gain"] == 0.0
    assert result["outcome"] == "insufficient_evidence"


def test_target_can_be_met_without_large_gain():
    result = comparable_outcome(
        {"progress_percent": 74},
        {"progress_percent": 76},
        target_mastery=0.75,
        minimum_improvement=0.03,
    )
    assert result["improved"] is False
    assert result["target_met"] is True


def test_student_actions_remove_internal_teacher_note():
    actions = safe_student_actions(
        {
            "actions": [
                {
                    "type": "teacher_feedback",
                    "title": "Feedback",
                    "note": "Anotação interna",
                    "completion_required": False,
                }
            ]
        }
    )
    assert actions == [
        {
            "type": "teacher_feedback",
            "title": "Feedback",
            "completion_required": False,
        }
    ]
