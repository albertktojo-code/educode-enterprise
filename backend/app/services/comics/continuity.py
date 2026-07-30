from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ContinuityFinding:
    severity: str
    code: str
    message: str
    page_id: UUID | None = None
    panel_id: UUID | None = None
    balloon_id: UUID | None = None


def _normalized_set(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def validate_payload(pages: list[dict[str, Any]]) -> tuple[float, list[ContinuityFinding]]:
    findings: list[ContinuityFinding] = []
    ordered_panels: list[dict[str, Any]] = []
    expected_page = 1
    for page in sorted(pages, key=lambda item: int(item.get("page_number", 0))):
        page_number = int(page.get("page_number", 0))
        page_id = _uuid_or_none(page.get("id"))
        if page_number != expected_page:
            findings.append(
                ContinuityFinding(
                    "warning",
                    "page_sequence",
                    (
                        f"Esperava-se a página {expected_page}, mas foi encontrada "
                        f"a página {page_number}."
                    ),
                    page_id=page_id,
                )
            )
        expected_page = page_number + 1
        panels = page.get("panels", [])
        if not isinstance(panels, list):
            continue
        panel_rectangles: list[tuple[UUID | None, float, float, float, float]] = []
        for geometry_panel in panels:
            if not isinstance(geometry_panel, dict):
                continue
            x = float(geometry_panel.get("position_x", 0.0))
            y = float(geometry_panel.get("position_y", 0.0))
            width = float(geometry_panel.get("width", 0.0))
            height = float(geometry_panel.get("height", 0.0))
            geometry_panel_id = _uuid_or_none(geometry_panel.get("id"))
            if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 100 or y + height > 100:
                findings.append(
                    ContinuityFinding(
                        "error",
                        "panel_out_of_bounds",
                        "O quadro ultrapassa os limites da página.",
                        page_id=page_id,
                        panel_id=geometry_panel_id,
                    )
                )
            for other_id, other_x, other_y, other_width, other_height in panel_rectangles:
                if (
                    _overlap_ratio(
                        x,
                        y,
                        width,
                        height,
                        other_x,
                        other_y,
                        other_width,
                        other_height,
                    )
                    > 0.18
                ):
                    findings.append(
                        ContinuityFinding(
                            "warning",
                            "panel_overlap",
                            "Há sobreposição relevante entre quadros da página.",
                            page_id=page_id,
                            panel_id=geometry_panel_id or other_id,
                        )
                    )
            panel_rectangles.append((geometry_panel_id, x, y, width, height))
        page_panel_count = int(page.get("panel_count", len(panels)))
        if page_panel_count != len(panels):
            findings.append(
                ContinuityFinding(
                    "warning",
                    "panel_count_mismatch",
                    f"A página declara {page_panel_count} quadros, mas possui {len(panels)}.",
                    page_id=page_id,
                )
            )
        reading_orders: set[int] = set()
        for panel in panels:
            if not isinstance(panel, dict):
                continue
            reading_order = int(panel.get("reading_order", 0))
            if reading_order in reading_orders:
                findings.append(
                    ContinuityFinding(
                        "error",
                        "duplicate_reading_order",
                        f"A ordem de leitura {reading_order} está repetida na página.",
                        page_id=page_id,
                        panel_id=_uuid_or_none(panel.get("id")),
                    )
                )
            reading_orders.add(reading_order)
            panel["_page_id"] = page_id
            ordered_panels.append(panel)

    ordered_panels.sort(
        key=lambda panel: (
            _page_number_for(pages, panel.get("_page_id")),
            int(panel.get("reading_order", 0)),
        )
    )
    known_facts: set[str] = set()
    previous_summary = ""
    for index, panel in enumerate(ordered_panels):
        panel_id = _uuid_or_none(panel.get("id"))
        page_id = _uuid_or_none(panel.get("_page_id"))
        previous_reference = str(panel.get("previous_panel_summary", "")).strip()
        if index > 0 and not previous_reference:
            findings.append(
                ContinuityFinding(
                    "warning",
                    "missing_previous_reference",
                    "O quadro não registra como continua o acontecimento anterior.",
                    page_id=page_id,
                    panel_id=panel_id,
                )
            )
        if index > 0 and previous_summary and previous_reference:
            previous_terms = set(previous_summary.lower().split())
            reference_terms = set(previous_reference.lower().split())
            if previous_terms and len(previous_terms & reference_terms) < 2:
                findings.append(
                    ContinuityFinding(
                        "info",
                        "weak_previous_reference",
                        "A ligação textual com o quadro anterior pode ser fortalecida.",
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )
        initial_state = panel.get("initial_state", {})
        final_state = panel.get("final_state", {})
        initial_known = (
            _normalized_set(initial_state.get("known_facts", []))
            if isinstance(initial_state, dict)
            else set()
        )
        if not initial_known.issubset(known_facts):
            introduced = initial_known - known_facts
            findings.append(
                ContinuityFinding(
                    "warning",
                    "knowledge_jump",
                    "O quadro assume conhecimento ainda não registrado: "
                    + ", ".join(sorted(introduced)),
                    page_id=page_id,
                    panel_id=panel_id,
                )
            )
        if isinstance(final_state, dict):
            known_facts |= _normalized_set(final_state.get("known_facts", []))
        balloons = panel.get("balloons", [])
        if isinstance(balloons, list):
            sequences: set[int] = set()
            for balloon in balloons:
                if not isinstance(balloon, dict):
                    continue
                sequence = int(balloon.get("sequence_number", 0))
                if sequence in sequences:
                    findings.append(
                        ContinuityFinding(
                            "error",
                            "duplicate_balloon_sequence",
                            f"A ordem da fala {sequence} está repetida no quadro.",
                            page_id=page_id,
                            panel_id=panel_id,
                            balloon_id=_uuid_or_none(balloon.get("id")),
                        )
                    )
                sequences.add(sequence)
                if not str(balloon.get("text", "")).strip():
                    findings.append(
                        ContinuityFinding(
                            "error",
                            "empty_balloon",
                            "Há um balão sem texto.",
                            page_id=page_id,
                            panel_id=panel_id,
                            balloon_id=_uuid_or_none(balloon.get("id")),
                        )
                    )
                balloon_x = float(balloon.get("position_x", 0.0))
                balloon_y = float(balloon.get("position_y", 0.0))
                balloon_width = float(balloon.get("width", 0.0))
                balloon_height = float(balloon.get("height", 0.0))
                if (
                    balloon_x < 0
                    or balloon_y < 0
                    or balloon_width <= 0
                    or balloon_height <= 0
                    or balloon_x + balloon_width > 100
                    or balloon_y + balloon_height > 100
                ):
                    findings.append(
                        ContinuityFinding(
                            "warning",
                            "balloon_out_of_bounds",
                            "O balão ultrapassa os limites do quadro.",
                            page_id=page_id,
                            panel_id=panel_id,
                            balloon_id=_uuid_or_none(balloon.get("id")),
                        )
                    )
            word_count = sum(
                len(str(item.get("text", "")).split())
                for item in balloons
                if isinstance(item, dict)
            )
            text_limit = int(panel.get("text_word_limit", 80))
            if word_count > text_limit:
                findings.append(
                    ContinuityFinding(
                        "warning",
                        "panel_text_overflow",
                        f"O quadro possui {word_count} palavras para um limite de {text_limit}.",
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )
        visual_prompt = panel.get("visual_prompt", {})
        if isinstance(visual_prompt, dict) and visual_prompt:
            if not bool(visual_prompt.get("image_without_balloons", False)):
                findings.append(
                    ContinuityFinding(
                        "warning",
                        "embedded_text_risk",
                        "O prompt visual deve solicitar imagem sem balões ou texto incorporado.",
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )
        if str(panel.get("plot_function", "")) == "plot_twist":
            previous_clues = {
                str(item.get("plot_function", ""))
                for item in ordered_panels[:index]
                if isinstance(item, dict)
            }
            if "clue" not in previous_clues:
                findings.append(
                    ContinuityFinding(
                        "error",
                        "unsupported_plot_twist",
                        "A reviravolta não possui uma pista registrada em quadro anterior.",
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )
        previous_summary = str(panel.get("narrative_goal", "")).strip()

    penalty = sum(
        18 if finding.severity == "error" else 8 if finding.severity == "warning" else 3
        for finding in findings
    )
    score = max(0.0, min(100.0, 100.0 - float(penalty)))
    return score, findings


def _overlap_ratio(
    x1: float,
    y1: float,
    width1: float,
    height1: float,
    x2: float,
    y2: float,
    width2: float,
    height2: float,
) -> float:
    intersection_width = max(0.0, min(x1 + width1, x2 + width2) - max(x1, x2))
    intersection_height = max(0.0, min(y1 + height1, y2 + height2) - max(y1, y2))
    intersection = intersection_width * intersection_height
    smaller_area = min(width1 * height1, width2 * height2)
    return intersection / smaller_area if smaller_area > 0 else 0.0


def _uuid_or_none(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


def _page_number_for(pages: list[dict[str, Any]], page_id: object) -> int:
    for page in pages:
        if str(page.get("id")) == str(page_id):
            return int(page.get("page_number", 0))
    return 0
