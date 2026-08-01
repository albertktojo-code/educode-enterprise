from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from app.models.creative import CreativeItemKind
from app.schemas.creative import (
    CreativeItemCreate,
    TeachingSequenceCreate,
    TeachingSequenceItemInput,
)
from app.services.creative.storage import CreativeStorage


def test_creative_item_schema_accepts_structured_profile() -> None:
    item = CreativeItemCreate(
        kind=CreativeItemKind.CHARACTER,
        name="Lia",
        description="Protagonista curiosa.",
        profile_data={
            "age_range": "11 a 13 anos",
            "mandatory_features": ["mochila azul"],
        },
        rights_confirmed=True,
    )

    assert item.kind == CreativeItemKind.CHARACTER
    assert item.profile_data["age_range"] == "11 a 13 anos"


def test_teaching_sequence_rejects_duplicate_positions() -> None:
    with pytest.raises(ValidationError):
        TeachingSequenceCreate(
            title="Sequência de Frações",
            items=[
                TeachingSequenceItemInput(
                    position=0,
                    title="Pré-teste",
                    material_type="quiz",
                ),
                TeachingSequenceItemInput(
                    position=0,
                    title="HQ",
                    material_type="comic",
                ),
            ],
        )


@pytest.mark.asyncio
async def test_creative_storage_saves_valid_png(tmp_path) -> None:
    storage = CreativeStorage(tmp_path, max_size_bytes=1024 * 1024)
    upload = UploadFile(
        filename="personagem.png",
        file=BytesIO(b"\x89PNG\r\n\x1a\n" + b"mock-image-content"),
        headers={"content-type": "image/png"},
    )

    stored = await storage.save(upload, uuid4())

    assert stored.mime_type == "image/png"
    assert storage.resolve(stored.storage_key).exists()
