from __future__ import annotations

from typing import Any


def audit_payload(event: str, *, organization_id: Any, user_id: Any, resource_id: Any, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event": event,
        "organization_id": str(organization_id),
        "user_id": str(user_id),
        "resource_id": str(resource_id),
        "details": details or {},
    }
