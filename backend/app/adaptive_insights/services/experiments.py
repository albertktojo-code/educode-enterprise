from __future__ import annotations

import hashlib
from collections import defaultdict
from statistics import mean, median

from ..enums import AssignmentStrategy, MetricDirection
from ..schemas import ExperimentComparisonResult, StrategyComparison


def deterministic_strategy_assignment(
    *, experiment_id: str, participant_id: str, strategy_keys: list[str]
) -> str:
    if not strategy_keys:
        raise ValueError("O experimento precisa possuir estratégias.")
    digest = hashlib.sha256(f"{experiment_id}:{participant_id}".encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(strategy_keys)
    return strategy_keys[index]


def compare_experiment_strategies(
    *,
    experiment_id: str,
    primary_metric: str,
    metric_direction: MetricDirection,
    minimum_sample_per_strategy: int,
    strategy_keys: list[str],
    observations: list[dict],
) -> ExperimentComparisonResult:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in observations:
        if item["strategy_key"] in strategy_keys:
            grouped[item["strategy_key"]].append(item)

    rows: list[StrategyComparison] = []
    for key in strategy_keys:
        values = [float(item["metric_value"]) for item in grouped[key] if item.get("completed", True)]
        total = len(grouped[key])
        completed = len(values)
        rows.append(
            StrategyComparison(
                strategy_key=key,
                sample_size=total,
                mean=round(mean(values), 4) if values else None,
                median=round(median(values), 4) if values else None,
                minimum=round(min(values), 4) if values else None,
                maximum=round(max(values), 4) if values else None,
                completion_rate=round(completed / total, 4) if total else 0,
            )
        )

    sufficient = all(row.sample_size >= minimum_sample_per_strategy for row in rows)
    eligible = [row for row in rows if row.mean is not None]
    if not eligible:
        leader = None
    elif metric_direction == MetricDirection.HIGHER_IS_BETTER:
        leader = max(eligible, key=lambda item: item.mean or float("-inf")).strategy_key
    else:
        leader = min(eligible, key=lambda item: item.mean or float("inf")).strategy_key

    warnings = [
        "Comparação descritiva controlada; não substitui análise estatística inferencial.",
        "Verifique equivalência dos grupos, perdas amostrais e duração do experimento.",
    ]
    if not sufficient:
        warnings.append("Amostra mínima ainda não atingida em todas as estratégias.")

    return ExperimentComparisonResult(
        experiment_id=experiment_id,
        primary_metric=primary_metric,
        metric_direction=metric_direction,
        strategies=rows,
        leading_strategy=leader,
        sufficient_sample=sufficient,
        warnings=warnings,
    )
