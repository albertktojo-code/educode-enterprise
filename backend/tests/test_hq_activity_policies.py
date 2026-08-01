from app.comic_page_editor.activities import (
    ACTIVITY_TYPES,
    build_word_search,
    canonical_answer_key,
    canonical_question_type,
    student_activity_payload,
    validate_activity_payload,
    validate_answer_key,
    validate_crossword,
)


def test_activity_catalog_contains_required_types():
    assert {
        "MULTIPLE_CHOICE",
        "TRUE_FALSE",
        "MATCHING",
        "ORDERING",
        "FILL_BLANKS",
        "CROSSWORD",
        "WORD_SEARCH",
        "SHORT_ANSWER",
        "ESSAY",
        "COMPUTATIONAL_THINKING",
        "MATHEMATICS",
    }.issubset(ACTIVITY_TYPES)


def test_word_search_contains_all_words():
    result = build_word_search(["algoritmo", "padrao"], 10)
    assert result["size"] >= 10
    assert set(result["words"]) == {"ALGORITMO", "PADRAO"}
    assert len(result["placements"]) == 2


def test_crossword_requires_clues_and_unique_answers():
    result = validate_crossword(
        [
            {"answer": "algoritmo", "clue": "Sequência de passos"},
            {"answer": "algoritmo", "clue": ""},
        ]
    )
    assert result["valid"] is False
    assert result["errors"]


def test_multiple_choice_requires_correct_option():
    errors = validate_activity_payload(
        "MULTIPLE_CHOICE",
        {
            "options": [
                {"id": "A", "text": "Uma opção", "correct": False},
                {"id": "B", "text": "Outra opção", "correct": False},
            ]
        },
    )
    assert errors


def test_hq_activity_types_map_to_canonical_question_types():
    assert canonical_question_type("MATCHING") == "MATCHING"
    assert canonical_question_type("SHORT_ANSWER", {}) == "ESSAY"
    assert (
        canonical_question_type(
            "SHORT_ANSWER",
            {"accepted_answers": ["algoritmo"]},
        )
        == "SHORT_TEXT"
    )
    assert canonical_question_type("MATHEMATICS") == "ESSAY"


def test_canonical_answer_key_uses_authoring_payload_when_needed():
    assert canonical_answer_key(
        "ORDERING",
        {"items": ["analisar", "planejar", "executar"]},
        {},
    ) == {"items": ["analisar", "planejar", "executar"]}
    assert canonical_answer_key(
        "MATCHING",
        {"pairs": [{"left": "A", "right": "1"}]},
        {},
    ) == {"pairs": [{"left": "A", "right": "1"}]}


def test_student_payload_hides_multiple_choice_and_crossword_answers():
    multiple_choice = student_activity_payload(
        "MULTIPLE_CHOICE",
        {
            "options": [
                {"id": "A", "text": "Correta", "correct": True},
                {"id": "B", "text": "Incorreta", "correct": False},
            ]
        },
    )
    crossword = student_activity_payload(
        "CROSSWORD",
        {
            "entries": [
                {"answer": "ALGORITMO", "clue": "Sequencia de passos"}
            ]
        },
    )

    assert multiple_choice == {
        "options": [
            {"id": "A", "text": "Correta"},
            {"id": "B", "text": "Incorreta"},
        ],
        "selection_mode": "SINGLE",
    }
    assert "correct" not in multiple_choice["options"][0]
    assert crossword["entries"] == [
        {"id": "0", "clue": "Sequencia de passos", "length": 9}
    ]
    assert "answer" not in crossword["entries"][0]


def test_student_payload_does_not_reveal_matching_or_ordering_key():
    matching = student_activity_payload(
        "MATCHING",
        {
            "pairs": [
                {"left": "A", "right": "1"},
                {"left": "B", "right": "2"},
            ]
        },
    )
    ordering = student_activity_payload(
        "ORDERING",
        {"items": ["primeiro", "segundo", "terceiro"]},
    )

    assert [item["text"] for item in matching["right_items"]] == ["2", "1"]
    assert ordering["items"] == ["segundo", "terceiro", "primeiro"]


def test_fill_blanks_requires_one_answer_per_blank():
    errors = validate_answer_key(
        "FILL_BLANKS",
        {
            "blanks": [
                {"id": "1", "label": "Primeira"},
                {"id": "2", "label": "Segunda"},
            ]
        },
        {"answers": ["algoritmo"]},
    )

    assert errors == ["Cada lacuna deve possuir uma resposta no gabarito."]
