import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.comic_review_publish.schemas import (
    DecisionCreate,
    PublicationTargetCreate,
    ReviewSessionCreate,
    ThreadCreate,
)


def test_review_session_schema():
    payload = ReviewSessionCreate(
        comic_project_id=uuid.uuid4(),
        title="Revisao editorial da HQ",
    )
    assert payload.title.startswith("Revisao")


def test_panel_thread_requires_panel_id():
    with pytest.raises(ValidationError):
        ThreadCreate(anchor_type="PANEL", title="Quadro", body="Ajustar enquadramento")


def test_reject_requires_justification():
    with pytest.raises(ValidationError):
        DecisionCreate(decision="REJECT", reviewer_role="EDITOR", note="")


def test_target_window_validation():
    start = datetime.now(UTC)
    with pytest.raises(ValidationError):
        PublicationTargetCreate(
            target_type="CLASSROOM",
            target_id=uuid.uuid4(),
            availability_from=start,
            availability_until=start - timedelta(days=1),
        )


def test_institutional_library_target_does_not_require_id():
    payload = PublicationTargetCreate(target_type="INSTITUTIONAL_LIBRARY")
    assert payload.target_id is None
