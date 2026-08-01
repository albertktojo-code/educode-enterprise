import uuid

import pytest
from pydantic import ValidationError

from app.institutional_governance.schemas import (
    GovernanceAssetCreate,
    GovernanceReviewCreate,
)


def test_asset_requires_exactly_one_matching_reference():
    item = GovernanceAssetCreate(
        code="adaptive-risk",
        name="Modelo adaptativo",
        asset_type="adaptive_model",
        adaptive_model_version_id=uuid.uuid4(),
    )
    assert item.risk_tier == "moderate"

    with pytest.raises(ValidationError):
        GovernanceAssetCreate(
            code="invalid",
            name="Referências conflitantes",
            asset_type="ai_model",
            ai_model_id=uuid.uuid4(),
            prompt_template_id=uuid.uuid4(),
        )

    with pytest.raises(ValidationError):
        GovernanceAssetCreate(
            code="mismatch",
            name="Tipo incompatível",
            asset_type="prompt_template",
            ai_model_id=uuid.uuid4(),
        )


def test_review_rejection_requires_explanation():
    approved = GovernanceReviewCreate(
        review_stage="technical",
        decision="approved",
    )
    assert approved.decision == "approved"

    with pytest.raises(ValidationError):
        GovernanceReviewCreate(
            review_stage="privacy",
            decision="changes_requested",
            comments="",
        )

    with pytest.raises(ValidationError):
        GovernanceReviewCreate(
            review_stage="unknown",
            decision="approved",
        )
