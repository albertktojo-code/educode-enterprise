from __future__ import annotations

from enum import StrEnum


class LibraryScope(StrEnum):
    PERSONAL = "PERSONAL"
    COMIC = "COMIC"
    ORGANIZATION = "ORGANIZATION"
    INSTITUTIONAL = "INSTITUTIONAL"


class AssetStatus(StrEnum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class CheckSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CheckStatus(StrEnum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"


class BatchStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
