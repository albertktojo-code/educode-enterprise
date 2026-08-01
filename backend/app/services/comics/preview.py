from __future__ import annotations

from collections import Counter
from typing import Any

from app.models.comic import ComicVersion, GeneratedComic, PreviewReviewStatus


def _value(value: object) -> str:
    return str(getattr(value, "value", value))


def _words(text: str) -> int:
    return len([part for part in text.replace("\n", " ").split(" ") if part.strip()])


def _finding(
    severity: str,
    code: str,
    message: str,
    *,
    page_id: str | None = None,
    panel_id: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if page_id is not None:
        result["page_id"] = page_id
    if panel_id is not None:
        result["panel_id"] = panel_id
    return result


def build_storyboard(comic: GeneratedComic) -> dict[str, Any]:
    scenes: list[dict[str, Any]] = []
    emotional_arc: list[str] = []
    plot_points: list[dict[str, Any]] = []
    sequence = 1

    for page in sorted(comic.pages, key=lambda item: item.page_number):
        for panel in sorted(page.panels, key=lambda item: item.reading_order):
            dialogue = [
                {
                    "balloon_id": str(balloon.id),
                    "sequence_number": balloon.sequence_number,
                    "speaker": balloon.speaker_name_snapshot or "Narrador",
                    "type": _value(balloon.balloon_type),
                    "text": balloon.text,
                    "emotion": balloon.emotion,
                }
                for balloon in sorted(
                    panel.balloons,
                    key=lambda item: item.sequence_number,
                )
            ]
            visual_prompt = dict(panel.visual_prompt or {})
            dialogue_text = " ".join(str(item["text"]) for item in dialogue)
            duration = max(3, min(18, 3 + _words(dialogue_text) // 4))
            scene = {
                "sequence_number": sequence,
                "page_id": str(page.id),
                "page_number": page.page_number,
                "page_role": page.page_role,
                "panel_id": str(panel.id),
                "panel_number": panel.panel_number,
                "reading_order": panel.reading_order,
                "review_status": _value(panel.preview_review_status),
                "scene_summary": panel.scene_description,
                "narrative_goal": panel.narrative_goal,
                "pedagogical_goal": panel.pedagogical_goal,
                "ct_pillar_codes": list(panel.ct_pillar_codes or []),
                "shot_type": str(visual_prompt.get("shot_type", "plano médio")),
                "camera_direction": visual_prompt.get("camera_direction"),
                "action": visual_prompt.get("action", panel.scene_description),
                "emotion": panel.emotion,
                "pacing": panel.pacing,
                "plot_function": panel.plot_function,
                "previous_panel_summary": panel.previous_panel_summary,
                "next_panel_hook": panel.next_panel_hook,
                "initial_state": dict(panel.initial_state or {}),
                "final_state": dict(panel.final_state or {}),
                "transition": str(visual_prompt.get("transition", "corte")),
                "estimated_duration_seconds": duration,
                "dialogue": dialogue,
                "image_asset_path": panel.image_asset_path,
                "alt_text": panel.alt_text,
                "audio_description": panel.audio_description,
            }
            scenes.append(scene)
            emotional_arc.append(panel.emotion)

            plot_types = {"clue", "false_solution", "plot_twist", "resolution"}
            if panel.plot_function in plot_types:
                plot_points.append(
                    {
                        "sequence_number": sequence,
                        "page_number": page.page_number,
                        "panel_number": panel.panel_number,
                        "type": panel.plot_function,
                        "summary": panel.narrative_goal or panel.scene_description,
                    }
                )
            sequence += 1

    estimated_duration = sum(
        int(scene["estimated_duration_seconds"])
        for scene in scenes
    )
    return {
        "comic_id": str(comic.id),
        "title": comic.title,
        "version": comic.current_version,
        "page_count": len(comic.pages),
        "scene_count": len(scenes),
        "estimated_duration_seconds": estimated_duration,
        "emotional_arc": emotional_arc,
        "plot_points": plot_points,
        "scenes": scenes,
    }


def validate_preview(comic: GeneratedComic) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    total_pages = len(comic.pages)
    total_panels = 0
    approved_pages = 0
    approved_panels = 0
    prior_plot_functions: list[str] = []
    approved_statuses = {
        PreviewReviewStatus.APPROVED,
        PreviewReviewStatus.LOCKED,
    }

    for page in sorted(comic.pages, key=lambda item: item.page_number):
        if page.preview_review_status in approved_statuses:
            approved_pages += 1
        if not page.panels:
            findings.append(
                _finding(
                    "error",
                    "empty_page",
                    f"Página {page.page_number} sem quadros.",
                    page_id=str(page.id),
                )
            )
        if page.panel_count != len(page.panels):
            findings.append(
                _finding(
                    "error",
                    "panel_count_mismatch",
                    (
                        f"Página {page.page_number} declara {page.panel_count} "
                        f"quadros, mas possui {len(page.panels)}."
                    ),
                    page_id=str(page.id),
                )
            )

        for panel in sorted(page.panels, key=lambda item: item.reading_order):
            total_panels += 1
            if panel.preview_review_status in approved_statuses:
                approved_panels += 1
            page_id = str(page.id)
            panel_id = str(panel.id)

            if not panel.image_asset_path:
                findings.append(
                    _finding(
                        "warning",
                        "missing_image",
                        (
                            f"Página {page.page_number}, quadro "
                            f"{panel.panel_number}: imagem ainda não definida."
                        ),
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )
            if not panel.alt_text:
                findings.append(
                    _finding(
                        "warning",
                        "missing_alt_text",
                        (
                            f"Página {page.page_number}, quadro "
                            f"{panel.panel_number}: texto alternativo ausente."
                        ),
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )

            word_count = sum(_words(balloon.text) for balloon in panel.balloons)
            word_limit = panel.text_word_limit or 80
            if word_count > word_limit:
                findings.append(
                    _finding(
                        "warning",
                        "text_overflow",
                        (
                            f"Página {page.page_number}, quadro {panel.panel_number}: "
                            f"{word_count} palavras para limite de {word_limit}."
                        ),
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )

            if (
                panel.plot_function == "plot_twist"
                and "clue" not in prior_plot_functions
            ):
                findings.append(
                    _finding(
                        "error",
                        "plot_twist_without_clue",
                        (
                            f"Página {page.page_number}, quadro {panel.panel_number}: "
                            "reviravolta sem pista anterior."
                        ),
                        page_id=page_id,
                        panel_id=panel_id,
                    )
                )
            prior_plot_functions.append(panel.plot_function)

    open_comments = sum(
        1
        for comment in comic.review_comments
        if _value(comment.status) in {"open", "in_review"}
    )
    if open_comments:
        findings.append(
            _finding(
                "warning",
                "open_comments",
                f"Há {open_comments} comentário(s) de revisão pendente(s).",
            )
        )

    errors = sum(1 for item in findings if item["severity"] == "error")
    warnings = sum(1 for item in findings if item["severity"] == "warning")
    coverage = (
        100.0
        if total_panels == 0
        else round(approved_panels / total_panels * 100, 1)
    )
    status = "ready"
    if errors:
        status = "blocked"
    elif warnings or approved_pages < total_pages or approved_panels < total_panels:
        status = "ready_with_warnings"

    checklist = [
        {
            "code": "pages_reviewed",
            "label": "Todas as páginas foram revisadas",
            "passed": approved_pages == total_pages and total_pages > 0,
        },
        {
            "code": "panels_reviewed",
            "label": "Todos os quadros foram revisados",
            "passed": approved_panels == total_panels and total_panels > 0,
        },
        {
            "code": "no_blocking_findings",
            "label": "Nenhum erro bloqueante",
            "passed": errors == 0,
        },
        {
            "code": "no_open_comments",
            "label": "Nenhum comentário pendente",
            "passed": open_comments == 0,
        },
        {
            "code": "continuity",
            "label": "Continuidade narrativa válida",
            "passed": comic.continuity_score >= 70,
        },
        {
            "code": "pedagogical",
            "label": "Cobertura pedagógica mínima",
            "passed": comic.pedagogical_score >= 60,
        },
    ]
    return {
        "comic_id": str(comic.id),
        "status": status,
        "review_coverage_percent": coverage,
        "approved_pages": approved_pages,
        "total_pages": total_pages,
        "approved_panels": approved_panels,
        "total_panels": total_panels,
        "error_count": errors,
        "warning_count": warnings,
        "findings": findings,
        "checklist": checklist,
    }


def _indexed_pages(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pages = snapshot.get("pages", [])
    return {
        str(page.get("id")): page
        for page in pages
        if isinstance(page, dict)
    }


def _indexed_panels(page: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    panels = (page or {}).get("panels", [])
    return {
        str(panel.get("id")): panel
        for panel in panels
        if isinstance(panel, dict)
    }


def compare_version_snapshots(
    from_version: ComicVersion,
    to_version: ComicVersion,
) -> dict[str, Any]:
    before = dict(from_version.snapshot_json)
    after = dict(to_version.snapshot_json)
    before_pages = _indexed_pages(before)
    after_pages = _indexed_pages(after)
    changed_pages: list[dict[str, Any]] = []

    for page_id in sorted(set(before_pages) | set(after_pages)):
        old = before_pages.get(page_id)
        new = after_pages.get(page_id)
        if old == new:
            continue

        status = "modified"
        if old is None:
            status = "added"
        elif new is None:
            status = "removed"

        old_panels = _indexed_panels(old)
        new_panels = _indexed_panels(new)
        panel_changes: list[dict[str, Any]] = []
        for panel_id in sorted(set(old_panels) | set(new_panels)):
            old_panel = old_panels.get(panel_id)
            new_panel = new_panels.get(panel_id)
            if old_panel == new_panel:
                continue

            panel_status = "modified"
            if old_panel is None:
                panel_status = "added"
            elif new_panel is None:
                panel_status = "removed"

            changed_fields = [
                key
                for key in sorted(
                    set((old_panel or {}).keys())
                    | set((new_panel or {}).keys())
                )
                if (old_panel or {}).get(key) != (new_panel or {}).get(key)
            ]
            panel_changes.append(
                {
                    "panel_id": panel_id,
                    "status": panel_status,
                    "changed_fields": changed_fields,
                }
            )

        changed_pages.append(
            {
                "page_id": page_id,
                "page_number": (new or old or {}).get("page_number"),
                "status": status,
                "panel_changes": panel_changes,
            }
        )

    top_level_changes = [
        key
        for key in sorted(set(before) | set(after))
        if key != "pages" and before.get(key) != after.get(key)
    ]
    counts = Counter(change["status"] for change in changed_pages)
    return {
        "from_version": from_version.version_number,
        "to_version": to_version.version_number,
        "top_level_changes": top_level_changes,
        "page_summary": dict(counts),
        "changed_pages": changed_pages,
    }
