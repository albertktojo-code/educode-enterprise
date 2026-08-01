import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.assessment_delivery.schemas import AccommodationCreate, PublicationCreate, PublicationItem, TargetCreate


def base_publication() -> dict:
    now = datetime.now(UTC)
    return {
        "code": "AV-001",
        "title": "Avaliacao de Pensamento Computacional",
        "source_type": "BLUEPRINT",
        "source_id": uuid.uuid4(),
        "item_snapshot": [PublicationItem(question_version_id=uuid.uuid4(), position=0)],
        "starts_at": now,
        "ends_at": now + timedelta(days=1),
    }


def test_publication_window() -> None:
    data = base_publication()
    data["ends_at"] = data["starts_at"] - timedelta(minutes=1)
    with pytest.raises(ValidationError):
        PublicationCreate(**data)


def test_duplicate_positions_are_rejected() -> None:
    data = base_publication()
    data["item_snapshot"] = [
        PublicationItem(question_version_id=uuid.uuid4(), position=0),
        PublicationItem(question_version_id=uuid.uuid4(), position=0),
    ]
    with pytest.raises(ValidationError):
        PublicationCreate(**data)


def test_accessibility_settings_are_explicit() -> None:
    payload = AccommodationCreate(student_id=uuid.uuid4(), extra_time_percent=50, screen_reader_mode=True)
    assert payload.extra_time_percent == 50
    assert payload.screen_reader_mode is True


def test_target_window() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        TargetCreate(
            target_type="CLASSROOM",
            target_id=uuid.uuid4(),
            available_from=now,
            available_until=now - timedelta(minutes=1),
        )
