from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from . import models
    from .compat import ActorContext


BUBBLE_TYPES = {
    "SPEECH": "Fala",
    "THOUGHT": "Pensamento",
    "SHOUT": "Grito",
    "WHISPER": "Sussurro",
    "NARRATION": "Narração",
    "CAPTION": "Legenda",
    "DEVICE": "Dispositivo eletrônico",
    "OFFSCREEN": "Voz fora de cena",
    "SOUND_EFFECT": "Efeito sonoro",
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def bubble_conflicts(
    *,
    layers: list[dict[str, Any]],
    panel_width: float = 1.0,
    panel_height: float = 1.0,
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for index, layer in enumerate(layers):
        x = float(layer.get("x", 0.0))
        y = float(layer.get("y", 0.0))
        width = float(layer.get("width", 0.0))
        height = float(layer.get("height", 0.0))
        content = str(layer.get("content", ""))
        layer_id = str(layer.get("id", index))

        if x < 0 or y < 0 or x + width > panel_width or y + height > panel_height:
            conflicts.append(
                {
                    "code": "OUTSIDE_SAFE_AREA",
                    "severity": "CRITICAL",
                    "layer_id": layer_id,
                    "message": "O balão ultrapassa a área segura do quadro.",
                }
            )
        if len(content) > 420:
            conflicts.append(
                {
                    "code": "EXCESSIVE_BUBBLE_TEXT",
                    "severity": "CRITICAL",
                    "layer_id": layer_id,
                    "message": "A fala é longa demais para um único balão.",
                }
            )
        elif len(content) > 220:
            conflicts.append(
                {
                    "code": "BUBBLE_TEXT_NEAR_LIMIT",
                    "severity": "WARNING",
                    "layer_id": layer_id,
                    "message": "A fala está próxima do limite recomendado.",
                }
            )

        for other in layers[index + 1 :]:
            ox = float(other.get("x", 0.0))
            oy = float(other.get("y", 0.0))
            ow = float(other.get("width", 0.0))
            oh = float(other.get("height", 0.0))
            overlap_width = max(0.0, min(x + width, ox + ow) - max(x, ox))
            overlap_height = max(0.0, min(y + height, oy + oh) - max(y, oy))
            overlap = overlap_width * overlap_height
            smaller = max(0.0001, min(width * height, ow * oh))
            ratio = overlap / smaller
            if ratio >= 0.25:
                conflicts.append(
                    {
                        "code": "BUBBLE_OVERLAP",
                        "severity": "CRITICAL" if ratio >= 0.55 else "WARNING",
                        "layer_id": layer_id,
                        "other_layer_id": str(other.get("id", "")),
                        "message": "Dois balões possuem sobreposição relevante.",
                    }
                )
    return conflicts


def arrange_bubbles(
    layers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered = sorted(
        layers,
        key=lambda item: (
            int(item.get("reading_order", 1)),
            float(item.get("y", 0.0)),
            float(item.get("x", 0.0)),
        ),
    )
    columns = 2 if len(ordered) > 3 else 1
    width = 0.42 if columns == 2 else 0.72
    height = clamp(0.16 + 0.001 * max(
        [len(str(item.get("content", ""))) for item in ordered] or [0]
    ), 0.16, 0.3)
    result: list[dict[str, Any]] = []
    for index, layer in enumerate(ordered):
        column = index % columns
        row = index // columns
        x = 0.05 + column * 0.5
        y = 0.05 + row * (height + 0.04)
        result.append(
            {
                **layer,
                "x": clamp(x, 0.02, 0.95 - width),
                "y": clamp(y, 0.02, 0.95 - height),
                "width": width,
                "height": height,
                "reading_order": index + 1,
                "bubble_metadata": {
                    **(layer.get("bubble_metadata") or {}),
                    "auto_arranged": True,
                    "tail_direction": (
                        layer.get("bubble_metadata") or {}
                    ).get("tail_direction", "AUTO"),
                },
            }
        )
    return result


def dialogue_suggestions(
    *,
    content: str,
    school_year: str,
    tone: str,
) -> list[dict[str, str]]:
    normalized = " ".join(content.split())
    words = normalized.split()
    compact = " ".join(words[: min(len(words), 24)])
    if len(words) > 24:
        compact += "…"
    return [
        {
            "kind": "SHORTEN",
            "label": "Tornar mais curta",
            "suggestion": compact,
        },
        {
            "kind": "QUESTION",
            "label": "Transformar em pergunta",
            "suggestion": (
                normalized.rstrip(".!?") + "?"
                if normalized
                else "Como podemos resolver este desafio?"
            ),
        },
        {
            "kind": "AGE_ADAPT",
            "label": f"Adequar ao {school_year or 'ano escolar'}",
            "suggestion": compact,
        },
        {
            "kind": "TONE",
            "label": f"Tom {tone or 'natural'}",
            "suggestion": normalized,
        },
    ]


async def panel_layers(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    panel_id: uuid.UUID,
) -> list[models.HQPanelTextLayer]:
    from . import models

    return list(
        (
            await session.scalars(
                select(models.HQPanelTextLayer)
                .where(
                    models.HQPanelTextLayer.organization_id
                    == organization_id,
                    models.HQPanelTextLayer.panel_id == panel_id,
                )
                .order_by(
                    models.HQPanelTextLayer.reading_order,
                    models.HQPanelTextLayer.layer_order,
                )
            )
        ).all()
    )


async def update_layer(
    session: AsyncSession,
    *,
    actor: ActorContext,
    layer_id: uuid.UUID,
    data: dict[str, Any],
) -> models.HQPanelTextLayer:
    from . import models

    layer = await session.scalar(
        select(models.HQPanelTextLayer)
        .where(
            models.HQPanelTextLayer.organization_id
            == actor.organization_id,
            models.HQPanelTextLayer.id == layer_id,
        )
        .with_for_update()
    )
    if layer is None:
        raise HTTPException(404, "Balão ou camada de texto não encontrado.")
    for key, value in data.items():
        if value is not None and hasattr(layer, key):
            setattr(layer, key, value)
    await session.flush()
    return layer


async def list_comments(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
) -> list[models.HQEditorialComment]:
    from . import models

    return list(
        (
            await session.scalars(
                select(models.HQEditorialComment)
                .where(
                    models.HQEditorialComment.organization_id
                    == actor.organization_id,
                    models.HQEditorialComment.comic_project_id
                    == project_id,
                )
                .order_by(
                    models.HQEditorialComment.status,
                    models.HQEditorialComment.created_at.desc(),
                )
            )
        ).all()
    )


async def resolve_comment(
    session: AsyncSession,
    *,
    actor: ActorContext,
    comment_id: uuid.UUID,
    status: str,
) -> models.HQEditorialComment:
    from . import models

    item = await session.scalar(
        select(models.HQEditorialComment)
        .where(
            models.HQEditorialComment.organization_id
            == actor.organization_id,
            models.HQEditorialComment.id == comment_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Comentário editorial não encontrado.")
    item.status = status
    if status == "RESOLVED":
        item.resolved_by_user_id = actor.user_id
        item.resolved_at = datetime.now(UTC)
    elif status == "REOPENED":
        item.resolved_by_user_id = None
        item.resolved_at = None
    await session.flush()
    return item
