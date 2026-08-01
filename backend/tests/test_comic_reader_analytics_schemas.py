import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.comic_reader_analytics.schemas import AnalyticsRefreshRequest, ReaderEventCreate


def test_event_normalization():
    event = ReaderEventCreate(
        client_event_id="event-12345678",
        release_id=uuid.uuid4(),
        session_key="session-12345678",
        event_type="page_viewed",
    )
    assert event.event_type == "PAGE_VIEWED"


def test_invalid_event_and_period():
    with pytest.raises(ValidationError):
        ReaderEventCreate(
            client_event_id="event-12345678",
            release_id=uuid.uuid4(),
            session_key="session-12345678",
            event_type="mouse_moved",
        )
    with pytest.raises(ValidationError):
        AnalyticsRefreshRequest(
            period_start=date(2026, 2, 1),
            period_end=date(2026, 1, 1),
        )
