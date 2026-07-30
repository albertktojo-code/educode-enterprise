from datetime import date

from app.instrument_governance.policies import (
    LearnerProfile,
    canonical_checksum,
    choose_norm_group,
    lookup_norm_entry,
    roman_gonzalez_structural_template,
    validate_import_manifest,
    validate_license_for_use,
)


def test_checksum_is_deterministic():
    assert canonical_checksum({"b": 2, "a": 1}) == canonical_checksum({"a": 1, "b": 2})


def test_active_license_with_action_is_valid():
    valid, reason = validate_license_for_use(
        status="ACTIVE",
        valid_from=date(2026, 1, 1),
        valid_until=date(2026, 12, 31),
        today=date(2026, 7, 27),
        rights_scope={"actions": ["IMPORT", "ADMINISTER", "SCORE"]},
        requested_action="IMPORT",
    )
    assert valid is True
    assert reason == "LICENSE_VALID"


def test_protected_import_requires_active_license():
    errors = validate_import_manifest(
        {
            "instrument_code": "CT",
            "instrument_version": "1",
            "dimensions": [{"code": "TOTAL"}],
            "items_count": 20,
            "contains_protected_items": True,
        },
        has_active_license=False,
    )
    assert any(item["code"] == "ACTIVE_LICENSE_REQUIRED" for item in errors)


def test_choose_most_specific_norm_group():
    groups = [
        {"id": "wide", "status": "PUBLISHED", "locale": "pt-BR", "age_min": 8, "age_max": 18, "sample_size": 200},
        {"id": "specific", "status": "PUBLISHED", "locale": "pt-BR", "age_min": 11, "age_max": 13, "sample_size": 100},
    ]
    selected = choose_norm_group(groups, LearnerProfile(locale="pt-BR", age=12))
    assert selected and selected["id"] == "specific"


def test_lookup_norm_entry_uses_matching_range():
    entry = lookup_norm_entry(
        [
            {"dimension_code": "TOTAL", "raw_min": 0, "raw_max": 10, "classification": "A"},
            {"dimension_code": "TOTAL", "raw_min": 11, "raw_max": 20, "classification": "B"},
        ],
        dimension_code="TOTAL",
        raw_score=14,
    )
    assert entry and entry["classification"] == "B"


def test_roman_template_contains_no_protected_items():
    template = roman_gonzalez_structural_template()
    assert template["requires_license"] is True
    assert template["protected_items_included"] is False
