import pytest
from pydantic import ValidationError

from app.comic_page_editor.schemas import (
    StoryGenerateRequest,
    StoryPlanUpsert,
)


def test_manual_story_accepts_complete_script():
    item = StoryPlanUpsert(
        source_mode="MANUAL",
        total_pages=8,
        full_script="Página 1: apresentação. Página 2: desenvolvimento.",
    )
    assert item.total_pages == 8
    assert item.narrative_pacing == "BALANCED"


def test_ai_story_requires_meaningful_summary():
    item = StoryGenerateRequest(
        total_pages=12,
        narrative_pacing="CINEMATIC",
        short_summary=(
            "Uma turma resolve um desafio de pensamento computacional."
        ),
    )
    assert item.total_pages == 12

    with pytest.raises(ValidationError):
        StoryGenerateRequest(
            total_pages=8,
            short_summary="curto",
        )


def test_story_page_limits_and_modes_are_validated():
    with pytest.raises(ValidationError):
        StoryPlanUpsert(
            source_mode="MANUAL",
            total_pages=0,
            full_script="Roteiro",
        )

    with pytest.raises(ValidationError):
        StoryPlanUpsert(
            source_mode="AI_SUMMARY",
            short_summary="pequeno",
        )

    with pytest.raises(ValidationError):
        StoryPlanUpsert(
            source_mode="MANUAL",
            full_script="Roteiro",
            narrative_pacing="RANDOM",
        )
