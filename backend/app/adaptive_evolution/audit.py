from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("educode.adaptive_evolution.audit")


def emit_audit_event(
    event: str,
    *,
    organization_id: Any,
    user_id: Any,
    resource_type: str,
    resource_id: Any | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Emite evento estruturado compatível com o pipeline de logs existente.

    O projeto pode substituir esta função pelo serviço institucional de auditoria,
    mantendo a mesma assinatura.
    """

    logger.info(
        "adaptive_audit_event",
        extra={
            "event": event,
            "organization_id": str(organization_id),
            "user_id": str(user_id),
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "details": details or {},
        },
    )
