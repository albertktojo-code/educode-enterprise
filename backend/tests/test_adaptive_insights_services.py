from __future__ import annotations

import uuid

from app.adaptive_insights.enums import MetricDirection, RecommendationAction
from app.adaptive_insights.schemas import (
    InstitutionalPathDashboardInput,
    InstitutionalPathSnapshot,
    InterventionHistoryItem,
    InterventionRecommendationInput,
    MaterialEffectivenessInput,
    MaterialObservation,
    SimulationProfile,
)
from app.adaptive_insights.services import (
    build_institutional_path_dashboard,
    calculate_material_effectiveness,
    compare_experiment_strategies,
    deterministic_strategy_assignment,
    recommend_from_intervention_history,
    simulate_recommendations,
)


def test_recommends_successful_intervention_from_history() -> None:
    payload = InterventionRecommendationInput(
        student_id=uuid.uuid4(),
        learning_node_id=uuid.uuid4(),
        current_mastery=0.45,
        current_confidence=0.72,
        candidate_interventions=["GUIDED_REVIEW", "VISUAL_ACTIVITY"],
        history=[
            InterventionHistoryItem(
                intervention_type="GUIDED_REVIEW",
                mastery_before=0.25,
                mastery_after=0.52,
                completion_rate=1,
                days_ago=3,
            ),
            InterventionHistoryItem(
                intervention_type="GUIDED_REVIEW",
                mastery_before=0.40,
                mastery_after=0.58,
                completion_rate=1,
                days_ago=12,
            ),
        ],
    )
    result = recommend_from_intervention_history(payload)
    assert result.action == RecommendationAction.REPEAT_INTERVENTION
    assert result.recommended_intervention == "GUIDED_REVIEW"
    assert result.requires_teacher_review is True


def test_material_effectiveness_is_descriptive_and_detects_gain() -> None:
    observations = [
        MaterialObservation(
            completed=True,
            score_before=0.30,
            score_after=0.60,
            correct=True,
            attempts=1,
            hints_used=0,
            duration_seconds=120,
        )
        for _ in range(25)
    ]
    result = calculate_material_effectiveness(
        MaterialEffectivenessInput(
            resource_type="ACTIVITY",
            resource_id=uuid.uuid4(),
            observations=observations,
        )
    )
    assert result.sample_size == 25
    assert result.average_gain == 0.3
    assert result.classification == "DESEMPENHO_DESCRITIVO_FORTE"
    assert any("causalidade" in warning for warning in result.warnings)


def test_simulation_does_not_mutate_and_advances_eligible_profile() -> None:
    profile = SimulationProfile(
        student_id=uuid.uuid4(),
        learning_node_id=uuid.uuid4(),
        mastery_score=0.82,
        confidence_score=0.75,
        evidences_count=6,
    )
    result = simulate_recommendations(
        [profile],
        {"advance_mastery": 0.75, "minimum_confidence": 0.55, "minimum_evidences": 3},
    )
    assert result.is_simulation is True
    assert result.decisions[0].action == RecommendationAction.ADVANCE


def test_assignment_is_stable_for_same_participant() -> None:
    experiment = str(uuid.uuid4())
    participant = str(uuid.uuid4())
    first = deterministic_strategy_assignment(
        experiment_id=experiment, participant_id=participant, strategy_keys=["A", "B"]
    )
    second = deterministic_strategy_assignment(
        experiment_id=experiment, participant_id=participant, strategy_keys=["A", "B"]
    )
    assert first == second


def test_experiment_comparison_respects_metric_direction() -> None:
    experiment_id = str(uuid.uuid4())
    result = compare_experiment_strategies(
        experiment_id=experiment_id,
        primary_metric="time_seconds",
        metric_direction=MetricDirection.LOWER_IS_BETTER,
        minimum_sample_per_strategy=2,
        strategy_keys=["A", "B"],
        observations=[
            {"strategy_key": "A", "metric_value": 100, "completed": True},
            {"strategy_key": "A", "metric_value": 120, "completed": True},
            {"strategy_key": "B", "metric_value": 80, "completed": True},
            {"strategy_key": "B", "metric_value": 90, "completed": True},
        ],
    )
    assert result.leading_strategy == "B"
    assert result.sufficient_sample is True


def test_institutional_dashboard_flags_attention_path() -> None:
    path_id = uuid.uuid4()
    result = build_institutional_path_dashboard(
        InstitutionalPathDashboardInput(
            paths=[
                InstitutionalPathSnapshot(
                    path_id=path_id,
                    path_name="Trilha de teste",
                    assigned_students=20,
                    active_students=16,
                    completed_students=2,
                    average_progress=0.30,
                    overdue_reviews=8,
                    interventions_count=14,
                    average_mastery=0.40,
                )
            ]
        )
    )
    assert path_id in result.attention_paths
    assert result.paths_count == 1
