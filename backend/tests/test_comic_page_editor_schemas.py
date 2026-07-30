import pytest
from pydantic import ValidationError

from app.comic_page_editor.schemas import GridDefinition, PanelRect, ReorderPagesRequest, TextLayerCreate


def test_panel_must_stay_inside_page():
    with pytest.raises(ValidationError):
        PanelRect(x=0.9, y=0, width=0.2, height=0.5)


def test_grid_requires_panels():
    with pytest.raises(ValidationError):
        GridDefinition(panels=[])


def test_text_layer_requires_content():
    with pytest.raises(ValidationError):
        TextLayerCreate(layer_type="SPEECH", content="")


def test_reorder_rejects_duplicates():
    from uuid import uuid4
    item = uuid4()
    with pytest.raises(ValidationError):
        ReorderPagesRequest(page_ids=[item, item])
