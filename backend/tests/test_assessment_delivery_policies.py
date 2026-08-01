from datetime import UTC, datetime, timedelta

import pytest

from app.assessment_delivery.policies import (
    calculate_duration_seconds,
    can_navigate,
    classify_integrity,
    deterministic_item_order,
    effective_publication_status,
    monitoring_progress,
    response_checksum,
    validate_transition,
)


def test_effective_publication_status() -> None:
    now = datetime.now(UTC)
    assert effective_publication_status("PUBLISHED", now - timedelta(minutes=1), now + timedelta(minutes=1), now) == "OPEN"
    assert effective_publication_status("PUBLISHED", now + timedelta(minutes=1), now + timedelta(minutes=2), now) == "SCHEDULED"
    assert effective_publication_status("PUBLISHED", now - timedelta(minutes=2), now - timedelta(minutes=1), now) == "CLOSED"


def test_duration_includes_accommodation() -> None:
    assert calculate_duration_seconds(60, extra_time_percent=50, extra_time_minutes=10) == 100 * 60
    assert calculate_duration_seconds(60, target_minutes=40, extra_time_percent=25) == 50 * 60


def test_navigation_rules() -> None:
    assert can_navigate("FREE", 0, 8)
    assert can_navigate("LINEAR", 0, 1)
    assert not can_navigate("LINEAR", 0, 2)
    assert can_navigate("LINEAR_WITH_REVIEW", 4, 1, {1, 2})


def test_integrity_is_descriptive_not_punitive() -> None:
    assert classify_integrity(0, 0) == "NORMAL"
    assert classify_integrity(3, 0) == "ATTENTION"
    assert classify_integrity(8, 0) == "REVIEW"


def test_deterministic_order() -> None:
    items = [{"position": index, "question_version_id": str(index)} for index in range(8)]
    first = deterministic_item_order(items, seed="same", shuffle=True)
    second = deterministic_item_order(items, seed="same", shuffle=True)
    assert first == second
    assert {item["question_version_id"] for item in first} == {str(index) for index in range(8)}


def test_checksum_is_stable() -> None:
    assert response_checksum({"b": 2, "a": 1}) == response_checksum({"a": 1, "b": 2})
    assert len(response_checksum({"answer": "A"})) == 64


def test_session_transition() -> None:
    validate_transition("CREATED", "IN_PROGRESS")
    with pytest.raises(ValueError):
        validate_transition("SUBMITTED", "PAUSED")


def test_monitoring_progress() -> None:
    assert monitoring_progress([0, 4], [10, 10]) == 0.3
