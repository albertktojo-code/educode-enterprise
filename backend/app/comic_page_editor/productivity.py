from __future__ import annotations

import math
import uuid
from collections import Counter
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from . import models
    from .compat import ActorContext
from .policies import stable_hash


def _words(value: str) -> list[str]:
    return [item for item in value.replace("\n", " ").split(" ") if item.strip()]


def analyze_panel_readability(
    *,
    panel: models.HQEditorPanel,
    page_width: int,
    page_height: int,
) -> dict[str, Any]:
    area = max(
        1.0,
        panel.width * page_width * panel.height * page_height,
    )
    text = " ".join(
        item.strip()
        for item in (panel.scene_summary, panel.visual_prompt)
        if item and item.strip()
    )
    word_count = len(_words(text))
    density = word_count / max(1.0, area / 10000.0)
    warnings: list[dict[str, str]] = []

    if word_count > 120:
        warnings.append(
            {
                "code": "EXCESSIVE_TEXT",
                "severity": "HIGH",
                "message": (
                    "O quadro possui texto demais para leitura confortável."
                ),
            }
        )
    elif word_count > 70:
        warnings.append(
            {
                "code": "TEXT_NEAR_LIMIT",
                "severity": "MEDIUM",
                "message": (
                    "O quadro está próximo do limite recomendado de texto."
                ),
            }
        )
    if density > 8.0:
        warnings.append(
            {
                "code": "HIGH_TEXT_DENSITY",
                "severity": "HIGH",
                "message": (
                    "A densidade estimada de texto é elevada para a área."
                ),
            }
        )
    return {
        "panel_id": str(panel.id),
        "panel_order": panel.panel_order,
        "word_count": word_count,
        "density": round(density, 2),
        "status": (
            "BLOCKED"
            if any(item["severity"] == "HIGH" for item in warnings)
            else "WARNING"
            if warnings
            else "READY"
        ),
        "warnings": warnings,
    }


def narrative_rhythm_analysis(
    *,
    pages: list[dict[str, Any]],
    expected_total: int,
) -> dict[str, Any]:
    story_pages = [
        page for page in pages if page.get("page_type") == "STORY"
    ]
    warnings: list[dict[str, Any]] = []
    counts = [
        int(page.get("panel_count") or 0)
        for page in story_pages
    ]
    if len(story_pages) != expected_total:
        warnings.append(
            {
                "code": "STORY_PAGE_COUNT_MISMATCH",
                "severity": "HIGH",
                "message": (
                    "A quantidade de páginas narrativas difere do planejamento."
                ),
            }
        )

    if counts:
        average = sum(counts) / len(counts)
        for index, count in enumerate(counts, start=1):
            if count >= max(8, math.ceil(average * 1.6)):
                warnings.append(
                    {
                        "code": "DENSE_PAGE",
                        "severity": "MEDIUM",
                        "page_number": index,
                        "message": (
                            "A página concentra muitos quadros e pode acelerar "
                            "demais a leitura."
                        ),
                    }
                )
            if count <= 1 and 1 < index < len(counts):
                warnings.append(
                    {
                        "code": "ABRUPT_PAGE",
                        "severity": "MEDIUM",
                        "page_number": index,
                        "message": (
                            "A página possui pouco desenvolvimento para uma "
                            "posição intermediária da história."
                        ),
                    }
                )

    stages = [
        str(page.get("stage") or "").upper()
        for page in pages
        if page.get("page_type") == "STORY"
    ]
    if stages and "CLIMAX" in stages:
        climax_index = stages.index("CLIMAX") + 1
        if climax_index <= max(1, round(len(stages) * 0.45)):
            warnings.append(
                {
                    "code": "EARLY_CLIMAX",
                    "severity": "MEDIUM",
                    "page_number": climax_index,
                    "message": "O clímax aparece muito cedo na história.",
                }
            )
    elif len(stages) >= 4:
        warnings.append(
            {
                "code": "MISSING_CLIMAX",
                "severity": "MEDIUM",
                "message": "Nenhum clímax explícito foi identificado.",
            }
        )

    return {
        "story_pages": len(story_pages),
        "expected_story_pages": expected_total,
        "average_panels_per_page": (
            round(sum(counts) / len(counts), 2) if counts else 0
        ),
        "warning_count": len(warnings),
        "status": (
            "BLOCKED"
            if any(item["severity"] == "HIGH" for item in warnings)
            else "WARNING"
            if warnings
            else "READY"
        ),
        "warnings": warnings,
    }


def compare_snapshot_payloads(
    left: dict[str, Any],
    right: dict[str, Any],
) -> dict[str, Any]:
    left_pages = left.get("pages") or []
    right_pages = right.get("pages") or []
    left_story = left.get("storyPlan") or left.get("story_plan") or {}
    right_story = right.get("storyPlan") or right.get("story_plan") or {}

    def page_signature(page: dict[str, Any]) -> tuple[Any, ...]:
        return (
            page.get("id"),
            page.get("pageType") or page.get("page_type"),
            page.get("pageNumber") or page.get("page_number"),
            len(page.get("panels") or []),
            stable_hash(page),
        )

    left_signatures = {
        str(item[0]): item for item in map(page_signature, left_pages)
    }
    right_signatures = {
        str(item[0]): item for item in map(page_signature, right_pages)
    }
    added = sorted(set(right_signatures) - set(left_signatures))
    removed = sorted(set(left_signatures) - set(right_signatures))
    changed = sorted(
        key
        for key in set(left_signatures).intersection(right_signatures)
        if left_signatures[key][-1] != right_signatures[key][-1]
    )
    fields = (
        "sourceMode",
        "totalPages",
        "narrativePacing",
        "distributionMode",
        "shortSummary",
        "fullScript",
    )
    story_changes = [
        key
        for key in fields
        if left_story.get(key) != right_story.get(key)
    ]
    return {
        "added_page_ids": added,
        "removed_page_ids": removed,
        "changed_page_ids": changed,
        "story_plan_changed_fields": story_changes,
        "left_hash": stable_hash(left),
        "right_hash": stable_hash(right),
        "identical": not (added or removed or changed or story_changes),
    }


async def project_pages(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    lock: bool = False,
) -> list[models.HQEditorPage]:
    from . import models
    statement = (
        select(models.HQEditorPage)
        .where(
            models.HQEditorPage.organization_id == organization_id,
            models.HQEditorPage.comic_project_id == project_id,
        )
        .order_by(models.HQEditorPage.page_number)
    )
    if lock:
        statement = statement.with_for_update()
    return list((await session.scalars(statement)).all())


async def reorder_story_pages(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    ordered_story_page_ids: list[uuid.UUID],
) -> list[models.HQEditorPage]:
    from . import models
    pages = await project_pages(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
        lock=True,
    )
    story_pages = [
        page for page in pages if page.page_type == "STORY"
    ]
    expected = {page.id for page in story_pages}
    received = set(ordered_story_page_ids)
    if expected != received:
        raise HTTPException(
            409,
            {
                "code": "INVALID_STORY_PAGE_ORDER",
                "missing": [str(item) for item in expected - received],
                "unknown": [str(item) for item in received - expected],
            },
        )

    by_id = {page.id: page for page in story_pages}
    for number, page_id in enumerate(ordered_story_page_ids, start=1):
        page = by_id[page_id]
        page.page_number = 10000 + number
    await session.flush()
    for number, page_id in enumerate(ordered_story_page_ids, start=1):
        page = by_id[page_id]
        page.page_number = number
        page.revision_number += 1
    await session.flush()
    return sorted(pages, key=lambda item: item.page_number)


async def reorder_page_panels(
    session: AsyncSession,
    *,
    actor: ActorContext,
    page_id: uuid.UUID,
    ordered_panel_ids: list[uuid.UUID],
) -> list[models.HQEditorPanel]:
    from . import models
    page = await session.scalar(
        select(models.HQEditorPage)
        .where(
            models.HQEditorPage.organization_id == actor.organization_id,
            models.HQEditorPage.id == page_id,
            models.HQEditorPage.page_type == "STORY",
        )
        .with_for_update()
    )
    if page is None:
        raise HTTPException(404, "Página narrativa não encontrada.")

    panels = list(
        (
            await session.scalars(
                select(models.HQEditorPanel)
                .where(
                    models.HQEditorPanel.organization_id
                    == actor.organization_id,
                    models.HQEditorPanel.page_id == page_id,
                )
                .order_by(models.HQEditorPanel.panel_order)
                .with_for_update()
            )
        ).all()
    )
    expected = {panel.id for panel in panels}
    received = set(ordered_panel_ids)
    if expected != received:
        raise HTTPException(
            409,
            {
                "code": "INVALID_PANEL_ORDER",
                "missing": [str(item) for item in expected - received],
                "unknown": [str(item) for item in received - expected],
            },
        )
    by_id = {panel.id: panel for panel in panels}
    for order, panel_id in enumerate(ordered_panel_ids, start=1):
        by_id[panel_id].panel_order = 1000 + order
    await session.flush()
    for order, panel_id in enumerate(ordered_panel_ids, start=1):
        panel = by_id[panel_id]
        panel.panel_order = order
        panel.accessibility_metadata = {
            **(panel.accessibility_metadata or {}),
            "reading_order": order,
        }
    page.revision_number += 1
    await session.flush()
    return sorted(panels, key=lambda item: item.panel_order)


async def analyze_project(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    expected_story_pages: int,
) -> dict[str, Any]:
    from . import models
    pages = await project_pages(
        session,
        organization_id=actor.organization_id,
        project_id=project_id,
    )
    page_payloads: list[dict[str, Any]] = []
    readability: list[dict[str, Any]] = []
    for page in pages:
        panels = list(
            (
                await session.scalars(
                    select(models.HQEditorPanel)
                    .where(
                        models.HQEditorPanel.organization_id
                        == actor.organization_id,
                        models.HQEditorPanel.page_id == page.id,
                    )
                    .order_by(models.HQEditorPanel.panel_order)
                )
            ).all()
        )
        stage = str(
            (page.background_settings or {}).get(
                "narrative_stage",
                "",
            )
        )
        page_payloads.append(
            {
                "page_id": str(page.id),
                "page_number": page.page_number,
                "page_type": page.page_type,
                "panel_count": len(panels),
                "stage": stage,
            }
        )
        for panel in panels:
            readability.append(
                analyze_panel_readability(
                    panel=panel,
                    page_width=page.page_width,
                    page_height=page.page_height,
                )
            )
    rhythm = narrative_rhythm_analysis(
        pages=page_payloads,
        expected_total=expected_story_pages,
    )
    counts = Counter(item["status"] for item in readability)
    return {
        "rhythm": rhythm,
        "readability": {
            "panels": readability,
            "ready": counts.get("READY", 0),
            "warning": counts.get("WARNING", 0),
            "blocked": counts.get("BLOCKED", 0),
        },
        "publication_status": (
            "BLOCKED"
            if rhythm["status"] == "BLOCKED"
            or counts.get("BLOCKED", 0)
            else "READY_WITH_WARNINGS"
            if rhythm["warning_count"] or counts.get("WARNING", 0)
            else "READY"
        ),
    }
