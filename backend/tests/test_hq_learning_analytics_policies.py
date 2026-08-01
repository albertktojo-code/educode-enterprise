import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.comic_page_editor.learning_analytics import (
    build_alerts,
    reading_answer_correlation,
    safe_rate,
    scored_summary,
)
from app.comic_page_editor.schemas import HQLearningAnalyticsGenerate


def test_safe_rate_handles_zero():
    assert safe_rate(2, 0) == 0.0


def test_correlation_describes_difference():
    result = reading_answer_correlation(
        reviewed_correct=72,
        reviewed_total=100,
        not_reviewed_correct=43,
        not_reviewed_total=100,
    )
    assert result["difference_points"] == 29.0
    assert "melhor desempenho" in result["interpretation"]


def test_alerts_flag_low_completion_and_skill():
    alerts = build_alerts(
        {
            "students": 10,
            "completion_rate": 40,
            "privacy_suppressed": False,
        },
        [
            {
                "skill_type": "COMPUTATIONAL_THINKING",
                "skill_code": "ABSTRACTION",
                "accuracy": 38,
                "evidence_count": 5,
            }
        ],
        [],
    )
    assert {item["code"] for item in alerts} >= {
        "LOW_COMPLETION",
        "SKILL_DIFFICULTY",
    }


def test_scoring_ignores_pending_human_review():
    result = scored_summary(
        [
            {
                "score": 1,
                "maximum_score": 1,
                "is_correct": True,
                "requires_human_review": False,
            },
            {
                "score": None,
                "maximum_score": 2,
                "is_correct": None,
                "requires_human_review": True,
            },
        ]
    )
    assert result["accuracy"] == 100.0
    assert result["scored_response_count"] == 1
    assert result["pending_review_count"] == 1


def test_small_group_does_not_materialize_alerts():
    alerts = build_alerts(
        {
            "students": 2,
            "completion_rate": 0,
            "privacy_suppressed": True,
        },
        [],
        [],
    )
    assert alerts == []


def test_correlation_requires_both_comparison_groups():
    result = reading_answer_correlation(
        reviewed_correct=0,
        reviewed_total=0,
        not_reviewed_correct=2,
        not_reviewed_total=3,
    )
    assert result["difference_points"] is None
    assert result["sufficient_data"] is False
    assert "insuficientes" in result["interpretation"]


def test_analytics_scope_and_period_are_validated():
    with pytest.raises(ValidationError):
        HQLearningAnalyticsGenerate(scope_type="STUDENT")
    with pytest.raises(ValidationError):
        HQLearningAnalyticsGenerate(
            scope_type="PUBLICATION",
            scope_id=uuid.uuid4(),
        )
    with pytest.raises(ValidationError):
        HQLearningAnalyticsGenerate(
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC) - timedelta(days=1),
        )
