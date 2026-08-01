import uuid

import pytest
from pydantic import ValidationError

from app.comic_layout_studio.schemas import (
    CanvasDocumentCreate,
    CanvasTransform,
    GroupCreate,
    LayerCreate,
    ReorderLayersRequest,
)


def test_canvas_document_accepts_a4_geometry():
    item = CanvasDocumentCreate(
        comic_project_id=uuid.uuid4(),
        page_id=uuid.uuid4(),
        name="Pagina livre",
    )
    assert item.dpi == 300
    assert item.bleed_mm == 3


def test_canvas_document_rejects_excessive_safe_margin():
    with pytest.raises(ValidationError):
        CanvasDocumentCreate(
            comic_project_id=uuid.uuid4(),
            page_id=uuid.uuid4(),
            name="Pagina invalida",
            page_width=20,
            page_height=20,
            safe_margin_mm=10,
        )


def test_transform_rejects_zero_dimensions():
    with pytest.raises(ValidationError):
        CanvasTransform(x=0, y=0, width=0, height=10)


def test_layer_create_has_separate_content_and_style():
    item = LayerCreate(
        layer_type="SPEECH_BALLOON",
        name="Fala principal",
        transform=CanvasTransform(x=10, y=10, width=60, height=30),
        content={"text": "Ola"},
        style={"font_size": 14},
    )
    assert item.content["text"] == "Ola"
    assert item.style["font_size"] == 14


def test_reorder_layers_rejects_duplicates():
    layer_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        ReorderLayersRequest(layer_ids=[layer_id, layer_id])


def test_group_requires_two_unique_layers():
    with pytest.raises(ValidationError):
        GroupCreate(name="Grupo", layer_ids=[uuid.uuid4()])
