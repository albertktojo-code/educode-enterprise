from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.comic import (
    ComicBalloon,
    ComicPage,
    ComicPanel,
    GeneratedComic,
    GenerationScope,
    PanelShape,
    PanelStatus,
)
from app.schemas.comic import (
    ComicCreate,
    NarrativeProfile,
    PageLayoutInput,
    RegenerateRequest,
    RegenerationProposalRequest,
)
from app.services.comics.continuity import validate_payload
from app.services.comics.generator import (
    GeneratedPanel,
    StoryInput,
    build_story,
    regenerate_panel_content,
)
from app.services.comics.layouts import layout_for, list_layout_templates, recommended_template
from app.services.comics.manager import _apply_locked_regeneration
from app.services.comics.review import narrative_map


def test_layout_catalog_supports_variable_panel_counts_and_shapes() -> None:
    templates = list_layout_templates()
    assert {template["panel_count"] for template in templates} >= {1, 2, 3, 4, 5, 6}
    dramatic = next(template for template in templates if template["code"] == "four_dramatic")
    shapes = {panel["shape"] for panel in dramatic["panels"]}
    assert PanelShape.CIRCLE.value in shapes
    assert PanelShape.PANORAMIC.value in shapes


def test_layout_falls_back_to_free_grid() -> None:
    panels = layout_for("unknown", 7)
    assert len(panels) == 7
    assert all(panel["width"] > 0 for panel in panels)


def test_recommended_layout_uses_opening_and_final_emphasis() -> None:
    assert recommended_template(3, 1, 4) == "three_hero_top"
    assert recommended_template(3, 4, 4) == "three_hero_bottom"
    assert recommended_template(1, 1, 1) == "single_full"


def test_story_is_continuous_but_contains_clue_and_plot_twist() -> None:
    story = build_story(
        StoryInput(
            title="O mistério das frações",
            topic="frações equivalentes",
            disciplinary_objective="Reconhecer frações equivalentes.",
            ct_objective="Identificar padrões e decompor o problema.",
            facts=["Duas frações equivalentes representam a mesma quantidade."],
            pillar_codes=["pattern_recognition", "decomposition"],
            characters=["Lia", "Caio", "Professor Byte"],
            scenes=["pizzaria", "sala de aula"],
            narrative_profile={"main_genre": "mystery", "max_plot_twists": 2},
        ),
        12,
    )
    beats = [panel["plot_function"] for panel in story]
    assert "clue" in beats
    assert "plot_twist" in beats
    assert all(panel["balloons"] for panel in story)
    assert story[1]["previous_panel_summary"] != ""


def test_regeneration_can_preserve_dialogue_or_scene() -> None:
    panel = build_story(
        StoryInput(
            title="Teste",
            topic="algoritmos",
            disciplinary_objective="Aplicar uma sequência.",
            ct_objective="Construir algoritmos.",
            facts=["Um algoritmo é uma sequência ordenada de passos."],
            pillar_codes=["algorithms"],
            characters=["Lia", "Caio"],
            scenes=["laboratório"],
            narrative_profile={},
        ),
        1,
    )[0]
    scene_only = regenerate_panel_content(
        panel,
        scope="scene",
        instruction="mais emocionante",
        preserve_dialogue=True,
        preserve_scene=False,
    )
    assert scene_only["scene_description"] != panel["scene_description"]
    assert scene_only["balloons"] == panel["balloons"]


def test_continuity_validator_requires_clue_before_plot_twist() -> None:
    pages = [
        {
            "id": str(uuid4()),
            "page_number": 1,
            "panel_count": 1,
            "panels": [
                {
                    "id": str(uuid4()),
                    "reading_order": 1,
                    "plot_function": "plot_twist",
                    "narrative_goal": "Revelar a surpresa.",
                    "previous_panel_summary": "",
                    "initial_state": {"known_facts": []},
                    "final_state": {"known_facts": []},
                    "balloons": [{"id": str(uuid4()), "sequence_number": 1, "text": "Surpresa!"}],
                }
            ],
        }
    ]
    score, findings = validate_payload(pages)
    assert score < 100
    assert any(finding.code == "unsupported_plot_twist" for finding in findings)


def test_comic_schema_accepts_distinct_layout_per_page() -> None:
    data = ComicCreate(
        generation_project_id=uuid4(),
        rag_context_id=uuid4(),
        title="HQ editável",
        page_count=3,
        default_panels_per_page=4,
        narrative_profile=NarrativeProfile(main_genre="comedy"),
        page_layouts=[
            PageLayoutInput(page_number=1, panel_count=1, layout_template="single_full"),
            PageLayoutInput(page_number=2, panel_count=6, layout_template="six_grid"),
            PageLayoutInput(page_number=3, panel_count=3, layout_template="three_hero_bottom"),
        ],
    )
    assert [page.panel_count for page in data.page_layouts] == [1, 6, 3]


def test_regeneration_schema_requires_target() -> None:
    with pytest.raises(ValidationError):
        RegenerateRequest(scope=GenerationScope.PANEL)


def test_regeneration_proposal_defaults_to_three_distinct_tones() -> None:
    request = RegenerationProposalRequest(
        scope=GenerationScope.PANEL,
        panel_id=uuid4(),
    )
    assert request.alternative_count == 3
    assert request.tones == ["funny", "emotional", "mysterious"]


def test_locked_scene_and_balloon_are_preserved() -> None:
    panel = ComicPanel(
        id=uuid4(),
        page_id=uuid4(),
        panel_number=1,
        reading_order=1,
        scene_description="Cena original",
        locked_elements=["scene"],
        status=PanelStatus.DRAFT,
    )
    balloon = ComicBalloon(
        id=uuid4(),
        panel_id=panel.id,
        sequence_number=1,
        text="Fala original",
        is_locked=True,
    )
    panel.balloons = [balloon]
    generated = _generated_from_test_panel(panel)
    generated["scene_description"] = "Cena alterada"
    generated["balloons"][0]["text"] = "Fala alterada"
    _apply_locked_regeneration(panel, generated, GenerationScope.PANEL)
    assert panel.scene_description == "Cena original"
    assert panel.balloons[0].text == "Fala original"


def _generated_from_test_panel(panel: ComicPanel) -> GeneratedPanel:
    return {
        "narrative_goal": "Objetivo",
        "pedagogical_goal": "Aprender",
        "ct_pillar_codes": [],
        "scene_description": panel.scene_description,
        "previous_panel_summary": "",
        "next_panel_hook": "",
        "initial_state": {},
        "final_state": {},
        "emotion": "curiosity",
        "plot_function": "development",
        "balloons": [
            {
                "sequence_number": 1,
                "speaker_name_snapshot": None,
                "balloon_type": "speech",
                "text": panel.balloons[0].text,
                "emotion": None,
                "pedagogical_function": None,
                "position_x": 10.0,
                "position_y": 10.0,
                "width": 40.0,
                "height": 20.0,
            }
        ],
    }


def test_narrative_map_flags_text_overflow_and_uniform_pacing() -> None:
    comic = GeneratedComic(
        id=uuid4(),
        organization_id=uuid4(),
        generation_project_id=uuid4(),
        rag_context_id=uuid4(),
        created_by_user_id=uuid4(),
        created_by_name_snapshot="Professor",
        title="Teste",
    )
    page = ComicPage(id=uuid4(), comic_id=comic.id, page_number=1, panel_count=4)
    page.panels = []
    for index in range(1, 5):
        panel = ComicPanel(
            id=uuid4(),
            page_id=page.id,
            panel_number=index,
            reading_order=index,
            narrative_goal=f"Ação {index}",
            plot_function="clue" if index == 1 else "development",
            pacing="moderate",
            text_word_limit=2,
            final_state={"open_questions": ["O que acontece?"]},
        )
        panel.balloons = [
            ComicBalloon(
                id=uuid4(),
                panel_id=panel.id,
                sequence_number=1,
                text="Texto com muitas palavras para o limite",
            )
        ]
        page.panels.append(panel)
    comic.pages = [page]
    result = narrative_map(comic)
    assert all(item.over_text_limit for item in result.items)
    assert result.pacing_warnings
    assert result.unresolved_clues


def test_panel_visual_prompt_keeps_image_separate_from_balloons() -> None:
    panel = ComicPanel(
        page_id=uuid4(),
        panel_number=1,
        reading_order=1,
        visual_prompt={"image_without_balloons": True, "must_avoid": ["embedded_text"]},
    )
    assert panel.visual_prompt["image_without_balloons"] is True
    assert "embedded_text" in panel.visual_prompt["must_avoid"]
