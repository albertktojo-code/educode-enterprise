import uuid

import pytest
from pydantic import ValidationError

from app.comic_visual_library.schemas import CharacterCreate, GenerationBatchCreate, LibraryCreate


def test_library_scope_is_normalized():
    item = LibraryCreate(code="my-lib", name="Minha biblioteca", scope="personal")
    assert item.scope == "PERSONAL"


def test_character_requires_stable_identity():
    with pytest.raises(ValidationError):
        CharacterCreate(
            library_id=uuid.uuid4(),
            name="Luna",
            slug="luna",
            identity_profile={"favorite_color": "blue"},
        )


def test_character_slug_validation():
    with pytest.raises(ValidationError):
        CharacterCreate(
            library_id=uuid.uuid4(),
            name="Luna",
            slug="Luna Principal",
            identity_profile={"hair": "black"},
        )


def test_batch_rejects_duplicate_panels():
    panel_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        GenerationBatchCreate(
            comic_project_id=uuid.uuid4(),
            name="Gerar pagina",
            items=[
                {"page_id": uuid.uuid4(), "panel_id": panel_id},
                {"page_id": uuid.uuid4(), "panel_id": panel_id},
            ],
        )


def test_library_rejects_unknown_scope():
    with pytest.raises(ValidationError):
        LibraryCreate(code="x1", name="Biblioteca", scope="PUBLIC")


def test_batch_accepts_distinct_panels():
    item = GenerationBatchCreate(
        comic_project_id=uuid.uuid4(),
        name="Gerar quadros",
        items=[
            {"page_id": uuid.uuid4(), "panel_id": uuid.uuid4()},
            {"page_id": uuid.uuid4(), "panel_id": uuid.uuid4()},
        ],
    )
    assert len(item.items) == 2
