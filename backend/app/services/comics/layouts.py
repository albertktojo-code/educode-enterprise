from copy import deepcopy
from typing import TypedDict

from app.models.comic import PanelShape, PanelSize


class PanelLayout(TypedDict):
    shape: str
    size_category: str
    position_x: float
    position_y: float
    width: float
    height: float
    z_index: int


class LayoutTemplate(TypedDict):
    code: str
    label: str
    panel_count: int
    description: str
    panels: list[PanelLayout]


def _panel(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    shape: PanelShape = PanelShape.RECTANGLE,
    size: PanelSize = PanelSize.MEDIUM,
    z_index: int = 0,
) -> PanelLayout:
    return {
        "shape": shape.value,
        "size_category": size.value,
        "position_x": x,
        "position_y": y,
        "width": width,
        "height": height,
        "z_index": z_index,
    }


_LAYOUTS: dict[str, LayoutTemplate] = {
    "single_full": {
        "code": "single_full",
        "label": "Página inteira",
        "panel_count": 1,
        "description": "Um quadro grande para abertura, revelação ou encerramento.",
        "panels": [_panel(2, 2, 96, 96, size=PanelSize.FULL_PAGE)],
    },
    "two_horizontal": {
        "code": "two_horizontal",
        "label": "Dois horizontais",
        "panel_count": 2,
        "description": "Dois quadros largos empilhados.",
        "panels": [
            _panel(2, 2, 96, 46, shape=PanelShape.HORIZONTAL, size=PanelSize.LARGE),
            _panel(2, 52, 96, 46, shape=PanelShape.HORIZONTAL, size=PanelSize.LARGE),
        ],
    },
    "two_vertical": {
        "code": "two_vertical",
        "label": "Dois verticais",
        "panel_count": 2,
        "description": "Dois quadros verticais lado a lado.",
        "panels": [
            _panel(2, 2, 46, 96, shape=PanelShape.VERTICAL, size=PanelSize.LARGE),
            _panel(52, 2, 46, 96, shape=PanelShape.VERTICAL, size=PanelSize.LARGE),
        ],
    },
    "three_hero_top": {
        "code": "three_hero_top",
        "label": "Destaque superior",
        "panel_count": 3,
        "description": "Um quadro panorâmico e dois quadros menores.",
        "panels": [
            _panel(2, 2, 96, 48, shape=PanelShape.PANORAMIC, size=PanelSize.LARGE),
            _panel(2, 54, 46, 44, size=PanelSize.MEDIUM),
            _panel(52, 54, 46, 44, size=PanelSize.MEDIUM),
        ],
    },
    "three_hero_bottom": {
        "code": "three_hero_bottom",
        "label": "Destaque inferior",
        "panel_count": 3,
        "description": "Dois quadros menores e uma conclusão ampla.",
        "panels": [
            _panel(2, 2, 46, 42, size=PanelSize.MEDIUM),
            _panel(52, 2, 46, 42, size=PanelSize.MEDIUM),
            _panel(2, 48, 96, 50, shape=PanelShape.PANORAMIC, size=PanelSize.LARGE),
        ],
    },
    "grid_2x2": {
        "code": "grid_2x2",
        "label": "Grade 2 × 2",
        "panel_count": 4,
        "description": "Quatro quadros equilibrados.",
        "panels": [
            _panel(2, 2, 46, 46),
            _panel(52, 2, 46, 46),
            _panel(2, 52, 46, 46),
            _panel(52, 52, 46, 46),
        ],
    },
    "four_dramatic": {
        "code": "four_dramatic",
        "label": "Dramático",
        "panel_count": 4,
        "description": "Abertura ampla, detalhe circular, quadro vertical e fechamento.",
        "panels": [
            _panel(2, 2, 96, 32, shape=PanelShape.PANORAMIC, size=PanelSize.LARGE),
            _panel(4, 38, 28, 28, shape=PanelShape.CIRCLE, size=PanelSize.SMALL, z_index=1),
            _panel(36, 38, 62, 28, shape=PanelShape.HORIZONTAL, size=PanelSize.MEDIUM),
            _panel(2, 70, 96, 28, shape=PanelShape.HORIZONTAL, size=PanelSize.LARGE),
        ],
    },
    "five_dynamic": {
        "code": "five_dynamic",
        "label": "Cinco dinâmicos",
        "panel_count": 5,
        "description": "Ritmo rápido com um quadro central de destaque.",
        "panels": [
            _panel(2, 2, 30, 30, size=PanelSize.SMALL),
            _panel(35, 2, 63, 30, shape=PanelShape.HORIZONTAL, size=PanelSize.MEDIUM),
            _panel(2, 35, 63, 30, shape=PanelShape.HORIZONTAL, size=PanelSize.MEDIUM),
            _panel(68, 35, 30, 30, shape=PanelShape.CIRCLE, size=PanelSize.SMALL),
            _panel(2, 68, 96, 30, shape=PanelShape.PANORAMIC, size=PanelSize.LARGE),
        ],
    },
    "six_grid": {
        "code": "six_grid",
        "label": "Grade de seis",
        "panel_count": 6,
        "description": "Seis quadros para ação, investigação ou comédia rápida.",
        "panels": [
            _panel(2, 2, 30, 46, size=PanelSize.SMALL),
            _panel(35, 2, 30, 46, size=PanelSize.SMALL),
            _panel(68, 2, 30, 46, size=PanelSize.SMALL),
            _panel(2, 52, 30, 46, size=PanelSize.SMALL),
            _panel(35, 52, 30, 46, size=PanelSize.SMALL),
            _panel(68, 52, 30, 46, size=PanelSize.SMALL),
        ],
    },
}


def list_layout_templates() -> list[LayoutTemplate]:
    return [deepcopy(layout) for layout in _LAYOUTS.values()]


def layout_for(template_code: str, panel_count: int) -> list[PanelLayout]:
    template = _LAYOUTS.get(template_code)
    if template is not None and template["panel_count"] == panel_count:
        return deepcopy(template["panels"])
    matching = next(
        (layout for layout in _LAYOUTS.values() if layout["panel_count"] == panel_count),
        None,
    )
    if matching is not None:
        return deepcopy(matching["panels"])
    return free_grid(panel_count)


def recommended_template(panel_count: int, page_number: int, page_total: int) -> str:
    if panel_count == 1:
        return "single_full"
    if page_number == 1 and panel_count == 3:
        return "three_hero_top"
    if page_number == page_total and panel_count == 3:
        return "three_hero_bottom"
    if panel_count == 4 and page_number == max(2, page_total - 1):
        return "four_dramatic"
    mapping = {
        2: "two_horizontal",
        3: "three_hero_top",
        4: "grid_2x2",
        5: "five_dynamic",
        6: "six_grid",
    }
    return mapping.get(panel_count, "custom")


def free_grid(panel_count: int) -> list[PanelLayout]:
    columns = 1 if panel_count == 1 else 2 if panel_count <= 4 else 3
    rows = (panel_count + columns - 1) // columns
    gap = 3.0
    width = (100.0 - gap * (columns + 1)) / columns
    height = (100.0 - gap * (rows + 1)) / rows
    panels: list[PanelLayout] = []
    for index in range(panel_count):
        row = index // columns
        column = index % columns
        panels.append(
            _panel(
                gap + column * (width + gap),
                gap + row * (height + gap),
                width,
                height,
                size=PanelSize.MEDIUM,
            )
        )
    return panels
