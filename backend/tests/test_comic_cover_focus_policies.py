from app.comic_page_editor.policies import (
    COVER_COMPOSITIONS,
    continuity_issues,
    cover_generation_payload,
    default_cover_layers,
)


def test_cover_has_six_compositions_and_no_grid():
    assert len(COVER_COMPOSITIONS) == 6
    assert {
        "CINEMATIC",
        "CHARACTER_FOCUS",
        "EDUCATIONAL",
        "MINIMALIST",
        "DIAGONAL",
        "ENSEMBLE",
    }.issubset(COVER_COMPOSITIONS)


def test_default_cover_text_is_editable_layer_content():
    layers = default_cover_layers()
    assert any(item["layer_type"] == "TITLE" for item in layers)
    assert all("grid" not in item for item in layers)


def test_cover_ai_prompt_forbids_embedded_text():
    payload = cover_generation_payload(
        title="Frações em aventura",
        summary=(
            "Dois estudantes resolvem um desafio com frações."
        ),
        discipline="Matemática",
        theme="Frações",
        composition_code="EDUCATIONAL",
        preservation={
            "elements": ["character", "outfit"],
        },
        continuity={
            "character": "Ana e Caio",
            "school_year": "6º ano",
        },
        variation_count=4,
        additional_instructions="",
    )
    requirements = " ".join(
        payload["mandatory_rules"]
    ).lower()
    assert "não inserir" in requirements
    assert "palavras" in requirements
    assert payload["purpose"] == "comic_cover"
    assert payload["variation_count"] == 4


def test_continuity_detects_changes_but_does_not_auto_correct():
    issues = continuity_issues(
        [
            {
                "page_number": 1,
                "page_type": "STORY",
                "character": "Ana",
                "outfit": "uniforme azul",
                "scenario": "laboratório",
            },
            {
                "page_number": 2,
                "page_type": "STORY",
                "character": "Ana",
                "outfit": "casaco vermelho",
                "scenario": "laboratório",
            },
        ]
    )
    assert issues
    assert issues[0]["field"] == "outfit"
    assert "message" in issues[0]
