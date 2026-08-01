from __future__ import annotations

import math
import statistics
from typing import Any

try:
    import numpy as np
    from scipy import stats
except ImportError:  # pragma: no cover - validated at runtime
    np = None
    stats = None


def describe(values: list[float]) -> dict[str, float | int | None]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "std_dev": None,
            "min": None,
            "max": None,
            "q1": None,
            "q3": None,
        }
    ordered = sorted(clean)
    q1, q3 = (
        np.percentile(ordered, [25, 75]).tolist()
        if np is not None
        else (ordered[len(ordered) // 4], ordered[(3 * len(ordered)) // 4])
    )
    return {
        "n": len(clean),
        "mean": statistics.fmean(clean),
        "median": statistics.median(clean),
        "std_dev": statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "min": min(clean),
        "max": max(clean),
        "q1": float(q1),
        "q3": float(q3),
    }


def cohens_d_independent(group_a: list[float], group_b: list[float]) -> float | None:
    if len(group_a) < 2 or len(group_b) < 2:
        return None
    pooled_denominator = len(group_a) + len(group_b) - 2
    pooled_numerator = (
        (len(group_a) - 1) * statistics.variance(group_a)
        + (len(group_b) - 1) * statistics.variance(group_b)
    )
    pooled = math.sqrt(pooled_numerator / pooled_denominator)
    return (statistics.fmean(group_a) - statistics.fmean(group_b)) / pooled if pooled else 0.0


def hedges_g(group_a: list[float], group_b: list[float]) -> float | None:
    d_value = cohens_d_independent(group_a, group_b)
    if d_value is None:
        return None
    degrees_of_freedom = len(group_a) + len(group_b) - 2
    correction = 1 - (3 / (4 * degrees_of_freedom - 1)) if degrees_of_freedom > 1 else 1
    return d_value * correction


def cohens_dz(before: list[float], after: list[float]) -> float | None:
    differences = [post - pre for pre, post in zip(before, after, strict=False)]
    if len(differences) < 2:
        return None
    standard_deviation = statistics.stdev(differences)
    return statistics.fmean(differences) / standard_deviation if standard_deviation else 0.0


def cronbach_alpha(matrix: list[list[float]]) -> float | None:
    if len(matrix) < 2 or not matrix or len(matrix[0]) < 2:
        return None
    item_count = len(matrix[0])
    columns = list(zip(*matrix, strict=True))
    item_variances = sum(statistics.variance(list(column)) for column in columns)
    totals = [sum(row) for row in matrix]
    total_variance = statistics.variance(totals)
    return (
        (item_count / (item_count - 1)) * (1 - item_variances / total_variance)
        if total_variance
        else 0.0
    )


def adjust_p_values(values: list[float], method: str = "holm") -> list[float]:
    if not values:
        return []
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    total = len(values)
    adjusted = [0.0] * total
    if method == "bonferroni":
        return [min(1.0, value * total) for value in values]
    if method == "benjamini_hochberg":
        previous = 1.0
        for rank, (original_index, value) in reversed(list(enumerate(indexed, start=1))):
            corrected = min(previous, value * total / rank)
            adjusted[original_index] = min(1.0, corrected)
            previous = corrected
        return adjusted
    running = 0.0
    for rank, (original_index, value) in enumerate(indexed):
        corrected = min(1.0, value * (total - rank))
        running = max(running, corrected)
        adjusted[original_index] = running
    return adjusted


def _numbers(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            values.append(numeric)
    return values


def _normality(values: list[float]) -> dict[str, Any]:
    if len(values) < 3 or stats is None:
        return {"checked": False, "reason": "São necessárias pelo menos 3 observações."}
    sample = values[:5000]
    result = stats.shapiro(sample)
    return {
        "checked": True,
        "test": "Shapiro-Wilk",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "adequate": bool(result.pvalue >= 0.05),
    }


def _ci_mean_diff(
    differences: list[float], confidence: float = 0.95
) -> dict[str, float | None]:
    if len(differences) < 2 or stats is None:
        return {"lower": None, "upper": None}
    mean_value = statistics.fmean(differences)
    standard_error = stats.sem(differences)
    lower, upper = stats.t.interval(
        confidence,
        len(differences) - 1,
        loc=mean_value,
        scale=standard_error,
    )
    return {"lower": float(lower), "upper": float(upper)}


def _correlation_ci(coefficient: float, sample_size: int) -> dict[str, float | None]:
    if sample_size <= 3 or abs(coefficient) >= 1 or stats is None:
        return {"lower": None, "upper": None}
    transformed = math.atanh(coefficient)
    margin = float(stats.norm.ppf(0.975)) / math.sqrt(sample_size - 3)
    return {
        "lower": math.tanh(transformed - margin),
        "upper": math.tanh(transformed + margin),
    }


def _effect_label(value: float | None) -> str:
    if value is None:
        return "não estimado"
    magnitude = abs(value)
    if magnitude < 0.2:
        return "muito pequeno"
    if magnitude < 0.5:
        return "pequeno"
    if magnitude < 0.8:
        return "moderado"
    return "grande"


def _grouped_values(
    rows: list[dict[str, Any]], group_key: str, value_key: str
) -> dict[str, list[float]]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        if row.get(group_key) is None or row.get(value_key) is None:
            continue
        try:
            groups.setdefault(str(row[group_key]), []).append(float(row[value_key]))
        except (TypeError, ValueError):
            continue
    return groups


def execute(
    rows: list[dict[str, Any]],
    analysis_type: str,
    params: dict[str, Any],
    alpha: float = 0.05,
) -> dict[str, Any]:
    if stats is None or np is None:
        raise RuntimeError("SciPy e NumPy são necessários para o Laboratório Estatístico.")

    x_key = str(params.get("x_key", "pre"))
    y_key = str(params.get("y_key", "post"))
    group_key = str(params.get("group_key", "group"))
    value_key = str(params.get("value_key", "score"))
    assumptions: dict[str, Any] = {}
    descriptive: dict[str, Any] = {}
    test: dict[str, Any] = {}
    effect: dict[str, Any] = {}
    confidence_intervals: dict[str, Any] = {}
    limitations: list[str] = []

    if analysis_type == "descriptive":
        values = _numbers(rows, value_key)
        descriptive = {value_key: describe(values)}

    elif analysis_type in {"paired_t", "wilcoxon"}:
        pairs = [
            (float(row[x_key]), float(row[y_key]))
            for row in rows
            if row.get(x_key) is not None and row.get(y_key) is not None
        ]
        if len(pairs) < 2:
            raise ValueError("São necessários pelo menos 2 pares completos.")
        before = [item[0] for item in pairs]
        after = [item[1] for item in pairs]
        differences = [post - pre for pre, post in pairs]
        descriptive = {
            x_key: describe(before),
            y_key: describe(after),
            "difference": describe(differences),
        }
        assumptions["difference_normality"] = _normality(differences)
        result = (
            stats.ttest_rel(after, before, nan_policy="omit")
            if analysis_type == "paired_t"
            else stats.wilcoxon(after, before, zero_method="wilcox")
        )
        test = {
            "name": "Teste t pareado" if analysis_type == "paired_t" else "Wilcoxon",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "degrees_of_freedom": len(pairs) - 1 if analysis_type == "paired_t" else None,
            "significant": bool(result.pvalue < alpha),
        }
        effect = (
            {"name": "Cohen's dz", "value": cohens_dz(before, after)}
            if analysis_type == "paired_t"
            else {
                "name": "r aproximado",
                "value": (
                    float(abs(stats.norm.ppf(result.pvalue / 2)) / math.sqrt(len(pairs)))
                    if result.pvalue > 0
                    else None
                ),
            }
        )
        confidence_intervals = {"mean_difference_95": _ci_mean_diff(differences)}

    elif analysis_type in {"independent_t", "welch_t", "mann_whitney"}:
        groups = _grouped_values(rows, group_key, value_key)
        if len(groups) != 2:
            raise ValueError("A análise exige exatamente dois grupos.")
        labels = list(groups)
        group_a, group_b = groups[labels[0]], groups[labels[1]]
        descriptive = {labels[0]: describe(group_a), labels[1]: describe(group_b)}
        assumptions = {
            "group_1_normality": _normality(group_a),
            "group_2_normality": _normality(group_b),
        }
        if len(group_a) >= 2 and len(group_b) >= 2:
            levene = stats.levene(group_a, group_b)
            assumptions["homogeneity"] = {
                "test": "Levene",
                "statistic": float(levene.statistic),
                "p_value": float(levene.pvalue),
                "adequate": bool(levene.pvalue >= 0.05),
            }
        if analysis_type == "mann_whitney":
            result = stats.mannwhitneyu(group_a, group_b, alternative="two-sided")
            name = "Mann-Whitney"
            degrees_of_freedom = None
        else:
            equal_variance = analysis_type == "independent_t"
            result = stats.ttest_ind(
                group_a,
                group_b,
                equal_var=equal_variance,
                nan_policy="omit",
            )
            name = "Teste t independente" if equal_variance else "Teste t de Welch"
            degrees_of_freedom = len(group_a) + len(group_b) - 2 if equal_variance else None
        test = {
            "name": name,
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "degrees_of_freedom": degrees_of_freedom,
            "significant": bool(result.pvalue < alpha),
        }
        effect = {
            "name": "Hedges' g" if min(len(group_a), len(group_b)) < 20 else "Cohen's d",
            "value": (
                hedges_g(group_a, group_b)
                if min(len(group_a), len(group_b)) < 20
                else cohens_d_independent(group_a, group_b)
            ),
        }

    elif analysis_type in {"anova", "kruskal_wallis"}:
        groups = _grouped_values(rows, group_key, value_key)
        if len(groups) < 3:
            raise ValueError("São necessários pelo menos três grupos.")
        arrays = list(groups.values())
        descriptive = {key: describe(values) for key, values in groups.items()}
        result = (
            stats.f_oneway(*arrays)
            if analysis_type == "anova"
            else stats.kruskal(*arrays)
        )
        test = {
            "name": "ANOVA de uma via" if analysis_type == "anova" else "Kruskal-Wallis",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "significant": bool(result.pvalue < alpha),
        }
        if analysis_type == "anova":
            all_values = [value for group in arrays for value in group]
            grand_mean = statistics.fmean(all_values)
            between = sum(
                len(group) * (statistics.fmean(group) - grand_mean) ** 2 for group in arrays
            )
            total = sum((value - grand_mean) ** 2 for value in all_values)
            effect = {"name": "Eta quadrado", "value": between / total if total else 0.0}

    elif analysis_type == "friedman":
        repeated_keys = list(params.get("repeated_keys", []))
        matrix = [
            [float(row[key]) for key in repeated_keys]
            for row in rows
            if repeated_keys and all(row.get(key) is not None for key in repeated_keys)
        ]
        if len(matrix) < 2 or len(repeated_keys) < 3:
            raise ValueError("Friedman exige pelo menos 2 participantes e 3 momentos.")
        columns = [list(column) for column in zip(*matrix, strict=True)]
        result = stats.friedmanchisquare(*columns)
        descriptive = {key: describe(values) for key, values in zip(repeated_keys, columns, strict=True)}
        test = {
            "name": "Friedman",
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
            "significant": bool(result.pvalue < alpha),
        }
        effect = {
            "name": "Kendall's W",
            "value": float(result.statistic / (len(matrix) * (len(repeated_keys) - 1))),
        }

    elif analysis_type in {"pearson", "spearman"}:
        pairs = [
            (float(row[x_key]), float(row[y_key]))
            for row in rows
            if row.get(x_key) is not None and row.get(y_key) is not None
        ]
        if len(pairs) < 3:
            raise ValueError("São necessários pelo menos 3 pares para correlação.")
        x_values = [item[0] for item in pairs]
        y_values = [item[1] for item in pairs]
        descriptive = {x_key: describe(x_values), y_key: describe(y_values)}
        result = (
            stats.pearsonr(x_values, y_values)
            if analysis_type == "pearson"
            else stats.spearmanr(x_values, y_values)
        )
        coefficient = float(result.statistic)
        test = {
            "name": "Correlação de Pearson" if analysis_type == "pearson" else "Correlação de Spearman",
            "statistic": coefficient,
            "p_value": float(result.pvalue),
            "significant": bool(result.pvalue < alpha),
        }
        effect = {"name": "r", "value": coefficient}
        confidence_intervals = {"correlation_95": _correlation_ci(coefficient, len(pairs))}

    elif analysis_type == "cronbach_alpha":
        item_keys = list(params.get("item_keys", []))
        matrix = [
            [float(row[key]) for key in item_keys]
            for row in rows
            if item_keys and all(row.get(key) is not None for key in item_keys)
        ]
        value = cronbach_alpha(matrix)
        descriptive = {"respondents": len(matrix), "items": len(item_keys)}
        test = {
            "name": "Alfa de Cronbach",
            "statistic": value,
            "p_value": None,
            "significant": None,
        }
        effect = {"name": "consistência interna", "value": value}

    elif analysis_type in {"chi_square", "fisher_exact"}:
        row_key = str(params.get("row_key", "group"))
        column_key = str(params.get("column_key", "outcome"))
        row_levels = sorted(
            {str(row[row_key]) for row in rows if row.get(row_key) is not None}
        )
        column_levels = sorted(
            {str(row[column_key]) for row in rows if row.get(column_key) is not None}
        )
        table = [
            [
                sum(
                    1
                    for row in rows
                    if str(row.get(row_key)) == row_value
                    and str(row.get(column_key)) == column_value
                )
                for column_value in column_levels
            ]
            for row_value in row_levels
        ]
        if analysis_type == "fisher_exact":
            if len(table) != 2 or any(len(row) != 2 for row in table):
                raise ValueError("Fisher exato exige uma tabela 2x2.")
            result = stats.fisher_exact(table)
            statistic = float(result.statistic)
            p_value = float(result.pvalue)
            name = "Teste exato de Fisher"
            degrees_of_freedom = None
        else:
            result = stats.chi2_contingency(table)
            statistic = float(result.statistic)
            p_value = float(result.pvalue)
            name = "Qui-quadrado"
            degrees_of_freedom = int(result.dof)
        test = {
            "name": name,
            "statistic": statistic,
            "p_value": p_value,
            "degrees_of_freedom": degrees_of_freedom,
            "significant": bool(p_value < alpha),
        }
        descriptive = {
            "contingency_table": table,
            "row_levels": row_levels,
            "column_levels": column_levels,
        }
        total_count = sum(sum(row) for row in table)
        minimum_dimension = min(len(row_levels) - 1, len(column_levels) - 1)
        effect = {
            "name": "Cramér's V" if analysis_type == "chi_square" else "Odds ratio",
            "value": (
                math.sqrt(statistic / (total_count * minimum_dimension))
                if analysis_type == "chi_square" and total_count and minimum_dimension
                else statistic
            ),
        }

    elif analysis_type == "mcnemar":
        before_key = str(params.get("before_key", "pre_binary"))
        after_key = str(params.get("after_key", "post_binary"))
        pairs = [
            (int(row[before_key]), int(row[after_key]))
            for row in rows
            if row.get(before_key) is not None and row.get(after_key) is not None
        ]
        discordant_01 = sum(1 for before, after in pairs if before == 0 and after == 1)
        discordant_10 = sum(1 for before, after in pairs if before == 1 and after == 0)
        discordant_total = discordant_01 + discordant_10
        if discordant_total == 0:
            p_value = 1.0
            statistic = 0.0
        else:
            exact = stats.binomtest(
                min(discordant_01, discordant_10),
                discordant_total,
                p=0.5,
                alternative="two-sided",
            )
            p_value = float(exact.pvalue)
            statistic = float((abs(discordant_01 - discordant_10) - 1) ** 2 / discordant_total)
        descriptive = {
            "pairs": len(pairs),
            "changed_0_to_1": discordant_01,
            "changed_1_to_0": discordant_10,
        }
        test = {
            "name": "McNemar exato",
            "statistic": statistic,
            "p_value": p_value,
            "significant": bool(p_value < alpha),
        }
        effect = {
            "name": "odds ratio pareado",
            "value": discordant_01 / discordant_10 if discordant_10 else None,
        }

    elif analysis_type == "likert_summary":
        dimensions = dict(params.get("dimensions", {}))
        if not dimensions:
            raise ValueError("Defina ao menos uma dimensão e seus itens.")
        reverse_items = set(params.get("reverse_items", []))
        scale_min = float(params.get("scale_min", 1))
        scale_max = float(params.get("scale_max", 5))
        dimension_results: dict[str, Any] = {}
        all_items: list[str] = []
        for dimension, keys_value in dimensions.items():
            keys = list(keys_value)
            all_items.extend(keys)
            scores: list[float] = []
            for row in rows:
                if not all(row.get(key) is not None for key in keys):
                    continue
                item_values = []
                for key in keys:
                    value = float(row[key])
                    if key in reverse_items:
                        value = scale_max + scale_min - value
                    item_values.append(value)
                scores.append(statistics.fmean(item_values))
            dimension_results[str(dimension)] = describe(scores)
        matrix = [
            [float(row[key]) for key in all_items]
            for row in rows
            if all_items and all(row.get(key) is not None for key in all_items)
        ]
        alpha_value = cronbach_alpha(matrix)
        descriptive = {"dimensions": dimension_results, "respondents": len(matrix)}
        test = {
            "name": "Resumo de escala Likert",
            "statistic": alpha_value,
            "p_value": None,
            "significant": None,
        }
        effect = {"name": "Alfa de Cronbach global", "value": alpha_value}

    else:
        raise ValueError("Tipo de análise não suportado.")

    p_value = test.get("p_value")
    significant = bool(p_value is not None and p_value < alpha)
    effect_value = effect.get("value")
    teacher = (
        "Os resultados indicam uma diferença ou associação estatisticamente significativa."
        if significant
        else "Os dados não apresentaram evidência estatística suficiente de diferença ou associação."
    )
    if effect_value is not None:
        teacher += (
            f" O tamanho do efeito estimado foi {float(effect_value):.2f} "
            f"({_effect_label(float(effect_value))})."
        )
    researcher = (
        f"{test.get('name', 'Análise')}: estatística={test.get('statistic')}, "
        f"p={p_value}, alfa={alpha}."
    )
    if len(rows) < 10:
        limitations.append("A amostra é pequena; interprete os resultados com cautela.")
    if p_value is not None and not significant:
        limitations.append(
            "Ausência de significância não comprova ausência de efeito; considere poder e precisão."
        )
    return {
        "assumptions": assumptions,
        "descriptive_results": descriptive,
        "test_results": test,
        "effect_size": effect,
        "confidence_intervals": confidence_intervals,
        "interpretation_teacher": teacher,
        "interpretation_researcher": researcher,
        "limitations": limitations,
    }


def recommend(
    goal: str,
    same: bool,
    variable_type: str,
    group_count: int,
) -> dict[str, Any]:
    if goal == "pre_post":
        return {
            "recommended_test": "paired_t" if variable_type == "numeric" else "wilcoxon",
            "alternative_test": "wilcoxon" if variable_type == "numeric" else "mcnemar",
            "rationale": "Os mesmos participantes são comparados em dois momentos.",
            "required_columns": ["pre", "post"],
        }
    if goal == "two_groups":
        return {
            "recommended_test": "independent_t" if variable_type == "numeric" else "mann_whitney",
            "alternative_test": "welch_t" if variable_type == "numeric" else "fisher_exact",
            "rationale": "Dois grupos independentes serão comparados.",
            "required_columns": ["group", "score"],
        }
    if goal == "three_groups" or group_count >= 3:
        return {
            "recommended_test": "anova" if variable_type == "numeric" else "kruskal_wallis",
            "alternative_test": "kruskal_wallis",
            "rationale": "Três ou mais grupos serão comparados.",
            "required_columns": ["group", "score"],
        }
    if goal == "association":
        return {
            "recommended_test": "pearson" if variable_type == "numeric" else "spearman",
            "alternative_test": "spearman",
            "rationale": "A análise verifica associação entre duas variáveis.",
            "required_columns": ["x", "y"],
        }
    return {
        "recommended_test": "likert_summary" if variable_type in {"likert", "ordinal"} else "cronbach_alpha",
        "alternative_test": "cronbach_alpha",
        "rationale": "A consistência interna e as dimensões da escala serão avaliadas.",
        "required_columns": ["item_1", "item_2", "item_3"],
    }
