from app.comic_page_editor.policies import (
    PRESERVATION_LABELS,
    build_story_distribution,
    merge_panel_content,
    narrative_stage,
    recommended_layout_code,
)


def test_narrative_stages_change_across_a_long_hq():
    stages = [
        narrative_stage(page, 10, "BALANCED")
        for page in range(1, 11)
    ]
    assert stages[0] == "OPENING"
    assert "DEVELOPMENT" in stages
    assert "CLIMAX" in stages
    assert stages[-1] == "RESOLUTION"
    assert len({recommended_layout_code(stage) for stage in stages}) >= 4


def test_distribution_respects_each_pages_real_grid_capacity():
    plan = build_story_distribution(
        source_text=(
            "A turma encontra um problema. O desafio é decomposto. "
            "Cada grupo testa uma solução. A solução é comparada. "
            "A turma explica o algoritmo. A história termina com reflexão."
        ),
        page_capacities=[4, 3, 6, 5],
        narrative_pacing="CINEMATIC",
    )
    assert [item["panel_count"] for item in plan] == [4, 3, 6, 5]
    assert sum(len(item["panels"]) for item in plan) == 18
    assert len(
        {item["recommended_layout_code"] for item in plan}
    ) >= 3
    assert plan[0]["panels"][0]["global_panel_order"] == 1
    assert plan[-1]["panels"][-1]["global_panel_order"] == 18


def test_layout_change_can_preserve_existing_content():
    previous = [
        {
            "scene_summary": "Cena original",
            "visual_prompt": "Plano geral",
            "locked_elements": ["character"],
            "pedagogical_metadata": {"bncc": "EF01"},
            "accessibility_metadata": {"alt_text": "Descrição"},
        }
    ]
    result = merge_panel_content(
        previous,
        [
            {
                "x": 0,
                "y": 0,
                "width": 0.5,
                "height": 1,
                "shape": "RECTANGLE",
            },
            {
                "x": 0.5,
                "y": 0,
                "width": 0.5,
                "height": 1,
                "shape": "RECTANGLE",
            },
        ],
        True,
    )
    assert result[0]["scene_summary"] == "Cena original"
    assert result[0]["locked_elements"] == ["character"]
    assert result[1]["scene_summary"] == ""


def test_preservation_labels_are_presented_in_portuguese():
    assert PRESERVATION_LABELS["character"] == "Personagem"
    assert PRESERVATION_LABELS["outfit"] == "Roupa"
    assert PRESERVATION_LABELS["scenario"] == "Cenário"
    assert PRESERVATION_LABELS["framing"] == "Enquadramento"
    assert PRESERVATION_LABELS["expression"] == "Expressão"
    assert PRESERVATION_LABELS["palette"] == "Paleta"
