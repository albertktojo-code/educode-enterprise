from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.assessment_delivery.access import (
    canonical_target_type,
    target_window_is_open,
)


def test_target_type_normalizes_legacy_class_value() -> None:
    assert canonical_target_type("CLASS") == "CLASSROOM"
    assert canonical_target_type("classroom") == "CLASSROOM"
    assert canonical_target_type("STUDENT") == "STUDENT"


def test_target_window_requires_active_status_and_valid_instant() -> None:
    now = datetime.now(UTC)
    open_target = SimpleNamespace(
        status="ACTIVE",
        available_from=now - timedelta(minutes=1),
        available_until=now + timedelta(minutes=1),
    )
    assert target_window_is_open(open_target, now=now)

    open_target.status = "INACTIVE"
    assert not target_window_is_open(open_target, now=now)

    open_target.status = "ACTIVE"
    open_target.available_from = now + timedelta(minutes=1)
    assert not target_window_is_open(open_target, now=now)
