from __future__ import annotations

from enum import StrEnum


class RubricStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class ReviewAssignmentStatus(StrEnum):
    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    REOPENED = "REOPENED"
    CANCELLED = "CANCELLED"


class ReviewMode(StrEnum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    MODERATION = "MODERATION"


class CriterionType(StrEnum):
    SCALE = "SCALE"
    BINARY = "BINARY"
    NUMERIC = "NUMERIC"
    TEXT = "TEXT"


class FeedbackAudience(StrEnum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    INTERNAL = "INTERNAL"


class FeedbackStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SUPERSEDED = "SUPERSEDED"


class AppealStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_ACCEPTED = "PARTIALLY_ACCEPTED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class RegradeStatus(StrEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class CorrectionSource(StrEnum):
    AUTOMATIC = "AUTOMATIC"
    HUMAN = "HUMAN"
    RUBRIC = "RUBRIC"
    ASSISTED = "ASSISTED"


class ReviewEventType(StrEnum):
    ASSIGNED = "ASSIGNED"
    STARTED = "STARTED"
    SCORE_RECORDED = "SCORE_RECORDED"
    FEEDBACK_PUBLISHED = "FEEDBACK_PUBLISHED"
    COMPLETED = "COMPLETED"
    REOPENED = "REOPENED"
    APPEAL_OPENED = "APPEAL_OPENED"
    APPEAL_DECIDED = "APPEAL_DECIDED"
    REGRADE_APPLIED = "REGRADE_APPLIED"
