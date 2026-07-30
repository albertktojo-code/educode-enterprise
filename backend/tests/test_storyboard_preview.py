from uuid import uuid4

from app.models.comic import (
    BalloonType,
    ComicBalloon,
    ComicPage,
    ComicPanel,
    ComicVersion,
    GeneratedComic,
    PreviewReviewStatus,
)
from app.services.comics.preview import (
    build_storyboard,
    compare_version_snapshots,
    validate_preview,
)


def _comic() -> GeneratedComic:
    comic = GeneratedComic(
        id=uuid4(),
        organization_id=uuid4(),
        generation_project_id=uuid4(),
        rag_context_id=uuid4(),
        created_by_user_id=uuid4(),
        created_by_name_snapshot="Professor",
        title="O mistério dos padrões",
        continuity_score=90,
        pedagogical_score=85,
    )
    page = ComicPage(
        id=uuid4(),
        comic_id=comic.id,
        page_number=1,
        panel_count=2,
        preview_review_status=PreviewReviewStatus.APPROVED,
    )
    clue = ComicPanel(
        id=uuid4(),
        page_id=page.id,
        panel_number=1,
        reading_order=1,
        scene_description="Lia encontra números repetidos.",
        narrative_goal="Introduzir uma pista.",
        pedagogical_goal="Reconhecer padrões.",
        plot_function="clue",
        emotion="curiosity",
        visual_prompt={"shot_type": "close", "transition": "corte"},
        preview_review_status=PreviewReviewStatus.APPROVED,
        alt_text="Lia observa uma sequência.",
        image_asset_path="/assets/clue.png",
    )
    clue.balloons = [
        ComicBalloon(
            id=uuid4(),
            panel_id=clue.id,
            sequence_number=1,
            balloon_type=BalloonType.SPEECH,
            speaker_name_snapshot="Lia",
            text="Os números estão se repetindo!",
        )
    ]
    twist = ComicPanel(
        id=uuid4(),
        page_id=page.id,
        panel_number=2,
        reading_order=2,
        scene_description="A repetição revela uma mensagem.",
        narrative_goal="Apresentar a reviravolta.",
        pedagogical_goal="Aplicar o padrão encontrado.",
        plot_function="plot_twist",
        emotion="surprise",
        preview_review_status=PreviewReviewStatus.APPROVED,
        alt_text="A sequência forma uma mensagem.",
        image_asset_path="/assets/twist.png",
    )
    twist.balloons = []
    page.panels = [clue, twist]
    comic.pages = [page]
    comic.review_comments = []
    return comic


def test_storyboard_is_derived_in_reading_order() -> None:
    result = build_storyboard(_comic())
    assert result["scene_count"] == 2
    assert result["scenes"][0]["plot_function"] == "clue"
    assert result["scenes"][1]["plot_function"] == "plot_twist"
    assert result["plot_points"][0]["page_number"] == 1


def test_preview_validation_accepts_clue_before_twist() -> None:
    result = validate_preview(_comic())
    assert not any(item["code"] == "plot_twist_without_clue" for item in result["findings"])
    assert result["review_coverage_percent"] == 100.0


def test_version_comparison_reports_changed_panel_fields() -> None:
    page_id = str(uuid4())
    panel_id = str(uuid4())
    before = ComicVersion(
        comic_id=uuid4(),
        version_number=1,
        scope="initial",
        change_description="Inicial",
        snapshot_json={
            "title": "A",
            "pages": [
                {
                    "id": page_id,
                    "page_number": 1,
                    "panels": [
                        {"id": panel_id, "scene_description": "Antes"}
                    ],
                }
            ],
        },
        created_by_user_id=uuid4(),
    )
    after = ComicVersion(
        comic_id=before.comic_id,
        version_number=2,
        scope="panel",
        change_description="Quadro alterado",
        snapshot_json={
            "title": "A",
            "pages": [
                {
                    "id": page_id,
                    "page_number": 1,
                    "panels": [
                        {"id": panel_id, "scene_description": "Depois"}
                    ],
                }
            ],
        },
        created_by_user_id=uuid4(),
    )
    result = compare_version_snapshots(before, after)
    assert result["changed_pages"][0]["panel_changes"][0]["changed_fields"] == [
        "scene_description"
    ]
