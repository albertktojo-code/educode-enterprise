from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext
from app.services.platform import append_audit_event


async def append_domain_audit(
    session: AsyncSession,
    *,
    actor: ActorContext,
    module_name: str,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    details: dict[str, Any] | None = None,
):
    return await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name=module_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details=details or {},
    )
