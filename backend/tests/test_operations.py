from uuid import uuid4

from app.services.operations import (
    build_idempotency_key,
    is_transient_error,
    queue_for_job_type,
    retry_delay_seconds,
)


def test_queue_routing_is_deterministic():
    assert queue_for_job_type("ai_generation") == "ai"
    assert queue_for_job_type("document_processing") == "documents"
    assert queue_for_job_type("analytics_refresh") == "analytics"
    assert queue_for_job_type("other") == "default"


def test_idempotency_key_is_stable_and_org_scoped():
    organization_id = uuid4()
    entity_id = uuid4()
    first = build_idempotency_key(
        organization_id=organization_id,
        job_type="ai_generation",
        entity_id=entity_id,
        input_snapshot={"topic": "frações", "quantity": 4},
    )
    second = build_idempotency_key(
        organization_id=organization_id,
        job_type="ai_generation",
        entity_id=entity_id,
        input_snapshot={"quantity": 4, "topic": "frações"},
    )
    assert first == second
    assert first.startswith("ai_generation:")


def test_retry_schedule_is_bounded():
    assert retry_delay_seconds(0) == 0
    assert retry_delay_seconds(1) == 30
    assert retry_delay_seconds(2) == 120
    assert retry_delay_seconds(3) == 600
    assert retry_delay_seconds(99) == 3600


def test_transient_errors_are_classified():
    assert is_transient_error(TimeoutError("provider timeout")) is True
    assert is_transient_error(RuntimeError("503 temporarily unavailable")) is True
    assert is_transient_error(ValueError("schema inválido")) is False
