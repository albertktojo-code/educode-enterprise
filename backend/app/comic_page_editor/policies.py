from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

PLAYFUL_MESSAGES = [
    "Os personagens estao ensaiando suas falas...",
    "Organizando os quadros para ninguem sair da pagina...",
    "Ajustando os superpoderes pedagogicos...",
    "Conferindo se a BNCC participa da aventura...",
    "Dando os ultimos retoques no cenario...",
]


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_grid_definition(grid: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    panels = grid.get("panels")
    if not isinstance(panels, list) or not panels:
        return ["GRID_REQUIRES_PANELS"]
    if len(panels) > 12:
        errors.append("TOO_MANY_PANELS")
    occupied_area = 0.0
    for index, panel in enumerate(panels, start=1):
        for key in ("x", "y", "width", "height"):
            value = panel.get(key)
            if not isinstance(value, (int, float)) or value < 0 or value > 1:
                errors.append(f"PANEL_{index}_{key.upper()}_OUT_OF_RANGE")
        x = float(panel.get("x", 0))
        y = float(panel.get("y", 0))
        width = float(panel.get("width", 0))
        height = float(panel.get("height", 0))
        if width <= 0 or height <= 0 or x + width > 1.0001 or y + height > 1.0001:
            errors.append(f"PANEL_{index}_OUTSIDE_PAGE")
        occupied_area += max(0.0, width * height)
    if occupied_area > 1.15:
        errors.append("PANEL_AREA_SUGGESTS_OVERLAP")
    return sorted(set(errors))


def aspect_ratio_for_panel(width: float, height: float) -> str:
    ratio = width / height if height else 1.0
    if ratio >= 1.7:
        return "16:9"
    if ratio >= 1.25:
        return "4:3"
    if ratio <= 0.6:
        return "9:16"
    if ratio <= 0.8:
        return "3:4"
    return "1:1"


def apply_locked_elements(previous: dict[str, Any], requested: dict[str, Any], locked: list[str]) -> dict[str, Any]:
    result = deepcopy(requested)
    for key in locked:
        if key in previous:
            result[key] = deepcopy(previous[key])
    return result


def calculate_progress(steps: list[dict[str, Any]]) -> int:
    if not steps:
        return 0
    total = sum(max(1, int(item.get("progress_weight", 1))) for item in steps)
    completed = 0
    for item in steps:
        weight = max(1, int(item.get("progress_weight", 1)))
        status = str(item.get("status", "PENDING")).upper()
        if status in {"COMPLETED", "SKIPPED"}:
            completed += weight
        elif status == "RUNNING":
            completed += weight * 0.5
    return min(100, round((completed / total) * 100))


def select_playful_message(seed: str, step_order: int) -> str:
    digest = int(hashlib.sha256(f"{seed}:{step_order}".encode()).hexdigest()[:8], 16)
    return PLAYFUL_MESSAGES[digest % len(PLAYFUL_MESSAGES)]


def validate_accessibility_payload(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if payload.get("contains_image") and not payload.get("alt_text"):
        warnings.append("ALT_TEXT_REQUIRED")
    if payload.get("text_font_size", 16) < 14:
        warnings.append("TEXT_TOO_SMALL")
    if payload.get("uses_color_only"):
        warnings.append("COLOR_ONLY_MEANING")
    if payload.get("reading_order") is None:
        warnings.append("READING_ORDER_REQUIRED")
    return warnings


def reorder_page_numbers(page_ids: list[str]) -> dict[str, int]:
    if len(page_ids) != len(set(page_ids)):
        raise ValueError("PAGE_IDS_MUST_BE_UNIQUE")
    return {page_id: index for index, page_id in enumerate(page_ids, start=1)}


PRESERVATION_LABELS = {
    "character": "Personagem",
    "outfit": "Roupa",
    "scenario": "Cenário",
    "framing": "Enquadramento",
    "expression": "Expressão",
    "palette": "Paleta",
    "style": "Estilo visual",
}

STAGE_LAYOUTS = {
    "OPENING": "GRID_OPENING_SCENE",
    "CONTEXT": "GRID_FEATURE_THREE",
    "DEVELOPMENT": "GRID_EQUAL_FOUR",
    "INVESTIGATION": "GRID_DYNAMIC_COLUMNS",
    "EXPLANATION": "GRID_NARRATIVE_MOSAIC",
    "CLIMAX": "GRID_ACTION_PAGE",
    "RESOLUTION": "GRID_CINEMATIC_STRIPS",
}


def narrative_stage(
    page_number: int,
    total_pages: int,
    pacing: str = "BALANCED",
) -> str:
    if total_pages <= 1:
        return "OPENING"
    progress = (page_number - 1) / max(1, total_pages - 1)
    normalized = pacing.upper()
    if progress <= 0.08:
        return "OPENING"
    if normalized == "FAST":
        if progress < 0.25:
            return "CONTEXT"
        if progress < 0.58:
            return "DEVELOPMENT"
        if progress < 0.78:
            return "CLIMAX"
        return "RESOLUTION"
    if normalized == "SLOW":
        if progress < 0.28:
            return "CONTEXT"
        if progress < 0.56:
            return "INVESTIGATION"
        if progress < 0.78:
            return "EXPLANATION"
        if progress < 0.92:
            return "CLIMAX"
        return "RESOLUTION"
    if normalized == "CINEMATIC":
        if progress < 0.20:
            return "CONTEXT"
        if progress < 0.52:
            return "DEVELOPMENT"
        if progress < 0.72:
            return "INVESTIGATION"
        if progress < 0.90:
            return "CLIMAX"
        return "RESOLUTION"
    if progress < 0.20:
        return "CONTEXT"
    if progress < 0.52:
        return "DEVELOPMENT"
    if progress < 0.72:
        return "INVESTIGATION"
    if progress < 0.88:
        return "CLIMAX"
    return "RESOLUTION"


def recommended_layout_code(stage: str) -> str:
    return STAGE_LAYOUTS.get(stage, "GRID_EQUAL_FOUR")


def split_story_segments(text: str) -> list[str]:
    import re

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    paragraphs = [
        item.strip(" -\t")
        for item in re.split(r"(?m)\n{2,}|^\s*(?:p[aá]gina|quadro|cena)\s+\d+\s*[:.-]\s*", normalized)
        if item.strip()
    ]
    if len(paragraphs) >= 3:
        return paragraphs
    sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+", normalized)
        if item.strip()
    ]
    return sentences or paragraphs


def _chunk_segments(
    segments: list[str],
    target_count: int,
) -> list[str]:
    if target_count <= 0:
        return []
    if not segments:
        return ["Cena a definir"] * target_count
    if len(segments) == target_count:
        return segments
    if len(segments) < target_count:
        result: list[str] = []
        for index in range(target_count):
            source = segments[min(len(segments) - 1, index * len(segments) // target_count)]
            suffix = (
                ""
                if index < len(segments)
                else f" — continuação {index - len(segments) + 1}"
            )
            result.append(f"{source}{suffix}")
        return result
    result = []
    for index in range(target_count):
        start = round(index * len(segments) / target_count)
        end = round((index + 1) * len(segments) / target_count)
        chunk = segments[start:max(start + 1, end)]
        result.append(" ".join(chunk))
    return result


def build_story_distribution(
    *,
    source_text: str,
    page_capacities: list[int],
    narrative_pacing: str,
) -> list[dict[str, Any]]:
    total_pages = len(page_capacities)
    total_panels = sum(max(1, count) for count in page_capacities)
    segments = _chunk_segments(
        split_story_segments(source_text),
        total_panels,
    )
    cursor = 0
    plan: list[dict[str, Any]] = []
    for page_index, panel_count in enumerate(page_capacities, start=1):
        count = max(1, panel_count)
        stage = narrative_stage(
            page_index,
            total_pages,
            narrative_pacing,
        )
        page_panels = []
        for panel_order in range(1, count + 1):
            summary = segments[cursor] if cursor < len(segments) else "Cena a definir"
            page_panels.append(
                {
                    "panel_order": panel_order,
                    "scene_summary": summary,
                    "narrative_function": stage.lower(),
                    "global_panel_order": cursor + 1,
                }
            )
            cursor += 1
        plan.append(
            {
                "page_number": page_index,
                "stage": stage,
                "panel_count": count,
                "recommended_layout_code": recommended_layout_code(stage),
                "panels": page_panels,
            }
        )
    return plan


def story_generation_payload(
    *,
    summary: str,
    total_pages: int,
    page_capacities: list[int],
    narrative_pacing: str,
    continuity_constraints: dict[str, Any],
    generation_instructions: dict[str, Any],
) -> dict[str, Any]:
    return {
        "purpose": "comic_script",
        "short_summary": summary,
        "total_pages": total_pages,
        "page_capacities": page_capacities,
        "total_panels": sum(page_capacities),
        "narrative_pacing": narrative_pacing,
        "continuity_constraints": continuity_constraints,
        "generation_instructions": generation_instructions,
        "requirements": [
            "Distribuir a narrativa por todas as páginas configuradas.",
            "Respeitar o número real de quadros de cada página.",
            "Não repetir o mesmo layout obrigatoriamente.",
            "Manter continuidade de personagem, roupa, cenário e paleta.",
            "Retornar roteiro completo e plano por página e quadro.",
            "Não incorporar texto dentro das imagens.",
        ],
        "output_schema": {
            "title": "string",
            "full_script": "string",
            "pages": [
                {
                    "page_number": "integer",
                    "stage": "string",
                    "panels": [
                        {
                            "panel_order": "integer",
                            "scene_summary": "string",
                            "visual_prompt": "string",
                            "dialogue": "string",
                        }
                    ],
                }
            ],
        },
    }


def merge_panel_content(
    previous_panels: list[dict[str, Any]],
    new_rectangles: list[dict[str, Any]],
    preserve_content: bool,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, rect in enumerate(new_rectangles):
        previous = previous_panels[index] if index < len(previous_panels) else {}
        result.append(
            {
                **rect,
                "panel_order": index + 1,
                "scene_summary": (
                    previous.get("scene_summary", "")
                    if preserve_content
                    else ""
                ),
                "visual_prompt": (
                    previous.get("visual_prompt", "")
                    if preserve_content
                    else ""
                ),
                "locked_elements": (
                    list(previous.get("locked_elements", []))
                    if preserve_content
                    else []
                ),
                "pedagogical_metadata": (
                    dict(previous.get("pedagogical_metadata", {}))
                    if preserve_content
                    else {}
                ),
                "accessibility_metadata": (
                    dict(previous.get("accessibility_metadata", {}))
                    if preserve_content
                    else {}
                ),
            }
        )
    return result


COVER_COMPOSITIONS = {
    "CINEMATIC": {
        "label": "Cinematográfica",
        "description": "Imagem em tela cheia, título superior e personagens no terço inferior.",
        "title_zone": {"x": 0.08, "y": 0.06, "width": 0.84, "height": 0.18},
        "image_focus": {"x": 0.5, "y": 0.58},
    },
    "CHARACTER_FOCUS": {
        "label": "Personagem em destaque",
        "description": "Protagonista central com título lateral ou superior.",
        "title_zone": {"x": 0.06, "y": 0.08, "width": 0.52, "height": 0.2},
        "image_focus": {"x": 0.62, "y": 0.55},
    },
    "EDUCATIONAL": {
        "label": "Educacional",
        "description": "Título, tema, disciplina e identificação escolar em composição clara.",
        "title_zone": {"x": 0.08, "y": 0.06, "width": 0.84, "height": 0.16},
        "image_focus": {"x": 0.5, "y": 0.5},
    },
    "MINIMALIST": {
        "label": "Minimalista",
        "description": "Objeto ou símbolo central, fundo limpo e título amplo.",
        "title_zone": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.2},
        "image_focus": {"x": 0.5, "y": 0.56},
    },
    "DIAGONAL": {
        "label": "Composição diagonal",
        "description": "Personagem e desafio em lados opostos com movimento visual.",
        "title_zone": {"x": 0.07, "y": 0.05, "width": 0.7, "height": 0.18},
        "image_focus": {"x": 0.5, "y": 0.55},
    },
    "ENSEMBLE": {
        "label": "Grupo de personagens",
        "description": "Elenco principal reunido com título central.",
        "title_zone": {"x": 0.08, "y": 0.05, "width": 0.84, "height": 0.16},
        "image_focus": {"x": 0.5, "y": 0.6},
    },
}


def default_cover_layers(title: str = "") -> list[dict[str, Any]]:
    return [
        {
            "id": "cover-title",
            "layer_type": "TITLE",
            "content": title,
            "x": 0.08,
            "y": 0.06,
            "width": 0.84,
            "height": 0.16,
            "visible": True,
            "style": {
                "font_size": 64,
                "font_weight": 900,
                "color": "#ffffff",
                "align": "center",
                "shadow": True,
                "outline": True,
            },
        },
        {
            "id": "cover-subtitle",
            "layer_type": "SUBTITLE",
            "content": "",
            "x": 0.12,
            "y": 0.23,
            "width": 0.76,
            "height": 0.08,
            "visible": True,
            "style": {
                "font_size": 28,
                "font_weight": 700,
                "color": "#ffffff",
                "align": "center",
            },
        },
        {
            "id": "cover-credits",
            "layer_type": "CREDITS",
            "content": "",
            "x": 0.08,
            "y": 0.9,
            "width": 0.84,
            "height": 0.06,
            "visible": True,
            "style": {
                "font_size": 18,
                "font_weight": 600,
                "color": "#ffffff",
                "align": "center",
            },
        },
    ]


def cover_generation_payload(
    *,
    composition_code: str,
    title: str,
    summary: str,
    discipline: str,
    theme: str,
    continuity: dict[str, Any],
    preservation: dict[str, Any],
    variation_count: int,
    additional_instructions: str,
) -> dict[str, Any]:
    return {
        "purpose": "comic_cover",
        "composition": COVER_COMPOSITIONS[composition_code],
        "title_context": title,
        "story_summary": summary,
        "discipline": discipline,
        "theme": theme,
        "continuity": continuity,
        "preservation": preservation,
        "variation_count": variation_count,
        "additional_instructions": additional_instructions,
        "mandatory_rules": [
            "Não inserir letras, palavras, títulos, logotipos ou marcas na imagem.",
            "Reservar área visual limpa para o título editável.",
            "Manter aparência e roupas dos personagens salvos.",
            "Manter estilo visual e paleta compatíveis com as páginas internas.",
            "Gerar imagem vertical com sangria e área segura.",
        ],
    }


def continuity_issues(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    tracked = (
        "character",
        "outfit",
        "scenario",
        "important_object",
        "time_of_day",
        "palette",
    )
    previous: dict[str, Any] | None = None
    for row in rows:
        if previous is not None:
            for key in tracked:
                left = str(previous.get(key, "")).strip()
                right = str(row.get(key, "")).strip()
                if left and right and left != right:
                    issues.append(
                        {
                            "type": "CONTINUITY_CHANGE",
                            "field": key,
                            "from_page": previous.get("page_number"),
                            "to_page": row.get("page_number"),
                            "from_value": left,
                            "to_value": right,
                            "message": (
                                f"{key} mudou entre as páginas "
                                f"{previous.get('page_number')} e "
                                f"{row.get('page_number')}."
                            ),
                        }
                    )
        previous = row
    return issues
