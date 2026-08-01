from app.comic_layout_studio.policies import (
    evaluate_preflight,
    export_progress,
    normalize_rotation,
    normalize_z_order,
    page_geometry,
    snap_transform,
)


def test_normalize_rotation_wraps_angles():
    assert normalize_rotation(370) == 10
    assert normalize_rotation(190) == -170


def test_snap_transform_uses_grid():
    result = snap_transform(
        {"x": 12.2, "y": 4.9, "width": 31.1, "height": 20.2, "rotation_deg": 370},
        grid_size=5,
        enabled=True,
    )
    assert result["x"] == 10
    assert result["y"] == 5
    assert result["width"] == 30
    assert result["rotation_deg"] == 10


def test_page_geometry_includes_bleed_and_safe_area():
    result = page_geometry(width_mm=210, height_mm=297, bleed_mm=3, safe_margin_mm=8)
    assert result["bleed"]["width"] == 216
    assert result["safe_area"]["x"] == 8
    assert result["safe_area"]["width"] == 194


def test_normalize_z_order_rejects_duplicates():
    try:
        normalize_z_order(["a", "a"])
    except ValueError as error:
        assert str(error) == "LAYER_IDS_MUST_BE_UNIQUE"
    else:
        raise AssertionError("Duplicate layer IDs should fail")


def test_preflight_detects_empty_page():
    findings = evaluate_preflight(
        {"page_width": 210, "page_height": 297, "bleed_mm": 3, "safe_margin_mm": 8, "dpi": 300},
        [],
        output_format="PDF",
    )
    assert any(item["code"] == "EMPTY_PAGE" for item in findings)


def test_preflight_detects_accessibility_and_safe_area():
    findings = evaluate_preflight(
        {"page_width": 210, "page_height": 297, "bleed_mm": 3, "safe_margin_mm": 8, "dpi": 300},
        [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "layer_type": "IMAGE",
                "z_index": 1,
                "x": 10,
                "y": 10,
                "width": 100,
                "height": 100,
                "rotation_deg": 0,
                "opacity": 1,
                "visible": True,
                "style": {},
                "content": {"source_dpi": 96},
                "accessibility_metadata": {},
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "layer_type": "SPEECH_BALLOON",
                "z_index": 2,
                "x": 1,
                "y": 1,
                "width": 30,
                "height": 20,
                "rotation_deg": 0,
                "opacity": 1,
                "visible": True,
                "style": {"font_size": 8},
                "content": {},
                "accessibility_metadata": {},
            },
        ],
        output_format="PDF",
    )
    codes = {item["code"] for item in findings}
    assert "LOW_RESOLUTION_IMAGE" in codes
    assert "IMAGE_ALT_TEXT_MISSING" in codes
    assert "TEXT_OUTSIDE_SAFE_AREA" in codes


def test_export_progress_is_deterministic():
    assert export_progress("RENDERING") == 55
    assert export_progress("COMPLETED") == 100
