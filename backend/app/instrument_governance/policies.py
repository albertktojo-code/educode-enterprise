from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class LearnerProfile:
    locale: str = "pt-BR"
    age: float | None = None
    school_year: int | None = None
    attributes: Mapping[str, Any] | None = None


def canonical_checksum(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_license_for_use(
    *,
    status: str,
    valid_from: date | None,
    valid_until: date | None,
    today: date | None = None,
    rights_scope: Mapping[str, Any] | None = None,
    requested_action: str = "ADMINISTER",
) -> tuple[bool, str]:
    current = today or date.today()
    if status != "ACTIVE":
        return False, "LICENSE_NOT_ACTIVE"
    if valid_from and current < valid_from:
        return False, "LICENSE_NOT_STARTED"
    if valid_until and current > valid_until:
        return False, "LICENSE_EXPIRED"
    actions = {str(item).upper() for item in (rights_scope or {}).get("actions", [])}
    if actions and requested_action.upper() not in actions:
        return False, "ACTION_NOT_LICENSED"
    return True, "LICENSE_VALID"


def validate_import_manifest(
    manifest: Mapping[str, Any], *, has_active_license: bool
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    required = ("instrument_code", "instrument_version", "dimensions", "items_count")
    for field in required:
        if field not in manifest:
            errors.append({"code": "MISSING_FIELD", "field": field})
    protected = bool(manifest.get("contains_protected_items", True))
    if protected and not has_active_license:
        errors.append({"code": "ACTIVE_LICENSE_REQUIRED", "field": "license"})
    if int(manifest.get("items_count", 0) or 0) < 0:
        errors.append({"code": "INVALID_ITEMS_COUNT", "field": "items_count"})
    dimensions = manifest.get("dimensions", [])
    if not isinstance(dimensions, list) or not all(isinstance(item, Mapping) and item.get("code") for item in dimensions):
        errors.append({"code": "INVALID_DIMENSIONS", "field": "dimensions"})
    return errors


def _range_width(group: Mapping[str, Any]) -> float:
    age_min = group.get("age_min")
    age_max = group.get("age_max")
    year_min = group.get("school_year_min")
    year_max = group.get("school_year_max")
    age_width = 100.0 if age_min is None or age_max is None else max(float(age_max) - float(age_min), 0.0)
    year_width = 20.0 if year_min is None or year_max is None else max(float(year_max) - float(year_min), 0.0)
    return age_width + year_width


def choose_norm_group(groups: Sequence[Mapping[str, Any]], profile: LearnerProfile) -> Mapping[str, Any] | None:
    matches: list[Mapping[str, Any]] = []
    for group in groups:
        if group.get("status") != "PUBLISHED":
            continue
        locale = group.get("locale")
        if locale and locale != profile.locale:
            continue
        if profile.age is not None:
            if group.get("age_min") is not None and profile.age < float(group["age_min"]):
                continue
            if group.get("age_max") is not None and profile.age > float(group["age_max"]):
                continue
        if profile.school_year is not None:
            if group.get("school_year_min") is not None and profile.school_year < int(group["school_year_min"]):
                continue
            if group.get("school_year_max") is not None and profile.school_year > int(group["school_year_max"]):
                continue
        filters = group.get("population_filters") or {}
        attributes = profile.attributes or {}
        if any(attributes.get(key) != value for key, value in filters.items()):
            continue
        matches.append(group)
    if not matches:
        return None
    return min(matches, key=lambda group: (_range_width(group), -int(group.get("sample_size") or 0)))


def lookup_norm_entry(
    entries: Iterable[Mapping[str, Any]], *, dimension_code: str, raw_score: float
) -> Mapping[str, Any] | None:
    valid = [
        item
        for item in entries
        if item.get("dimension_code") == dimension_code
        and float(item.get("raw_min", 0)) <= raw_score <= float(item.get("raw_max", 0))
    ]
    if not valid:
        return None
    return min(valid, key=lambda item: float(item["raw_max"]) - float(item["raw_min"]))


def calculate_dimension_scores(
    responses: Iterable[Mapping[str, Any]], item_dimensions: Mapping[str, Sequence[Mapping[str, Any]]]
) -> dict[str, float]:
    totals: dict[str, float] = {}
    weights: dict[str, float] = {}
    for response in responses:
        item_code = str(response.get("item_code", ""))
        score = float(response.get("score", 0) or 0)
        maximum = float(response.get("maximum_score", 1) or 1)
        normalized = 0.0 if maximum <= 0 else score / maximum
        for mapping in item_dimensions.get(item_code, []):
            dimension = str(mapping["dimension_code"])
            weight = float(mapping.get("weight", 1.0) or 1.0)
            totals[dimension] = totals.get(dimension, 0.0) + normalized * weight
            weights[dimension] = weights.get(dimension, 0.0) + weight
    return {dimension: round(totals[dimension] / weights[dimension], 4) for dimension in totals if weights[dimension] > 0}


def safe_descriptive_interpretation(
    *, dimension_code: str, classification: str, percentile: float | None, source: str
) -> dict[str, Any]:
    return {
        "dimension_code": dimension_code,
        "classification": classification,
        "percentile": percentile,
        "source": source,
        "notice": "Resultado educacional descritivo; nao constitui diagnostico clinico ou psicologico.",
        "requires_human_contextualization": True,
    }


def roman_gonzalez_structural_template() -> dict[str, Any]:
    return {
        "template_code": "CT_ROMAN_GONZALEZ",
        "name": "Teste de Pensamento Computacional de Roman-Gonzalez",
        "support_level": "STRUCTURAL_ONLY",
        "requires_license": True,
        "protected_items_included": False,
        "allowed_configuration": [
            "instrument_metadata",
            "authorized_dimensions",
            "administration_protocol",
            "authorized_scoring_rules",
            "norm_groups",
            "framework_mappings",
        ],
        "notice": "Itens, gabaritos e normas protegidos devem ser importados apenas com autorizacao documentada.",
    }
