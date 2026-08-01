from __future__ import annotations

from enum import StrEnum


class PublicationStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class DeliverySourceType(StrEnum):
    BLUEPRINT = "BLUEPRINT"
    EXTERNAL_INSTRUMENT = "EXTERNAL_INSTRUMENT"


class TargetType(StrEnum):
    CLASSROOM = "CLASSROOM"
    STUDENT = "STUDENT"
    GROUP = "GROUP"


class NavigationMode(StrEnum):
    FREE = "FREE"
    LINEAR = "LINEAR"
    LINEAR_WITH_REVIEW = "LINEAR_WITH_REVIEW"


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


class IntegrityStatus(StrEnum):
    NORMAL = "NORMAL"
    ATTENTION = "ATTENTION"
    REVIEW = "REVIEW"


class EventSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


class AutosaveStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"
