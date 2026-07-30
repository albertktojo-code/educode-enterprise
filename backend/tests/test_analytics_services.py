from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.models.delivery import AttemptStatus
from app.services.analytics import (
    answer_label,
    calculate_discrimination,
    confidence_score,
    difficulty_label,
    mastery_level,
    select_attempts,
    trend_direction,
)


def _attempt(assignment_id, student_id, number, percentage, status=AttemptStatus.GRADED):
    return SimpleNamespace(
        assignment_id=assignment_id,
        student_id=student_id,
        attempt_number=number,
        percentage=percentage,
        status=status,
        started_at=datetime(2026, 7, number, tzinfo=UTC),
    )


def test_select_attempts_best_first_latest_and_all() -> None:
    assignment_id = uuid4()
    student_id = uuid4()
    attempts = [
        _attempt(assignment_id, student_id, 1, 40),
        _attempt(assignment_id, student_id, 2, 80),
        _attempt(assignment_id, student_id, 3, 65),
    ]
    assert select_attempts(attempts, "first")[0].attempt_number == 1
    assert select_attempts(attempts, "latest")[0].attempt_number == 3
    assert select_attempts(attempts, "best")[0].attempt_number == 2
    assert len(select_attempts(attempts, "all")) == 3


def test_select_attempts_ignores_incomplete() -> None:
    assignment_id = uuid4()
    student_id = uuid4()
    attempts = [
        _attempt(assignment_id, student_id, 1, 99, AttemptStatus.IN_PROGRESS),
        _attempt(assignment_id, student_id, 2, 70),
    ]
    selected = select_attempts(attempts, "best")
    assert len(selected) == 1
    assert selected[0].attempt_number == 2


def test_mastery_and_confidence_are_explainable() -> None:
    assert mastery_level(0, 0) == "not_evaluated"
    assert mastery_level(39, 3) == "initial"
    assert mastery_level(59, 3) == "developing"
    assert mastery_level(84, 3) == "adequate"
    assert mastery_level(90, 3) == "advanced"
    assert confidence_score(1) == 20
    assert confidence_score(5) == 100
    assert confidence_score(12) == 100


def test_difficulty_labels() -> None:
    assert difficulty_label(None) == "sem dados"
    assert difficulty_label(0.81) == "fácil"
    assert difficulty_label(0.4) == "moderada"
    assert difficulty_label(0.39) == "difícil"


def test_discrimination_requires_data_and_compares_extremes() -> None:
    assert calculate_discrimination([(50, True)] * 5) is None
    rows = [
        (10, False), (20, False), (30, False), (40, False),
        (60, True), (70, True), (80, True), (90, True),
    ]
    assert calculate_discrimination(rows) == 1.0


def test_answer_labels_and_trend_direction() -> None:
    assert answer_label({}) == "Sem resposta"
    assert answer_label({"selected_option": "B"}) == "B"
    assert answer_label({"selected": ["A", "C"]}) == "A | C"
    assert trend_direction([50]) == "stable"
    assert trend_direction([50, 56]) == "up"
    assert trend_direction([70, 60]) == "down"
