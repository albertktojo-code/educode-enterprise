from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.pedagogy import SourceMode, SourceType
from app.schemas.pedagogy import GenerationProjectCreate


def base_payload() -> dict[str, object]:
    return {
        "title": "Projeto interdisciplinar",
        "source_mode": SourceMode.AI,
        "custom_subject_name": "Educação Financeira",
        "topic": "Planejamento de orçamento",
        "desired_materials": ["comic", "quiz"],
        "pillars": [{"pillar_id": uuid4(), "relevance": "high"}],
        "sources": [{"source_type": SourceType.AI_KNOWLEDGE}],
    }


def test_ai_generation_project_accepts_custom_subject() -> None:
    project = GenerationProjectCreate.model_validate(base_payload())
    assert project.source_mode == SourceMode.AI
    assert project.custom_subject_name == "Educação Financeira"
    assert project.desired_materials == ["comic", "quiz"]


def test_teacher_text_mode_requires_teacher_story() -> None:
    payload = base_payload()
    payload["source_mode"] = SourceMode.TEACHER_TEXT
    payload["sources"] = [{"source_type": SourceType.TEACHER_TEXT}]

    with pytest.raises(ValidationError, match="história do professor"):
        GenerationProjectCreate.model_validate(payload)


def test_document_mode_requires_pdf_source() -> None:
    payload = base_payload()
    payload["source_mode"] = SourceMode.DOCUMENT
    payload["sources"] = []

    with pytest.raises(ValidationError, match="ao menos um PDF"):
        GenerationProjectCreate.model_validate(payload)


def test_hybrid_mode_requires_two_sources() -> None:
    payload = base_payload()
    payload["source_mode"] = SourceMode.HYBRID
    payload["sources"] = [{"source_type": SourceType.AI_KNOWLEDGE}]

    with pytest.raises(ValidationError, match="pelo menos duas fontes"):
        GenerationProjectCreate.model_validate(payload)
