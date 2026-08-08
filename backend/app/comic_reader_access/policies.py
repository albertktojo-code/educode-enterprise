from __future__ import annotations

import secrets
import string
from typing import Any

DEFAULT_PREFERENCES: dict[str, Any] = {
    "reader_mode": "PAGE",
    "font_scale": 1.0,
    "line_spacing": 1.4,
    "high_contrast": False,
    "reduced_motion": False,
    "screen_reader_mode": False,
    "show_alt_text": False,
    "auto_play_narration": False,
    "caption_mode": "VISIBLE",
    "focus_mode": False,
    "narration_rate": 1.0,
    "zoom_level": 1.0,
    "orientation": "AUTO",
}

PRESENTATION_TRANSITIONS = {
    "DRAFT": {"LIVE", "CANCELLED"},
    "LIVE": {"PAUSED", "ENDED", "CANCELLED"},
    "PAUSED": {"LIVE", "ENDED", "CANCELLED"},
    "ENDED": set(),
    "CANCELLED": set(),
}


def normalize_preferences(
    saved: dict[str, Any] | None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(DEFAULT_PREFERENCES)
    if saved:
        result.update(saved)
    if overrides:
        result.update(overrides)
    mode = str(result.get("reader_mode", "PAGE")).upper()
    result["reader_mode"] = mode if mode in {"PAGE", "PANEL", "VERTICAL", "FOCUS"} else "PAGE"
    caption = str(result.get("caption_mode", "VISIBLE")).upper()
    result["caption_mode"] = caption if caption in {"VISIBLE", "ON_DEMAND", "HIDDEN"} else "VISIBLE"
    result["font_scale"] = min(2.5, max(0.75, float(result.get("font_scale", 1.0))))
    result["line_spacing"] = min(2.5, max(1.0, float(result.get("line_spacing", 1.4))))
    result["narration_rate"] = min(2.0, max(0.5, float(result.get("narration_rate", 1.0))))
    result["zoom_level"] = min(2.5, max(0.5, float(result.get("zoom_level", 1.0))))
    orientation = str(result.get("orientation", "AUTO")).upper()
    result["orientation"] = (
        orientation if orientation in {"AUTO", "PORTRAIT", "LANDSCAPE"} else "AUTO"
    )
    return result


def calculate_progress(
    *,
    current_page: int,
    current_panel: int,
    total_pages: int,
    total_panels: int,
    completed_panels: int = 0,
) -> dict[str, Any]:
    pages = max(total_pages, 1)
    panels = max(total_panels, 1)
    page_ratio = min(1.0, max(0.0, current_page / pages))
    panel_ratio = min(1.0, max(0.0, max(current_panel, completed_panels) / panels))
    percentage = round(max(page_ratio, panel_ratio) * 100, 2)
    return {
        "progress_percent": percentage,
        "page_progress_percent": round(page_ratio * 100, 2),
        "panel_progress_percent": round(panel_ratio * 100, 2),
        "is_complete": percentage >= 100,
    }


def validate_sequence(last_sequence: int, incoming_sequence: int) -> dict[str, Any]:
    if incoming_sequence <= last_sequence:
        return {"accepted": False, "reason": "DUPLICATE_OR_OLD_SEQUENCE"}
    if incoming_sequence > last_sequence + 100:
        return {"accepted": False, "reason": "SEQUENCE_GAP_TOO_LARGE"}
    return {"accepted": True, "reason": None}


def can_transition_presentation(current: str, target: str) -> bool:
    return target.upper() in PRESENTATION_TRANSITIONS.get(current.upper(), set())


def generate_join_code(length: int = 6) -> str:
    alphabet = "".join(
        char for char in string.ascii_uppercase + string.digits if char not in "0O1IL"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def accessibility_summary(pages: list[dict[str, Any]]) -> dict[str, Any]:
    panels = [
        panel
        for page in pages
        for panel in (page.get("panels") or [])
        if isinstance(panel, dict)
    ]
    missing_alt = sum(1 for panel in panels if not str(panel.get("alt_text") or "").strip())
    missing_audio = sum(
        1 for panel in panels if not str(panel.get("audio_description") or "").strip()
    )
    return {
        "total_panels": len(panels),
        "missing_alt_text": missing_alt,
        "missing_audio_description": missing_audio,
        "screen_reader_ready": missing_alt == 0,
        "narration_ready": missing_audio == 0,
    }
