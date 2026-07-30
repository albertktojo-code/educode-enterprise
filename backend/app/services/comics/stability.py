from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.models.comic import (
    BalloonType,
    GeneratedComic,
    GenerationScope,
    ReviewCommentStatus,
    ReviewDecision,
    ReviewSpecialty,
)
from app.services.comics.continuity import validate_payload
from app.services.comics.manager import snapshot_pages

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ0-9]+)?")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
SPEAKER_REQUIRED = {
    BalloonType.SPEECH.value,
    BalloonType.THOUGHT.value,
    BalloonType.SHOUT.value,
    BalloonType.WHISPER.value,
}


@dataclass(frozen=True)
class StabilityFinding:
    severity: str
    code: str
    message: str
    page_id: UUID | None = None
    panel_id: UUID | None = None
    balloon_id: UUID | None = None


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in SENTENCE_RE.findall(text) if item.strip()]


def _language_metrics(text: str) -> dict[str, float | int]:
    words = _words(text)
    sentences = _sentences(text)
    long_words = [word for word in words if len(word) >= 10]
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "average_words_per_sentence": round(
            len(words) / max(1, len(sentences)), 2
        ),
        "average_word_length": round(
            sum(len(word) for word in words) / max(1, len(words)), 2
        ),
        "long_word_ratio": round(len(long_words) / max(1, len(words)), 3),
    }


def _canonical_character_names(comic: GeneratedComic) -> set[str]:
    names: set[str] = set()
    for page in comic.pages:
        for panel in page.panels:
            frozen = panel.frozen_assets or {}
            characters = frozen.get("characters", [])
            if not isinstance(characters, list):
                continue
            for item in characters:
                if isinstance(item, dict) and str(item.get("name", "")).strip():
                    names.add(str(item["name"]).strip())
    if not names:
        story_characters = comic.story_state.get("characters", [])
        if isinstance(story_characters, list):
            names.update(str(item).strip() for item in story_characters if str(item).strip())
    return names


def analyze_stability(comic: GeneratedComic) -> dict[str, Any]:
    findings: list[StabilityFinding] = []
    page_densities: list[dict[str, Any]] = []
    all_dialogue_text: list[str] = []
    canonical_names = _canonical_character_names(comic)
    spoken_names: list[str] = []

    for page in sorted(comic.pages, key=lambda item: item.page_number):
        page_words = 0
        panel_area = 0.0
        balloon_area_weighted = 0.0
        for panel in page.panels:
            panel_area += max(0.0, panel.width) * max(0.0, panel.height)
            if not panel.alt_text or not panel.alt_text.strip():
                findings.append(
                    StabilityFinding(
                        "warning",
                        "missing_alt_text",
                        "O quadro ainda não possui texto alternativo.",
                        page_id=page.id,
                        panel_id=panel.id,
                    )
                )
            if not panel.visual_prompt or not bool(
                panel.visual_prompt.get("image_without_balloons", False)
            ):
                findings.append(
                    StabilityFinding(
                        "error",
                        "visual_prompt_embeds_text",
                        "O prompt visual deve exigir imagem limpa, sem balões incorporados.",
                        page_id=page.id,
                        panel_id=panel.id,
                    )
                )
            for balloon in panel.balloons:
                balloon_words = _words(balloon.text)
                page_words += len(balloon_words)
                all_dialogue_text.append(balloon.text)
                balloon_area_weighted += (
                    max(0.0, balloon.width) * max(0.0, balloon.height)
                ) * (max(0.0, panel.width) * max(0.0, panel.height) / 10000.0)
                balloon_type = _enum_value(balloon.balloon_type)
                speaker = (balloon.speaker_name_snapshot or "").strip()
                if balloon_type in SPEAKER_REQUIRED and not speaker:
                    findings.append(
                        StabilityFinding(
                            "error",
                            "missing_balloon_speaker",
                            "Um balão de fala, pensamento, grito ou sussurro precisa de personagem.",
                            page_id=page.id,
                            panel_id=panel.id,
                            balloon_id=balloon.id,
                        )
                    )
                if speaker:
                    spoken_names.append(speaker)
                    if canonical_names and speaker not in canonical_names:
                        findings.append(
                            StabilityFinding(
                                "warning",
                                "unknown_character_name",
                                f"O nome ‘{speaker}’ não corresponde aos personagens congelados da HQ.",
                                page_id=page.id,
                                panel_id=panel.id,
                                balloon_id=balloon.id,
                            )
                        )
                metrics = _language_metrics(balloon.text)
                if metrics["word_count"] > 42:
                    findings.append(
                        StabilityFinding(
                            "warning",
                            "long_balloon",
                            "O balão possui mais de 42 palavras e pode ficar pouco legível.",
                            page_id=page.id,
                            panel_id=panel.id,
                            balloon_id=balloon.id,
                        )
                    )
                if float(metrics["average_words_per_sentence"]) > 22:
                    findings.append(
                        StabilityFinding(
                            "warning",
                            "complex_sentence",
                            "A fala possui frases longas para leitura em balão de HQ.",
                            page_id=page.id,
                            panel_id=panel.id,
                            balloon_id=balloon.id,
                        )
                    )

        panel_coverage = min(1.5, panel_area / 10000.0)
        balloon_pressure = min(1.0, balloon_area_weighted / 2200.0)
        text_pressure = min(1.0, page_words / 220.0)
        density_score = round(
            min(100.0, panel_coverage * 50 + balloon_pressure * 25 + text_pressure * 25),
            1,
        )
        classification = (
            "high" if density_score >= 78 else "moderate" if density_score >= 50 else "low"
        )
        page_densities.append(
            {
                "page_id": page.id,
                "page_number": page.page_number,
                "panel_coverage_percent": round(panel_coverage * 100, 1),
                "word_count": page_words,
                "density_score": density_score,
                "classification": classification,
            }
        )
        if classification == "high":
            findings.append(
                StabilityFinding(
                    "warning",
                    "high_page_density",
                    "A página apresenta alta densidade visual e textual.",
                    page_id=page.id,
                )
            )

    normalized = [re.sub(r"[^a-z0-9]", "", name.lower()) for name in spoken_names]
    collisions = {name for name, count in Counter(normalized).items() if name and count > 1}
    if collisions and canonical_names:
        canonical_normalized = {
            re.sub(r"[^a-z0-9]", "", name.lower()) for name in canonical_names
        }
        unknown_collision = collisions - canonical_normalized
        if unknown_collision:
            findings.append(
                StabilityFinding(
                    "info",
                    "character_alias_review",
                    "Há variações de nomes que devem ser revisadas como apelidos autorizados.",
                )
            )

    complete_text = " ".join(all_dialogue_text)
    language = _language_metrics(complete_text)
    if float(language["long_word_ratio"]) > 0.2:
        findings.append(
            StabilityFinding(
                "info",
                "advanced_vocabulary",
                "A proporção de palavras longas pode exigir adaptação à faixa etária.",
            )
        )
    penalty = sum(
        16 if item.severity == "error" else 7 if item.severity == "warning" else 2
        for item in findings
    )
    score = max(0.0, min(100.0, 100.0 - penalty))
    return {
        "comic_id": comic.id,
        "score": score,
        "language_metrics": language,
        "page_densities": page_densities,
        "findings": [item.__dict__ for item in findings],
        "generated_at": datetime.now(UTC),
    }


def canvas_readiness(comic: GeneratedComic) -> dict[str, Any]:
    pages = snapshot_pages(comic)
    continuity_score, continuity_findings = validate_payload(pages)
    sequential_pages = [page.page_number for page in comic.pages] == list(
        range(1, len(comic.pages) + 1)
    )
    reading_order_ok = all(
        sorted(panel.reading_order for panel in page.panels)
        == list(range(1, len(page.panels) + 1))
        for page in comic.pages
    )
    panels_in_bounds = all(
        panel.position_x >= 0
        and panel.position_y >= 0
        and panel.position_x + panel.width <= 100
        and panel.position_y + panel.height <= 100
        for page in comic.pages
        for panel in page.panels
    )
    images_separated = all(
        bool(panel.visual_prompt.get("image_without_balloons", False))
        for page in comic.pages
        for panel in page.panels
    )
    alt_text_complete = all(
        bool(panel.alt_text and panel.alt_text.strip())
        for page in comic.pages
        for panel in page.panels
    )
    assets_frozen = all(
        bool(panel.frozen_assets)
        for page in comic.pages
        for panel in page.panels
    )
    prompts_structured = all(
        isinstance(panel.visual_prompt, dict) and bool(panel.visual_prompt)
        for page in comic.pages
        for panel in page.panels
    )
    approved = {
        _enum_value(item.specialty): _enum_value(item.decision)
        for item in comic.review_approvals
    }
    reviews_complete = all(
        approved.get(specialty.value) == ReviewDecision.APPROVED.value
        for specialty in ReviewSpecialty
    )
    no_open_comments = not any(
        item.status in {ReviewCommentStatus.OPEN, ReviewCommentStatus.IN_REVIEW}
        for item in comic.review_comments
    )
    checklist = [
        ("pages_numbered", "Páginas numeradas em sequência", sequential_pages, True),
        ("reading_order", "Ordem de leitura definida", reading_order_ok, True),
        ("panels_in_bounds", "Quadros dentro dos limites", panels_in_bounds, True),
        ("balloons_separate", "Balões separados das imagens", images_separated, True),
        ("alt_text", "Texto alternativo preenchido", alt_text_complete, True),
        ("assets_frozen", "Assets vinculados por versão", assets_frozen, False),
        ("visual_prompts", "Prompts visuais estruturados", prompts_structured, True),
        ("continuity", "Continuidade sem erros bloqueantes", not any(
            item.severity == "error" for item in continuity_findings
        ), True),
        ("reviews", "Revisões obrigatórias concluídas", reviews_complete, True),
        ("comments", "Nenhum comentário de revisão aberto", no_open_comments, True),
    ]
    required_ok = all(passed for _, _, passed, required in checklist if required)
    all_ok = all(passed for _, _, passed, _ in checklist)
    status = "ready" if all_ok else "ready_with_warnings" if required_ok else "not_ready"
    return {
        "comic_id": comic.id,
        "status": status,
        "continuity_score": continuity_score,
        "checklist": [
            {
                "code": code,
                "label": label,
                "passed": passed,
                "required": required,
            }
            for code, label, passed, required in checklist
        ],
        "checked_at": datetime.now(UTC),
    }


def regeneration_policy(
    comic: GeneratedComic,
    *,
    scope: GenerationScope,
    page_id: UUID | None,
    panel_id: UUID | None,
    preserve_dialogue: bool,
    preserve_scene: bool,
) -> dict[str, Any]:
    ordered = [
        panel
        for page in sorted(comic.pages, key=lambda item: item.page_number)
        for panel in sorted(page.panels, key=lambda item: item.reading_order)
    ]
    selected: list[Any] = []
    if scope == GenerationScope.COMIC:
        selected = ordered
    elif scope == GenerationScope.PAGE:
        selected = [
            panel for page in comic.pages if page.id == page_id for panel in page.panels
        ]
    elif scope == GenerationScope.FROM_PANEL:
        start = next((index for index, item in enumerate(ordered) if item.id == panel_id), -1)
        selected = ordered[start:] if start >= 0 else []
    else:
        selected = [item for item in ordered if item.id == panel_id]
    locked = sorted({lock for panel in selected for lock in (panel.locked_elements or [])})
    if preserve_dialogue and "dialogue" not in locked:
        locked.append("dialogue")
    if preserve_scene and "scene" not in locked:
        locked.append("scene")
    mutable = {
        GenerationScope.COMIC: ["story_structure", "scenes", "dialogues", "layout"],
        GenerationScope.PAGE: ["page_panels", "scenes", "dialogues"],
        GenerationScope.PANEL: ["scene", "dialogue", "narrative_state"],
        GenerationScope.BALLOONS: ["balloons"],
        GenerationScope.DIALOGUE: ["dialogue"],
        GenerationScope.SCENE: ["scene", "visual_prompt"],
        GenerationScope.FROM_PANEL: ["selected_panel_and_following"],
    }[scope]
    warnings: list[str] = []
    if scope == GenerationScope.FROM_PANEL:
        warnings.append("A operação pode alterar todos os quadros posteriores ao selecionado.")
    if not selected:
        warnings.append("Nenhum quadro corresponde ao alvo informado.")
    if locked:
        warnings.append("Elementos bloqueados serão preservados: " + ", ".join(locked))
    facts = comic.story_state.get("facts_used", [])
    return {
        "comic_id": comic.id,
        "scope": scope,
        "affected_panel_ids": [panel.id for panel in selected],
        "mutable_elements": [item for item in mutable if item not in locked],
        "locked_elements": locked,
        "immutable_facts": [str(item) for item in facts] if isinstance(facts, list) else [],
        "warnings": warnings,
    }
