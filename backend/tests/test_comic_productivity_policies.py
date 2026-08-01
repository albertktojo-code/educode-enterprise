from app.comic_page_editor.productivity import (
    compare_snapshot_payloads,
    narrative_rhythm_analysis,
)


def test_rhythm_analysis_detects_page_count_and_dense_pages():
    result = narrative_rhythm_analysis(
        pages=[
            {
                "page_type": "STORY",
                "panel_count": 4,
                "stage": "OPENING",
            },
            {
                "page_type": "STORY",
                "panel_count": 10,
                "stage": "DEVELOPMENT",
            },
            {
                "page_type": "STORY",
                "panel_count": 4,
                "stage": "CLIMAX",
            },
        ],
        expected_total=4,
    )
    codes = {item["code"] for item in result["warnings"]}
    assert "STORY_PAGE_COUNT_MISMATCH" in codes
    assert "DENSE_PAGE" in codes
    assert result["status"] == "BLOCKED"


def test_snapshot_comparison_reports_changed_pages_and_story_fields():
    left = {
        "pages": [
            {
                "id": "page-1",
                "pageType": "STORY",
                "pageNumber": 1,
                "panels": [{"id": "panel-1"}],
            }
        ],
        "storyPlan": {
            "totalPages": 1,
            "narrativePacing": "BALANCED",
        },
    }
    right = {
        "pages": [
            {
                "id": "page-1",
                "pageType": "STORY",
                "pageNumber": 1,
                "panels": [
                    {"id": "panel-1"},
                    {"id": "panel-2"},
                ],
            }
        ],
        "storyPlan": {
            "totalPages": 1,
            "narrativePacing": "FAST",
        },
    }
    result = compare_snapshot_payloads(left, right)
    assert result["changed_page_ids"] == ["page-1"]
    assert "narrativePacing" in result["story_plan_changed_fields"]
    assert result["identical"] is False
