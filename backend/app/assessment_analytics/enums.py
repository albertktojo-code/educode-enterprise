from __future__ import annotations

from enum import StrEnum


class AnalyticsModelStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class AnalyticsRunStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MetricScope(StrEnum):
    ITEM = "ITEM"
    ASSESSMENT = "ASSESSMENT"
    SKILL = "SKILL"
    COHORT = "COHORT"
    ORGANIZATION = "ORGANIZATION"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ExportStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
