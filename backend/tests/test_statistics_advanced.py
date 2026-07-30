from __future__ import annotations

from types import SimpleNamespace

from app.services.statistical_exports import (
    render_chart_bytes,
    report_docx_bytes,
    report_pdf_bytes,
)
from app.services.statistics_advanced import (
    calculate_sample_size,
    compare_methods,
    configuration_checksum,
    generate_reproduction_script,
    result_signature,
    run_sensitivity_scenario,
)
from app.services.statistics_engine import adjust_p_values, execute


PAIRED_ROWS = [
    {"student_id": "E1", "pre": 45, "post": 65},
    {"student_id": "E2", "pre": 52, "post": 73},
    {"student_id": "E3", "pre": 60, "post": 80},
    {"student_id": "E4", "pre": 57, "post": 78},
    {"student_id": "E5", "pre": 49, "post": 70},
    {"student_id": "E6", "pre": 63, "post": 84},
]
PARAMETERS = {"x_key": "pre", "y_key": "post", "value_key": "score"}


def test_checksums_are_deterministic() -> None:
    first = configuration_checksum("abc", "paired_t", PARAMETERS)
    second = configuration_checksum("abc", "paired_t", dict(reversed(PARAMETERS.items())))
    assert first == second
    assert len(result_signature({"p": 0.05})) == 64


def test_sensitivity_complete_cases_does_not_require_unrelated_score() -> None:
    method, rows, result, metadata = run_sensitivity_scenario(
        PAIRED_ROWS,
        "paired_t",
        PARAMETERS,
        0.05,
        "complete_cases",
    )
    assert method == "paired_t"
    assert len(rows) == len(PAIRED_ROWS)
    assert metadata["removed_rows"] == 0
    assert result["test_results"]["p_value"] < 0.05


def test_sensitivity_and_method_comparison() -> None:
    methods = compare_methods(PAIRED_ROWS, ["paired_t", "wilcoxon"], PARAMETERS, 0.05)
    assert methods["conclusions_consistent"] is True
    assert set(methods["results"]) == {"paired_t", "wilcoxon"}


def test_sample_size_planning() -> None:
    paired = calculate_sample_size("paired", 0.05, 0.80, 0.5)
    independent = calculate_sample_size("independent", 0.05, 0.80, 0.5)
    correlation = calculate_sample_size("correlation", 0.05, 0.80, 0.3)
    assert paired["total_participants"] > 0
    assert independent["group_1"] > 0
    assert correlation["recommendation"] >= correlation["total_participants"]


def test_reproduction_scripts_include_dataset_checksum() -> None:
    python_script = generate_reproduction_script("python", "paired_t", PARAMETERS, "checksum123")
    r_script = generate_reproduction_script("r", "paired_t", PARAMETERS, "checksum123")
    assert "checksum123" in python_script
    assert "ttest_rel" in python_script
    assert "paired=TRUE" in r_script


def test_multiple_comparison_adjustments() -> None:
    values = [0.01, 0.03, 0.20]
    assert adjust_p_values(values, "bonferroni") == [0.03, 0.09, 0.6000000000000001]
    holm = adjust_p_values(values, "holm")
    bh = adjust_p_values(values, "benjamini_hochberg")
    assert all(0 <= value <= 1 for value in holm + bh)


def test_advanced_statistical_methods() -> None:
    friedman_rows = [
        {"m1": 1, "m2": 2, "m3": 4},
        {"m1": 2, "m2": 3, "m3": 5},
        {"m1": 1, "m2": 4, "m3": 5},
        {"m1": 2, "m2": 4, "m3": 6},
    ]
    friedman = execute(friedman_rows, "friedman", {"repeated_keys": ["m1", "m2", "m3"]})
    assert friedman["test_results"]["name"] == "Friedman"

    mcnemar_rows = [
        {"before": 0, "after": 1},
        {"before": 0, "after": 1},
        {"before": 1, "after": 0},
        {"before": 1, "after": 1},
    ]
    mcnemar = execute(
        mcnemar_rows,
        "mcnemar",
        {"before_key": "before", "after_key": "after"},
    )
    assert mcnemar["test_results"]["name"] == "McNemar exato"

    likert_rows = [
        {"u1": 4, "u2": 5, "f1": 3, "f2": 4},
        {"u1": 5, "u2": 4, "f1": 4, "f2": 5},
        {"u1": 3, "u2": 4, "f1": 2, "f2": 3},
    ]
    likert = execute(
        likert_rows,
        "likert_summary",
        {"dimensions": {"utilidade": ["u1", "u2"], "facilidade": ["f1", "f2"]}},
    )
    assert "utilidade" in likert["descriptive_results"]["dimensions"]


def test_chart_and_report_exports() -> None:
    chart = SimpleNamespace(
        chart_type="paired",
        data_snapshot=PAIRED_ROWS,
        configuration={"before_key": "pre", "after_key": "post", "y_key": "post"},
        title="Evolução",
        description="Pré e pós-teste",
        alt_text="Gráfico de evolução entre dois momentos.",
    )
    png = render_chart_bytes(
        chart.chart_type,
        chart.data_snapshot,
        chart.configuration,
        chart.title,
        chart.description,
        "png",
    )
    svg = render_chart_bytes(
        chart.chart_type,
        chart.data_snapshot,
        chart.configuration,
        chart.title,
        chart.description,
        "svg",
    )
    assert png.startswith(b"\x89PNG")
    assert b"<svg" in svg[:500]

    metadata = {"dataset_checksum": "abc", "analysis_signature": "def"}
    pdf = report_pdf_bytes("Relatório", "<h1>Resultado</h1><p>Teste.</p>", [chart], metadata)
    docx = report_docx_bytes("Relatório", "<h1>Resultado</h1><p>Teste.</p>", [chart], metadata)
    assert pdf.startswith(b"%PDF")
    assert docx.startswith(b"PK")
