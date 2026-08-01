from __future__ import annotations

import math
from typing import Any, Iterable


ALLOWED_BLEND_MODES = {
    "NORMAL",
    "MULTIPLY",
    "SCREEN",
    "OVERLAY",
    "DARKEN",
    "LIGHTEN",
}

PRINT_FORMATS = {"PDF", "PNG", "JPEG", "WEBP", "SVG"}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def normalize_rotation(value: float) -> float:
    normalized = value % 360
    if normalized > 180:
        normalized -= 360
    return round(normalized, 4)


def snap_value(value: float, grid_size: float, enabled: bool = True) -> float:
    if not enabled or grid_size <= 0:
        return round(value, 6)
    return round(round(value / grid_size) * grid_size, 6)


def snap_transform(
    transform: dict[str, float],
    *,
    grid_size: float,
    enabled: bool,
) -> dict[str, float]:
    result = dict(transform)
    for key in ("x", "y", "width", "height"):
        if key in result:
            result[key] = snap_value(float(result[key]), grid_size, enabled)
    if "rotation_deg" in result:
        result["rotation_deg"] = normalize_rotation(float(result["rotation_deg"]))
    return result


def validate_transform(transform: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("x", "y", "width", "height"):
        value = transform.get(key)
        if not isinstance(value, (int, float)):
            errors.append(f"{key.upper()}_REQUIRED")
    width = float(transform.get("width", 0) or 0)
    height = float(transform.get("height", 0) or 0)
    if width <= 0:
        errors.append("WIDTH_MUST_BE_POSITIVE")
    if height <= 0:
        errors.append("HEIGHT_MUST_BE_POSITIVE")
    opacity = transform.get("opacity", 1)
    if not isinstance(opacity, (int, float)) or not 0 <= float(opacity) <= 1:
        errors.append("OPACITY_OUT_OF_RANGE")
    rotation = transform.get("rotation_deg", 0)
    if not isinstance(rotation, (int, float)):
        errors.append("ROTATION_INVALID")
    return sorted(set(errors))


def next_z_index(existing: Iterable[int]) -> int:
    values = list(existing)
    return (max(values) + 1) if values else 1


def normalize_z_order(layer_ids: list[str]) -> dict[str, int]:
    if len(layer_ids) != len(set(layer_ids)):
        raise ValueError("LAYER_IDS_MUST_BE_UNIQUE")
    return {layer_id: index for index, layer_id in enumerate(layer_ids, start=1)}


def page_geometry(
    *,
    width_mm: float,
    height_mm: float,
    bleed_mm: float,
    safe_margin_mm: float,
) -> dict[str, Any]:
    if min(width_mm, height_mm) <= 0:
        raise ValueError("PAGE_DIMENSIONS_MUST_BE_POSITIVE")
    if bleed_mm < 0 or safe_margin_mm < 0:
        raise ValueError("MARGINS_CANNOT_BE_NEGATIVE")
    return {
        "trim": {"x": 0, "y": 0, "width": width_mm, "height": height_mm},
        "bleed": {
            "x": -bleed_mm,
            "y": -bleed_mm,
            "width": width_mm + (2 * bleed_mm),
            "height": height_mm + (2 * bleed_mm),
        },
        "safe_area": {
            "x": safe_margin_mm,
            "y": safe_margin_mm,
            "width": max(0.0, width_mm - (2 * safe_margin_mm)),
            "height": max(0.0, height_mm - (2 * safe_margin_mm)),
        },
    }


def rotated_bounds(layer: dict[str, float]) -> dict[str, float]:
    width = float(layer["width"])
    height = float(layer["height"])
    angle = math.radians(float(layer.get("rotation_deg", 0)))
    rotated_width = abs(width * math.cos(angle)) + abs(height * math.sin(angle))
    rotated_height = abs(width * math.sin(angle)) + abs(height * math.cos(angle))
    center_x = float(layer["x"]) + width / 2
    center_y = float(layer["y"]) + height / 2
    return {
        "x": center_x - rotated_width / 2,
        "y": center_y - rotated_height / 2,
        "width": rotated_width,
        "height": rotated_height,
    }


def evaluate_preflight(
    document: dict[str, Any],
    layers: list[dict[str, Any]],
    *,
    output_format: str,
    minimum_dpi: int = 150,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    width = float(document.get("page_width", 0))
    height = float(document.get("page_height", 0))
    bleed = float(document.get("bleed_mm", 0))
    safe = float(document.get("safe_margin_mm", 0))
    try:
        geometry = page_geometry(
            width_mm=width,
            height_mm=height,
            bleed_mm=bleed,
            safe_margin_mm=safe,
        )
    except ValueError as error:
        return [{"severity": "ERROR", "code": str(error), "message": "Geometria da pagina invalida."}]

    if output_format.upper() not in PRINT_FORMATS:
        findings.append({
            "severity": "ERROR",
            "code": "UNSUPPORTED_EXPORT_FORMAT",
            "message": "Formato de exportacao nao suportado.",
        })
    if output_format.upper() == "PDF" and int(document.get("dpi", 0)) < minimum_dpi:
        findings.append({
            "severity": "WARNING",
            "code": "LOW_DOCUMENT_DPI",
            "message": f"Resolucao inferior a {minimum_dpi} DPI.",
        })
    if output_format.upper() == "PDF" and bleed <= 0:
        findings.append({
            "severity": "WARNING",
            "code": "BLEED_NOT_CONFIGURED",
            "message": "Sangria nao configurada para exportacao de impressao.",
        })

    safe_area = geometry["safe_area"]
    trim = geometry["trim"]
    visible_layers = [item for item in layers if item.get("visible", True)]
    if not visible_layers:
        findings.append({
            "severity": "ERROR",
            "code": "EMPTY_PAGE",
            "message": "A pagina nao possui camadas visiveis.",
        })

    z_values: list[int] = []
    for layer in visible_layers:
        layer_id = layer.get("id")
        transform_errors = validate_transform(layer)
        for code in transform_errors:
            findings.append({
                "severity": "ERROR",
                "code": code,
                "message": "Transformacao de camada invalida.",
                "resource_type": "LAYER",
                "resource_id": layer_id,
            })
        z_values.append(int(layer.get("z_index", 0)))
        bounds = rotated_bounds(layer)
        if (
            bounds["x"] < trim["x"]
            or bounds["y"] < trim["y"]
            or bounds["x"] + bounds["width"] > trim["width"]
            or bounds["y"] + bounds["height"] > trim["height"]
        ):
            findings.append({
                "severity": "INFO",
                "code": "LAYER_CROSSES_TRIM",
                "message": "A camada ultrapassa a area de corte.",
                "resource_type": "LAYER",
                "resource_id": layer_id,
            })
        if layer.get("layer_type") in {
            "SPEECH_BALLOON",
            "THOUGHT_BALLOON",
            "CAPTION",
            "NARRATION",
            "PEDAGOGICAL_BADGE",
        }:
            if (
                bounds["x"] < safe_area["x"]
                or bounds["y"] < safe_area["y"]
                or bounds["x"] + bounds["width"] > safe_area["x"] + safe_area["width"]
                or bounds["y"] + bounds["height"] > safe_area["y"] + safe_area["height"]
            ):
                findings.append({
                    "severity": "WARNING",
                    "code": "TEXT_OUTSIDE_SAFE_AREA",
                    "message": "Texto ou elemento pedagogico fora da area segura.",
                    "resource_type": "LAYER",
                    "resource_id": layer_id,
                })
        if layer.get("layer_type") == "IMAGE":
            source_dpi = int(layer.get("content", {}).get("source_dpi", 0) or 0)
            if source_dpi and source_dpi < minimum_dpi:
                findings.append({
                    "severity": "WARNING",
                    "code": "LOW_RESOLUTION_IMAGE",
                    "message": "Imagem com resolucao abaixo do recomendado.",
                    "resource_type": "LAYER",
                    "resource_id": layer_id,
                    "details": {"source_dpi": source_dpi},
                })
            if not layer.get("accessibility_metadata", {}).get("alt_text"):
                findings.append({
                    "severity": "WARNING",
                    "code": "IMAGE_ALT_TEXT_MISSING",
                    "message": "Imagem sem descricao alternativa.",
                    "resource_type": "LAYER",
                    "resource_id": layer_id,
                })
        if layer.get("layer_type") in {"SPEECH_BALLOON", "CAPTION", "NARRATION"}:
            font_size = float(layer.get("style", {}).get("font_size", 0) or 0)
            if font_size and font_size < 10:
                findings.append({
                    "severity": "WARNING",
                    "code": "FONT_TOO_SMALL",
                    "message": "Tamanho de fonte inferior ao recomendado.",
                    "resource_type": "LAYER",
                    "resource_id": layer_id,
                })

    if len(z_values) != len(set(z_values)):
        findings.append({
            "severity": "ERROR",
            "code": "DUPLICATE_Z_INDEX",
            "message": "Existem camadas com a mesma ordem de empilhamento.",
        })
    return findings


def export_progress(status: str) -> int:
    return {
        "QUEUED": 0,
        "PREFLIGHT": 15,
        "RENDERING": 55,
        "PACKAGING": 85,
        "COMPLETED": 100,
        "COMPLETED_WITH_WARNINGS": 100,
        "FAILED": 100,
        "CANCELLED": 100,
    }.get(status.upper(), 0)
