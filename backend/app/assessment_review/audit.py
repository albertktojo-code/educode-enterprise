from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("educode.assessment_review")


def record(event: str, **payload: Any) -> None:
    logger.info(event, extra={"event": event, **payload})
