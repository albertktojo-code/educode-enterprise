from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.assessment_review import models
from app.assessment_review.services import (
    ensure_review_assignment,
    optional_uuid,
)


class FakeSession:
    def __init__(self, scalar_results: list[Any]) -> None:
        self.scalar_results = scalar_results
        self.added: list[Any] = []

    async def scalar(self, _statement: Any) -> Any:
        return self.scalar_results.pop(0)

    def add(self, entity: Any) -> None:
        self.added.append(entity)

    async def flush(self) -> None:
        assignment = next(
            (
                entity
                for entity in self.added
                if isinstance(entity, models.ReviewAssignment)
            ),
            None,
        )
        if assignment is not None and assignment.id is None:
            assignment.id = uuid.uuid4()


def test_optional_uuid_rejects_invalid_metadata() -> None:
    assert optional_uuid(None) is None
    assert optional_uuid("not-an-id") is None


@pytest.mark.asyncio
async def test_review_assignment_is_created_with_audit_event() -> None:
    session = FakeSession([None])
    organization_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    response_id = uuid.uuid4()
    question_version_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()
    student_id = uuid.uuid4()

    assignment = await ensure_review_assignment(
        session,  # type: ignore[arg-type]
        organization_id=organization_id,
        attempt_id=attempt_id,
        response_id=response_id,
        question_version_id=question_version_id,
        reviewer_user_id=reviewer_id,
        assigned_by_user_id=reviewer_id,
        initiated_by_user_id=student_id,
        context_snapshot={"source": "ASSESSMENT_DELIVERY_SUBMISSION"},
    )

    assert assignment.organization_id == organization_id
    assert assignment.response_id == response_id
    assert assignment.reviewer_user_id == reviewer_id
    assert assignment.status == "PENDING"
    assert assignment.rubric_version_id is None
    assert any(
        isinstance(entity, models.ReviewAuditEvent)
        and entity.actor_user_id == student_id
        for entity in session.added
    )


@pytest.mark.asyncio
async def test_review_assignment_is_idempotent_for_first_round() -> None:
    existing = models.ReviewAssignment(
        organization_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        response_id=uuid.uuid4(),
        question_version_id=uuid.uuid4(),
        reviewer_user_id=uuid.uuid4(),
        assigned_by_user_id=uuid.uuid4(),
        review_round=1,
        review_mode="SINGLE",
        status="PENDING",
        priority=50,
        context_snapshot={},
    )
    session = FakeSession([existing])

    assignment = await ensure_review_assignment(
        session,  # type: ignore[arg-type]
        organization_id=existing.organization_id,
        attempt_id=existing.attempt_id,
        response_id=existing.response_id,
        question_version_id=existing.question_version_id,
        reviewer_user_id=existing.reviewer_user_id,
        assigned_by_user_id=existing.assigned_by_user_id,
        initiated_by_user_id=uuid.uuid4(),
    )

    assert assignment is existing
    assert session.added == []
