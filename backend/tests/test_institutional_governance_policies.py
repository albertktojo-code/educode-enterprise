from app.institutional_governance.policies import (
    compare_documents,
    documentation_completeness,
    fairness_from_cohorts,
    required_approvals,
    required_stages,
    review_summary,
    threshold_breaches,
)


def test_risk_tiers_define_review_stages_and_quorum():
    assert required_stages("low", {}) == {"technical"}
    assert required_stages("moderate", {}) == {
        "technical",
        "pedagogical",
    }
    assert "privacy" in required_stages("high", {})
    assert "ethics" in required_stages("critical", {})
    assert required_approvals("high", {}, 2) == 3
    assert required_approvals(
        "moderate",
        {"minimum_approvals": 4},
        2,
    ) == 4


def test_review_summary_requires_stages_and_no_blockers():
    summary = review_summary(
        risk_tier="moderate",
        approval_policy={},
        reviews=[
            {"review_stage": "technical", "decision": "approved"},
            {"review_stage": "pedagogical", "decision": "approved"},
        ],
        institutional_default=2,
    )
    assert summary["ready"] is True
    assert summary["missing_stages"] == []

    blocked = review_summary(
        risk_tier="moderate",
        approval_policy={},
        reviews=[
            {"review_stage": "technical", "decision": "approved"},
            {
                "review_stage": "pedagogical",
                "decision": "changes_requested",
            },
        ],
        institutional_default=2,
    )
    assert blocked["ready"] is False
    assert blocked["blocked"] is True


def test_thresholds_generate_explainable_breaches():
    rows = threshold_breaches(
        {
            "quality_score": 0.60,
            "safety_score": 0.95,
            "effectiveness_score": 0.80,
            "fairness_score": 0.70,
            "error_rate": 0.20,
            "recurrence_rate": 0.10,
            "drift_score": 0.05,
        },
        {},
    )
    assert {item["metric"] for item in rows} == {
        "quality_score",
        "fairness_score",
        "error_rate",
    }


def test_fairness_is_contextual_disparity_not_identity_inference():
    score, disparity = fairness_from_cohorts([0.80, 0.60, 0.70])
    assert score == 0.8
    assert disparity == 0.2
    assert fairness_from_cohorts([0.8]) == (None, None)


def test_documentation_and_version_comparison():
    complete = {
        "summary": "Resumo",
        "data_sources": ["fonte"],
        "decision_logic": "regras",
        "human_oversight": "revisão",
        "known_limitations": ["limite"],
        "validation_evidence": "teste",
        "rollback_plan": "rollback",
    }
    assert documentation_completeness(complete) == 1.0
    diff = compare_documents(
        {"summary": "v1", "limit": 1},
        {"summary": "v2", "limit": 1},
    )
    assert diff["changed_keys"] == ["summary"]
    assert diff["left_hash"] != diff["right_hash"]
