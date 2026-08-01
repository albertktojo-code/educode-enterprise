import pytest
from pydantic import ValidationError

from app.intervention_effectiveness.schemas import (
    CheckpointEvaluationRequest,
    EffectivenessRefreshRequest,
)


def test_refresh_period_and_window_are_validated():
    item = EffectivenessRefreshRequest(
        period_start="2026-01-01",
        period_end="2026-03-31",
        window_code="d30",
    )
    assert item.window_code == "d30"

    with pytest.raises(ValidationError):
        EffectivenessRefreshRequest(
            period_start="2026-03-31",
            period_end="2026-01-01",
        )

    with pytest.raises(ValidationError):
        EffectivenessRefreshRequest(
            period_start="2026-01-01",
            period_end="2026-03-31",
            window_code="d90",
        )


def test_manual_observations_are_percentages():
    item = CheckpointEvaluationRequest(
        force=True,
        observed_progress_percent=80,
        observed_score_percent=75,
    )
    assert item.force is True
    with pytest.raises(ValidationError):
        CheckpointEvaluationRequest(observed_score_percent=101)
