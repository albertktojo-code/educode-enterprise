from __future__ import annotations

from enum import StrEnum


class LicenseStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class ProtocolStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class NormStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"


class ImportStatus(StrEnum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    VALID = "VALID"
    REJECTED = "REJECTED"
    IMPORTED = "IMPORTED"


class InterpretationStatus(StrEnum):
    CALCULATED = "CALCULATED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    VALIDATED = "VALIDATED"
    INVALIDATED = "INVALIDATED"


class FrameworkType(StrEnum):
    BNCC = "BNCC"
    COMPUTATIONAL_THINKING = "COMPUTATIONAL_THINKING"
    INSTITUTIONAL = "INSTITUTIONAL"
