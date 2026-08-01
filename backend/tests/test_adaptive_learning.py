from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.services.adaptive import (
    EvidencePoint,
    build_review_dates,
    calculate_mastery,
    default_materials_for,
    evaluate_advancement,
    recommendation_priority,
    recommendation_type_for,
)


def test_sprint_14_revision_fits_alembic_column():
    assert len("0028_adaptive_learning") <= 32


def test_mastery_requires_evidence_and_is_explainable():
    result = calculate_mastery([], minimum_evidence_count=3)
    assert result.mastery_level == "not_assessed"
    assert result.confidence_score == 0
    assert "Nenhuma evidência" in result.explanation


def test_mastery_uses_recency_difficulty_and_consistency():
    now = datetime(2026, 7, 27, tzinfo=UTC)
    evidence = [
        EvidencePoint(None, 4, 10, calculated_at=now - timedelta(days=120), difficulty="easy"),
        EvidencePoint(None, 6, 10, calculated_at=now - timedelta(days=30), difficulty="medium"),
        EvidencePoint(None, 9, 10, calculated_at=now - timedelta(days=1), difficulty="hard"),
        EvidencePoint(None, 8, 10, calculated_at=now, difficulty="hard"),
    ]
    result = calculate_mastery(evidence, minimum_evidence_count=3, now=now)
    assert 0.70 <= result.mastery_score <= 0.85
    assert result.mastery_level in {"adequate", "developing"}
    assert result.evidence_count == 4
    assert result.confidence_score > 0.6
    assert result.trend == "improving"
    assert "ponderadas" in result.explanation


def test_low_evidence_does_not_overstate_mastery():
    result = calculate_mastery(
        [EvidencePoint(None, 10, 10, calculated_at=datetime.now(UTC))],
        minimum_evidence_count=3,
    )
    assert result.mastery_score == 1.0
    assert result.mastery_level == "insufficient_evidence"
    assert result.confidence_level in {"insufficient", "low"}


def test_recommendation_types_cover_learning_levels():
    base = calculate_mastery(
        [EvidencePoint(None, 2, 10), EvidencePoint(None, 3, 10), EvidencePoint(None, 2, 10)],
        minimum_evidence_count=3,
    )
    assert recommendation_type_for(base) == "recovery"
    assert recommendation_priority(base) == "high"
    assert len(default_materials_for("recovery", "EF06MA07")) == 3


def test_spaced_review_is_more_frequent_for_low_mastery():
    start = datetime(2026, 7, 27, tzinfo=UTC)
    low = build_review_dates(mastery_score=0.35, start=start)
    high = build_review_dates(mastery_score=0.90, start=start)
    assert low[1] < high[1]
    assert len(low) == 3
    assert low[0] > start


def test_advancement_requires_mastery_evidence_and_steps():
    allowed, blockers = evaluate_advancement(
        mastery_score=0.82,
        evidence_count=6,
        target_mastery=0.75,
        minimum_evidence_count=5,
        required_steps_complete=True,
    )
    assert allowed is True
    assert blockers == []

    allowed, blockers = evaluate_advancement(
        mastery_score=0.70,
        evidence_count=2,
        target_mastery=0.75,
        minimum_evidence_count=5,
        required_steps_complete=False,
    )
    assert allowed is False
    assert len(blockers) == 3


def test_sprint_14_settings_version():
    settings = Settings()
    assert tuple(map(int, settings.app_version.split("."))) >= (0, 14, 0)
    assert settings.build_identifier.startswith("sprint-")
