from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable

from .enums import IntegrityStatus, NavigationMode, PublicationStatus, SessionStatus


TRANSITIONS: dict[str, set[str]] = {
    SessionStatus.CREATED.value: {SessionStatus.IN_PROGRESS.value, SessionStatus.CANCELLED.value},
    SessionStatus.IN_PROGRESS.value: {
        SessionStatus.PAUSED.value,
        SessionStatus.SUBMITTED.value,
        SessionStatus.UNDER_REVIEW.value,
        SessionStatus.TIMED_OUT.value,
        SessionStatus.CANCELLED.value,
    },
    SessionStatus.PAUSED.value: {SessionStatus.IN_PROGRESS.value, SessionStatus.CANCELLED.value},
    SessionStatus.TIMED_OUT.value: {SessionStatus.IN_PROGRESS.value, SessionStatus.CANCELLED.value},
    SessionStatus.SUBMITTED.value: {SessionStatus.IN_PROGRESS.value, SessionStatus.UNDER_REVIEW.value},
    SessionStatus.UNDER_REVIEW.value: set(),
    SessionStatus.CANCELLED.value: set(),
}


def validate_transition(current: str, target: str) -> None:
    if target not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Transicao de sessao invalida: {current} -> {target}")


def effective_publication_status(status: str, starts_at: datetime, ends_at: datetime, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if status in {PublicationStatus.CLOSED.value, PublicationStatus.CANCELLED.value, PublicationStatus.DRAFT.value}:
        return status
    if now < starts_at:
        return "SCHEDULED"
    if now > ends_at:
        return PublicationStatus.CLOSED.value
    return "OPEN"


def calculate_duration_seconds(
    base_minutes: int,
    *,
    target_minutes: int | None = None,
    extra_time_percent: int = 0,
    extra_time_minutes: int = 0,
) -> int:
    minutes = target_minutes or base_minutes
    minutes = minutes + round(minutes * extra_time_percent / 100) + extra_time_minutes
    return max(60, minutes * 60)


def calculate_expiration(started_at: datetime, duration_seconds: int) -> datetime:
    return started_at + timedelta(seconds=duration_seconds)


def can_navigate(
    mode: str,
    current_position: int,
    target_position: int,
    answered_positions: set[int] | None = None,
) -> bool:
    answered_positions = answered_positions or set()
    if target_position < 0:
        return False
    if mode == NavigationMode.FREE.value:
        return True
    if mode == NavigationMode.LINEAR.value:
        return target_position in {current_position, current_position + 1}
    if mode == NavigationMode.LINEAR_WITH_REVIEW.value:
        if target_position in answered_positions:
            return True
        return target_position in {current_position, current_position + 1}
    return False


def classify_integrity(focus_loss_count: int, reconnect_count: int, severe_events: int = 0) -> str:
    if severe_events > 0 or focus_loss_count >= 8 or reconnect_count >= 5:
        return IntegrityStatus.REVIEW.value
    if focus_loss_count >= 3 or reconnect_count >= 2:
        return IntegrityStatus.ATTENTION.value
    return IntegrityStatus.NORMAL.value


def deterministic_item_order(items: list[dict[str, Any]], *, seed: str, shuffle: bool) -> list[dict[str, Any]]:
    result = [dict(item) for item in sorted(items, key=lambda item: int(item.get("position", 0)))]
    if shuffle:
        random.Random(seed).shuffle(result)
    return result


def response_checksum(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def monitoring_progress(current_positions: Iterable[int], item_counts: Iterable[int]) -> float:
    ratios: list[float] = []
    for position, count in zip(current_positions, item_counts, strict=False):
        if count > 0:
            ratios.append(min(1.0, max(0.0, (position + 1) / count)))
    return round(sum(ratios) / len(ratios), 4) if ratios else 0.0
