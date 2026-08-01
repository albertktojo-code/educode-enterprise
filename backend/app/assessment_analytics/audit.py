from __future__ import annotations

from typing import Any


def audit_payload(event: str, actor, resource_id: str | None = None, **details: Any) -> dict[str, Any]:
    return {
        "event": event,
        "organization_id": str(actor.organization_id),
        "actor_user_id": str(actor.user_id),
        "resource_id": resource_id,
        "details": details,
    }
