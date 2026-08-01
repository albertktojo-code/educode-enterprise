from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any

from scipy import stats

from app.services.statistics_engine import execute


def configuration_checksum(
    dataset_checksum: str, analysis_type: str, parameters: dict[str, Any]
) -> str:
    payload = {
        "dataset_checksum": dataset_checksum,
        "analysis_type": analysis_type,
        "parameters": parameters,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def result_signature(result: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _numeric_keys(parameters: dict[str, Any]) -> list[str]:
    keys = [
        str(parameters.get("x_key", "pre")),
        str(parameters.get("y_key", "post")),
        str(parameters.get("value_key", "score")),
    ]
    keys.extend(str(value) for value in parameters.get("item_keys", []))
    keys.extend(str(value) for value in parameters.get("repeated_keys", []))
    return list(dict.fromkeys(keys))


def _complete_cases(
    rows: list[dict[str, Any]], parameters: dict[str, Any]
) -> list[dict[str, Any]]:
    required = [key for key in _numeric_keys(parameters) if any(key in row for row in rows)]
    return [row for row in rows if all(row.get(key) is not None for key in required)]


def _without_iqr_outliers(
    rows: list[dict[str, Any]], parameters: dict[str, Any]
) -> list[dict[str, Any]]:
    preferred = str(parameters.get("value_key", "score"))
    fallback = str(parameters.get("y_key", "post"))
    value_key = preferred if any(preferred in row for row in rows) else fallback
    values = [float(row[value_key]) for row in rows if row.get(value_key) is not None]
    if len(values) < 4:
        return deepcopy(rows)
    q1, q3 = stats.scoreatpercentile(values, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return [
        row
        for row in rows
        if row.get(value_key) is None or lower <= float(row[value_key]) <= upper
    ]


def _winsorized_rows(
    rows: list[dict[str, Any]], parameters: dict[str, Any]
) -> list[dict[str, Any]]:
    keys = [key for key in _numeric_keys(parameters) if any(key in row for row in rows)]
    result = deepcopy(rows)
    for key in keys:
        values = [float(row[key]) for row in result if row.get(key) is not None]
        if len(values) < 4:
            continue
        lower, upper = stats.scoreatpercentile(values, [5, 95])
        for row in result:
            if row.get(key) is not None:
                row[key] = min(float(upper), max(float(lower), float(row[key])))
    return result


def alternative_method(analysis_type: str) -> str | None:
    mapping = {
        "paired_t": "wilcoxon",
        "wilcoxon": "paired_t",
        "independent_t": "mann_whitney",
        "welch_t": "mann_whitney",
        "mann_whitney": "welch_t",
        "anova": "kruskal_wallis",
        "kruskal_wallis": "anova",
        "pearson": "spearman",
        "spearman": "pearson",
        "chi_square": "fisher_exact",
        "fisher_exact": "chi_square",
    }
    return mapping.get(analysis_type)


def run_sensitivity_scenario(
    rows: list[dict[str, Any]],
    base_analysis_type: str,
    parameters: dict[str, Any],
    alpha: float,
    scenario_key: str,
    requested_alternative: str | None = None,
) -> tuple[str, list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    scenario_parameters: dict[str, Any] = {}
    analysis_type = base_analysis_type
    transformed = deepcopy(rows)
    if scenario_key == "complete_cases":
        transformed = _complete_cases(rows, parameters)
    elif scenario_key == "without_iqr_outliers":
        transformed = _without_iqr_outliers(rows, parameters)
    elif scenario_key == "winsorized_5":
        transformed = _winsorized_rows(rows, parameters)
    elif scenario_key == "alternative_method":
        analysis_type = requested_alternative or alternative_method(base_analysis_type) or base_analysis_type
        scenario_parameters["alternative_analysis_type"] = analysis_type
    else:
        raise ValueError("Cenário de sensibilidade não suportado.")
    scenario_parameters.update(
        {
            "original_rows": len(rows),
            "analyzed_rows": len(transformed),
            "removed_rows": len(rows) - len(transformed),
        }
    )
    return (
        analysis_type,
        transformed,
        execute(transformed, analysis_type, parameters, alpha),
        scenario_parameters,
    )


def compare_methods(
    rows: list[dict[str, Any]],
    methods: list[str],
    parameters: dict[str, Any],
    alpha: float,
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    conclusions: list[bool] = []
    for method in methods:
        result = execute(rows, method, parameters, alpha)
        results[method] = result
        p_value = result.get("test_results", {}).get("p_value")
        if p_value is not None:
            conclusions.append(bool(float(p_value) < alpha))
    consistent = len(set(conclusions)) <= 1
    recommendation = (
        "Os métodos produziram a mesma conclusão estatística. Priorize o método cujos pressupostos melhor correspondem aos dados."
        if consistent
        else "As conclusões diferem entre os métodos. Revise pressupostos, valores extremos e tamanho amostral antes de concluir."
    )
    return {
        "results": results,
        "conclusions_consistent": consistent,
        "recommendation": recommendation,
    }


def calculate_sample_size(
    design: str,
    alpha: float,
    power: float,
    effect_size: float,
    group_ratio: float = 1.0,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if effect_size <= 0:
        raise ValueError("O tamanho do efeito esperado deve ser maior que zero.")
    z_alpha = float(stats.norm.ppf(1 - alpha / 2))
    z_power = float(stats.norm.ppf(power))
    parameters = parameters or {}
    if design == "paired":
        required = math.ceil(((z_alpha + z_power) / effect_size) ** 2)
        return {
            "total_participants": required,
            "per_group": None,
            "formula": "aproximação normal para diferença pareada",
            "recommendation": math.ceil(required * 1.15),
            "attrition_allowance": "15%",
        }
    if design == "independent":
        first_group = math.ceil(
            ((1 + 1 / group_ratio) * (z_alpha + z_power) ** 2) / effect_size**2
        )
        second_group = math.ceil(first_group * group_ratio)
        total = first_group + second_group
        return {
            "total_participants": total,
            "group_1": first_group,
            "group_2": second_group,
            "formula": "aproximação normal para dois grupos independentes",
            "recommendation": math.ceil(total * 1.15),
            "attrition_allowance": "15%",
        }
    if design == "correlation":
        expected_r = min(0.99, effect_size)
        fisher_z = math.atanh(expected_r)
        required = math.ceil(3 + ((z_alpha + z_power) / fisher_z) ** 2)
        return {
            "total_participants": required,
            "expected_correlation": expected_r,
            "formula": "transformação z de Fisher",
            "recommendation": math.ceil(required * 1.15),
            "attrition_allowance": "15%",
        }
    if design == "proportion":
        baseline = float(parameters.get("baseline_proportion", 0.5))
        expected = min(0.999, max(0.001, baseline + effect_size))
        pooled = (baseline + expected) / 2
        numerator = (
            z_alpha * math.sqrt(2 * pooled * (1 - pooled))
            + z_power
            * math.sqrt(baseline * (1 - baseline) + expected * (1 - expected))
        ) ** 2
        per_group = math.ceil(numerator / (expected - baseline) ** 2)
        return {
            "total_participants": per_group * 2,
            "per_group": per_group,
            "baseline_proportion": baseline,
            "expected_proportion": expected,
            "formula": "comparação aproximada de duas proporções",
            "recommendation": math.ceil(per_group * 2 * 1.15),
            "attrition_allowance": "15%",
        }
    raise ValueError("Desenho amostral não suportado.")


def generate_reproduction_script(
    language: str,
    analysis_type: str,
    parameters: dict[str, Any],
    dataset_checksum: str,
) -> str:
    x_key = str(parameters.get("x_key", "pre"))
    y_key = str(parameters.get("y_key", "post"))
    value_key = str(parameters.get("value_key", "score"))
    group_key = str(parameters.get("group_key", "group"))
    if language == "python":
        test_lines = {
            "paired_t": f"result = stats.ttest_rel(df[{y_key!r}], df[{x_key!r}], nan_policy='omit')",
            "wilcoxon": f"result = stats.wilcoxon(df[{y_key!r}], df[{x_key!r}])",
            "independent_t": f"groups = [g[{value_key!r}].dropna().to_numpy() for _, g in df.groupby({group_key!r})]\nresult = stats.ttest_ind(groups[0], groups[1], equal_var=True)",
            "welch_t": f"groups = [g[{value_key!r}].dropna().to_numpy() for _, g in df.groupby({group_key!r})]\nresult = stats.ttest_ind(groups[0], groups[1], equal_var=False)",
            "mann_whitney": f"groups = [g[{value_key!r}].dropna().to_numpy() for _, g in df.groupby({group_key!r})]\nresult = stats.mannwhitneyu(groups[0], groups[1], alternative='two-sided')",
            "pearson": f"result = stats.pearsonr(df[{x_key!r}], df[{y_key!r}])",
            "spearman": f"result = stats.spearmanr(df[{x_key!r}], df[{y_key!r}])",
        }
        call = test_lines.get(
            analysis_type,
            "# Consulte os parâmetros JSON abaixo para reproduzir este método específico.\nresult = None",
        )
        return f'''# Gerado pelo EduCode Enterprise 2.0 — Sprint 11.1\n# Dataset SHA-256: {dataset_checksum}\nimport json\nimport pandas as pd\nfrom scipy import stats\n\ndf = pd.read_csv("dataset.csv")\nparameters = json.loads({json.dumps(parameters, ensure_ascii=False)!r})\n{call}\nprint(result)\n'''
    if language == "r":
        test_lines = {
            "paired_t": f'result <- t.test(df[["{y_key}"]], df[["{x_key}"]], paired=TRUE)',
            "wilcoxon": f'result <- wilcox.test(df[["{y_key}"]], df[["{x_key}"]], paired=TRUE)',
            "independent_t": f'result <- t.test(df[["{value_key}"]] ~ df[["{group_key}"]], var.equal=TRUE)',
            "welch_t": f'result <- t.test(df[["{value_key}"]] ~ df[["{group_key}"]], var.equal=FALSE)',
            "mann_whitney": f'result <- wilcox.test(df[["{value_key}"]] ~ df[["{group_key}"]])',
            "pearson": f'result <- cor.test(df[["{x_key}"]], df[["{y_key}"]], method="pearson")',
            "spearman": f'result <- cor.test(df[["{x_key}"]], df[["{y_key}"]], method="spearman")',
        }
        call = test_lines.get(
            analysis_type,
            "# Consulte os parâmetros registrados para reproduzir este método específico.\nresult <- NULL",
        )
        return f'''# Gerado pelo EduCode Enterprise 2.0 — Sprint 11.1\n# Dataset SHA-256: {dataset_checksum}\ndf <- read.csv("dataset.csv", stringsAsFactors=TRUE)\n{call}\nprint(result)\n'''
    raise ValueError("Linguagem não suportada. Use python ou r.")
