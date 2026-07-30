from app.models.studio import PedagogicalPackage, StudioMaterialType, TeacherStudioDraft
from app.schemas.studio import RecommendPagesRequest
from app.services.teacher_studio import (
    SYSTEM_ART_PRESETS,
    material_content,
    publication_checklist,
    recommend_page_plan,
)


def test_page_plan_is_multipage_and_ordered() -> None:
    plan = recommend_page_plan(
        RecommendPagesRequest(
            story_pages=6,
            include_cover=True,
            include_exercises=True,
            include_answer_key=True,
            include_teacher_guide=True,
        )
    )
    assert [page["page_number"] for page in plan] == list(range(1, len(plan) + 1))
    assert plan[0]["role"] == "cover"
    assert sum(page["role"] == "story" for page in plan) == 6
    assert plan[-1]["role"] == "teacher_guide"
    assert all(1 <= int(page["panel_count"]) <= 8 for page in plan)


def test_art_presets_keep_text_outside_images() -> None:
    assert len(SYSTEM_ART_PRESETS) >= 8
    assert {preset["category"] for preset in SYSTEM_ART_PRESETS} >= {
        "manga",
        "american",
        "anime",
        "cartoon",
    }
    assert all(preset["visual_rules"]["text_in_image"] is False for preset in SYSTEM_ART_PRESETS)


def test_package_materials_share_pedagogical_context() -> None:
    draft = TeacherStudioDraft(
        title="Missão das Frações",
        subject_name="Matemática",
        school_year="6º ano",
        topic="Frações equivalentes",
        objective="Reconhecer equivalências.",
    )
    comic = material_content(StudioMaterialType.COMIC, draft)
    quiz = material_content(StudioMaterialType.QUIZ, draft)
    assert comic["topic"] == quiz["topic"]
    assert comic["objective"] == quiz["objective"]
    assert quiz["question_count"] == 5


def test_publication_requires_generated_materials() -> None:
    package = PedagogicalPackage(
        title="Pacote",
        outputs=["comic"],
        shared_context={"topic": "Frações"},
        art_direction_snapshot={"preset_code": "manga_educational"},
    )
    readiness, checklist = publication_checklist(package, None)
    assert readiness.value == "not_ready"
    assert any(item["code"] == "materials" and not item["passed"] for item in checklist)
