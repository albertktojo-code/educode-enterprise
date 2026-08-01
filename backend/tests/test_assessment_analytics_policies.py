from app.assessment_analytics.policies import (
    analyze_distractors,
    calculate_discrimination,
    calculate_facility,
    classify_item_flags,
    cronbach_alpha,
    point_biserial,
    privacy_guard,
    skill_coverage,
    trend_label,
)


def test_facility_and_discrimination():
    assert calculate_facility(8, 10) == 0.8
    assert calculate_discrimination(8, 10, 3, 10) == 0.5


def test_point_biserial_positive():
    value = point_biserial([1, 1, 0, 0], [90, 80, 50, 40])
    assert value is not None and value > 0.8


def test_item_flags():
    flags = classify_item_flags(
        sample_size=12, facility_index=0.15, discrimination_index=-0.1, omission_rate=0.25,
        predicted_difficulty=0.4, observed_difficulty=0.85, minimum_sample=20,
    )
    assert "INSUFFICIENT_SAMPLE" in flags
    assert "VERY_DIFFICULT" in flags
    assert "NEGATIVE_DISCRIMINATION" in flags
    assert "HIGH_OMISSION" in flags
    assert "HARDER_THAN_PREDICTED" in flags


def test_distractor_analysis():
    result = analyze_distractors(["A", "A", "B", "C", "A"], "A", minimum_functioning_rate=0.25)
    by_code = {item["option_code"]: item for item in result}
    assert by_code["A"]["is_correct"] is True
    assert by_code["B"]["non_functioning"] is True


def test_cronbach_alpha_and_privacy():
    alpha = cronbach_alpha([[1, 1, 1], [1, 1, 0], [0, 0, 0], [0, 1, 0]])
    assert alpha is not None
    assert privacy_guard(4, 5)["privacy_suppressed"] is True
    assert privacy_guard(5, 5)["privacy_suppressed"] is False


def test_coverage_and_trend():
    assert skill_coverage(4, 5) == 0.8
    assert trend_label(0.7, 0.6) == "IMPROVING"
    assert trend_label(0.5, 0.6) == "DECLINING"
    assert trend_label(0.61, 0.6) == "STABLE"
