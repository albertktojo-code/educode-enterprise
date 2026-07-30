from uuid import uuid4

from app.models.comic import (
    BalloonType,
    ComicBalloon,
    ComicPage,
    ComicPanel,
    GeneratedComic,
    GenerationScope,
)
from app.services.comics.stability import (
    analyze_stability,
    canvas_readiness,
    regeneration_policy,
)


def _comic() -> GeneratedComic:
    comic = GeneratedComic(
        id=uuid4(),
        organization_id=uuid4(),
        generation_project_id=uuid4(),
        rag_context_id=uuid4(),
        created_by_user_id=uuid4(),
        created_by_name_snapshot="Professor",
        title="HQ estável",
        story_state={
            "facts_used": ["Frações equivalentes representam a mesma quantidade."],
            "characters": ["Lia"],
        },
    )
    page = ComicPage(id=uuid4(), comic_id=comic.id, page_number=1, panel_count=1)
    panel = ComicPanel(
        id=uuid4(),
        page_id=page.id,
        panel_number=1,
        reading_order=1,
        position_x=0,
        position_y=0,
        width=100,
        height=100,
        visual_prompt={"image_without_balloons": True},
        frozen_assets={"characters": [{"name": "Lia", "version_id": "v1"}]},
        alt_text="Lia observa duas frações no quadro.",
        locked_elements=["pedagogical_goal"],
    )
    panel.balloons = [
        ComicBalloon(
            id=uuid4(),
            panel_id=panel.id,
            sequence_number=1,
            speaker_name_snapshot="Lia",
            balloon_type=BalloonType.SPEECH,
            text="As duas representações ocupam a mesma quantidade.",
            width=35,
            height=18,
        )
    ]
    page.panels = [panel]
    comic.pages = [page]
    comic.review_comments = []
    comic.review_approvals = []
    return comic


def test_stability_report_measures_language_and_density() -> None:
    report = analyze_stability(_comic())
    assert report["score"] > 70
    assert report["language_metrics"]["word_count"] > 0
    assert report["page_densities"][0]["classification"] in {"low", "moderate", "high"}


def test_stability_flags_speech_without_character() -> None:
    comic = _comic()
    comic.pages[0].panels[0].balloons[0].speaker_name_snapshot = None
    report = analyze_stability(comic)
    assert any(item["code"] == "missing_balloon_speaker" for item in report["findings"])


def test_canvas_readiness_requires_review_approvals() -> None:
    report = canvas_readiness(_comic())
    assert report["status"] == "not_ready"
    review_item = next(item for item in report["checklist"] if item["code"] == "reviews")
    assert review_item["passed"] is False


def test_regeneration_policy_preserves_locks_and_facts() -> None:
    comic = _comic()
    panel = comic.pages[0].panels[0]
    policy = regeneration_policy(
        comic,
        scope=GenerationScope.PANEL,
        page_id=None,
        panel_id=panel.id,
        preserve_dialogue=True,
        preserve_scene=False,
    )
    assert panel.id in policy["affected_panel_ids"]
    assert "dialogue" in policy["locked_elements"]
    assert policy["immutable_facts"]


def test_regeneration_policy_from_panel_includes_following_panels() -> None:
    comic = _comic()
    page = comic.pages[0]
    second = ComicPanel(
        id=uuid4(),
        page_id=page.id,
        panel_number=2,
        reading_order=2,
        visual_prompt={"image_without_balloons": True},
        frozen_assets={"characters": [{"name": "Lia"}]},
        alt_text="Continuação.",
    )
    second.balloons = []
    page.panels.append(second)
    page.panel_count = 2
    policy = regeneration_policy(
        comic,
        scope=GenerationScope.FROM_PANEL,
        page_id=None,
        panel_id=page.panels[0].id,
        preserve_dialogue=False,
        preserve_scene=False,
    )
    assert len(policy["affected_panel_ids"]) == 2
    assert policy["warnings"]
