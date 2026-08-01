from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("educode.assessment_delivery.audit")


def record(event: str, **context: Any) -> None:
    logger.info(event, extra={"assessment_delivery": context})
