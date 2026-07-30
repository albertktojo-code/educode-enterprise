from datetime import UTC, datetime

from app.intervention_effectiveness.policies import (
    WINDOWS,
    classify_followup,
    dimension_key,
    metric_from_intervention,
    privacy_guard,
    safe_rate,
    scheduled_for,
)


def test_longitudinal_windows_are_fixed_and_ordered():
    assert WINDOWS == (
        ("immediate", 0),
        ("d7", 7),
        ("d15", 15),
        ("d30", 30),
        ("d60", 60),
    )
    completed = datetime(2026, 1, 1, tzinfo=UTC)
    assert scheduled_for(completed, 30).day == 31


def test_followup_classifies_improvement_and_retention():
    result = classify_followup(
        baseline_value=0.40,
        observed_value=0.72,
        immediate_value=0.75,
        target_value=0.70,
        minimum_improvement=0.03,
        retention_tolerance=0.05,
    )
    assert result["comparable"] is True
    assert result["improved"] is True
    assert result["target_met"] is True
    assert result["retained"] is True
    assert result["outcome"] == "retained"


def test_followup_does_not_invent_evidence():
    result = classify_followup(
        baseline_value=0.40,
        observed_value=None,
        immediate_value=0.70,
        target_value=0.75,
        minimum_improvement=0.03,
        retention_tolerance=0.05,
    )
    assert result["comparable"] is False
    assert result["delta"] is None
    assert result["outcome"] == "insufficient_evidence"


def test_metric_uses_same_dimension_as_intervention():
    metric, baseline, target = metric_from_intervention(
        {
            "metric": "assessment_score_percent",
            "before": 0.45,
            "target_mastery": 0.75,
        },
        {
            "assessment_score_percent": 45,
            "progress_percent": 80,
        },
    )
    assert metric == "assessment_score_percent"
    assert baseline == 0.45
    assert target == 0.75


def test_privacy_and_dimension_helpers():
    assert privacy_guard(4, 5) is True
    assert privacy_guard(5, 5) is False
    assert safe_rate(3, 5) == 0.6
    assert safe_rate(0, 0) is None
    assert dimension_key("adaptive_path", True) == "adaptive_path:true"
