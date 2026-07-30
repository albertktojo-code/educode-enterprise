from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("educode.instrument_governance")


def record(event: str, **payload: Any) -> None:
    logger.info(event, extra={"event": event, **payload})
