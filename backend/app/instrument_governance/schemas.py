from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import FrameworkType, ImportStatus, InterpretationStatus, LicenseStatus, NormStatus, ProtocolStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LicenseCreate(BaseModel):
    instrument_id: uuid.UUID
    license_holder: str = Field(min_length=2, max_length=240)
    rights_owner: str | None = Field(default=None, max_length=240)
    permission_reference: str = Field(min_length=3)
    rights_scope: dict[str, Any] = Field(default_factory=dict)
    permitted_populations: list[dict[str, Any]] = Field(default_factory=list)
    permitted_territories: list[str] = Field(default_factory=list)
    item_exposure_policy: dict[str, Any] = Field(default_factory=dict)
    storage_policy: dict[str, Any] = Field(default_factory=dict)
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "LicenseCreate":
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until deve ser igual ou posterior a valid_from")
        return self


class LicenseRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    instrument_id: uuid.UUID
    version: int
    status: LicenseStatus
    license_holder: str
    rights_owner: str | None
    permission_reference: str
    rights_scope: dict[str, Any]
    permitted_populations: list[dict[str, Any]]
    permitted_territories: list[str]
    item_exposure_policy: dict[str, Any]
    storage_policy: dict[str, Any]
    valid_from: date | None
    valid_until: date | None
    created_at: datetime


class LicenseDecision(BaseModel):
    approve: bool
    justification: str = Field(min_length=3)


class ProtocolCreate(BaseModel):
    instrument_id: uuid.UUID
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=220)
    version: str = Field(min_length=1, max_length=40)
    instructions: dict[str, Any] = Field(default_factory=dict)
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    target_population: dict[str, Any] = Field(default_factory=dict)
    administration_conditions: dict[str, Any] = Field(default_factory=dict)
    accessibility_rules: dict[str, Any] = Field(default_factory=dict)
    scoring_reference: str | None = None


class ProtocolRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    instrument_id: uuid.UUID
    code: str
    name: str
    version: str
    status: ProtocolStatus
    instructions: dict[str, Any]
    duration_minutes: int | None
    target_population: dict[str, Any]
    administration_conditions: dict[str, Any]
    accessibility_rules: dict[str, Any]
    created_at: datetime


class NormEntryCreate(BaseModel):
    dimension_code: str = Field(default="TOTAL", min_length=1, max_length=80)
    raw_min: float
    raw_max: float
    standardized_score: float | None = None
    percentile: float | None = Field(default=None, ge=0, le=100)
    classification: str = Field(min_length=1, max_length=120)
    interpretation: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_range(self) -> "NormEntryCreate":
        if self.raw_max < self.raw_min:
            raise ValueError("raw_max deve ser maior ou igual a raw_min")
        return self


class NormGroupCreate(BaseModel):
    instrument_id: uuid.UUID
    code: str = Field(min_length=2, max_length=100)
    version: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=2, max_length=220)
    locale: str = Field(default="pt-BR", min_length=2, max_length=20)
    age_min: float | None = Field(default=None, ge=0, le=120)
    age_max: float | None = Field(default=None, ge=0, le=120)
    school_year_min: int | None = Field(default=None, ge=1, le=20)
    school_year_max: int | None = Field(default=None, ge=1, le=20)
    population_filters: dict[str, Any] = Field(default_factory=dict)
    sample_size: int | None = Field(default=None, ge=1)
    source_reference: str = Field(min_length=3)
    methodology: dict[str, Any] = Field(default_factory=dict)
    entries: list[NormEntryCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ranges(self) -> "NormGroupCreate":
        if self.age_min is not None and self.age_max is not None and self.age_max < self.age_min:
            raise ValueError("age_max deve ser maior ou igual a age_min")
        if self.school_year_min is not None and self.school_year_max is not None and self.school_year_max < self.school_year_min:
            raise ValueError("school_year_max deve ser maior ou igual a school_year_min")
        return self


class NormGroupRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    instrument_id: uuid.UUID
    code: str
    version: str
    name: str
    locale: str
    status: NormStatus
    age_min: float | None
    age_max: float | None
    school_year_min: int | None
    school_year_max: int | None
    population_filters: dict[str, Any]
    sample_size: int | None
    source_reference: str
    methodology: dict[str, Any]
    created_at: datetime


class MappingCreate(BaseModel):
    instrument_id: uuid.UUID
    dimension_id: uuid.UUID
    framework_type: FrameworkType
    framework_code: str = Field(min_length=1, max_length=100)
    relation_type: str = Field(default="RELATED", min_length=1, max_length=40)
    weight: float = Field(default=1.0, gt=0, le=10)
    justification: str = Field(min_length=3)


class MappingRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    instrument_id: uuid.UUID
    dimension_id: uuid.UUID
    framework_type: FrameworkType
    framework_code: str
    relation_type: str
    weight: float
    justification: str
    status: str


class ImportManifest(BaseModel):
    instrument_code: str = Field(min_length=1)
    instrument_version: str = Field(min_length=1)
    dimensions: list[dict[str, Any]]
    items_count: int = Field(ge=0)
    contains_protected_items: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ImportBatchCreate(BaseModel):
    instrument_id: uuid.UUID
    filename: str = Field(min_length=1, max_length=260)
    file_format: str = Field(min_length=1, max_length=40)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    declared_license_id: uuid.UUID | None = None
    manifest: ImportManifest


class ImportBatchRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    instrument_id: uuid.UUID
    filename: str
    file_format: str
    checksum_sha256: str
    status: ImportStatus
    declared_license_id: uuid.UUID | None
    contains_protected_items: bool
    manifest: dict[str, Any]
    validation_errors: list[dict[str, Any]]
    imported_counts: dict[str, Any]
    created_at: datetime


class LearnerProfileInput(BaseModel):
    locale: str = "pt-BR"
    age: float | None = Field(default=None, ge=0, le=120)
    school_year: int | None = Field(default=None, ge=1, le=20)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ScoreSimulationRequest(BaseModel):
    instrument_id: uuid.UUID
    raw_scores: dict[str, float]
    profile: LearnerProfileInput = Field(default_factory=LearnerProfileInput)


class DimensionInterpretation(BaseModel):
    dimension_code: str
    raw_score: float
    standardized_score: float | None
    percentile: float | None
    classification: str
    interpretation: dict[str, Any]


class ScoreSimulationResult(BaseModel):
    norm_group_id: uuid.UUID | None
    dimensions: list[DimensionInterpretation]
    warnings: list[str] = Field(default_factory=list)
    requires_human_review: bool = True


class InterpretationCreate(BaseModel):
    instrument_id: uuid.UUID
    attempt_id: uuid.UUID
    norm_group_id: uuid.UUID | None = None
    scoring_version: str = Field(min_length=1, max_length=60)
    raw_scores: dict[str, float]
    standardized_scores: dict[str, Any] = Field(default_factory=dict)
    classifications: dict[str, Any] = Field(default_factory=dict)
    descriptive_interpretation: dict[str, Any] = Field(default_factory=dict)


class InterpretationRead(ORMModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    instrument_id: uuid.UUID
    attempt_id: uuid.UUID
    norm_group_id: uuid.UUID | None
    scoring_version: str
    status: InterpretationStatus
    raw_scores: dict[str, Any]
    standardized_scores: dict[str, Any]
    classifications: dict[str, Any]
    descriptive_interpretation: dict[str, Any]
    requires_human_review: bool
    created_at: datetime


class InterpretationDecision(BaseModel):
    approved: bool
    justification: str = Field(min_length=3)
