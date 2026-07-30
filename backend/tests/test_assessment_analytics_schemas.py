import pytest
from pydantic import ValidationError

from app.assessment_analytics.schemas import AnalyticsRunCreate, ItemAnalysisRequest, ReportDefinitionCreate


def test_item_vectors_must_match():
    with pytest.raises(ValidationError):
        ItemAnalysisRequest(item_scores=[1, 0], total_scores=[10])


def test_item_scores_binary():
    with pytest.raises(ValidationError):
        ItemAnalysisRequest(item_scores=[1, 2], total_scores=[10, 5])


def test_report_requires_sections():
    with pytest.raises(ValidationError):
        ReportDefinitionCreate(code="R1", name="Relatorio", description="Descricao valida", sections=[])


def test_run_period_validation():
    from datetime import UTC, datetime
    from uuid import uuid4
    with pytest.raises(ValidationError):
        AnalyticsRunCreate(
            analytics_model_id=uuid4(), scope_type="ASSESSMENT",
            period_start=datetime(2026, 2, 1, tzinfo=UTC),
            period_end=datetime(2026, 1, 1, tzinfo=UTC),
        )
