from __future__ import annotations

import re

from ..enums import (
    AccessibleVersionStatus,
    AdaptationType,
    EquivalenceStatus,
    GenerationMethod,
)
from ..schemas import AccessibleVersionGenerateInput, AccessibleVersionGenerateResult


SIMPLE_REPLACEMENTS: dict[str, str] = {
    "posteriormente": "depois",
    "anteriormente": "antes",
    "efetuar": "fazer",
    "utilizar": "usar",
    "identifique": "encontre",
    "selecione": "escolha",
    "respectivamente": "na mesma ordem",
    "compreender": "entender",
}


def _plain_language(content: str) -> str:
    result = content
    for source, target in SIMPLE_REPLACEMENTS.items():
        result = re.sub(rf"\b{source}\b", target, result, flags=re.IGNORECASE)
    sentences = re.split(r"(?<=[.!?])\s+", result.strip())
    paragraphs: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= 22:
            paragraphs.append(sentence)
            continue
        midpoint = len(words) // 2
        paragraphs.append(" ".join(words[:midpoint]) + ".")
        paragraphs.append(" ".join(words[midpoint:]))
    return "\n\n".join(item.strip() for item in paragraphs if item.strip())


def _step_by_step(content: str) -> str:
    chunks = [chunk.strip() for chunk in re.split(r"[.;]\s+", content) if chunk.strip()]
    if len(chunks) <= 1:
        chunks = [content.strip()]
    return "\n".join(f"{index}. {chunk.rstrip('.')}" for index, chunk in enumerate(chunks, start=1))


def generate_accessible_version(
    payload: AccessibleVersionGenerateInput,
) -> AccessibleVersionGenerateResult:
    adapted = payload.content.strip()
    metadata: dict[str, object] = {
        "requires_human_review": True,
        "preserves_learning_objective": True,
        "source_images_without_description": payload.source_images_without_description,
    }
    warnings: list[str] = []

    if payload.adaptation_type in {AdaptationType.PLAIN_LANGUAGE, AdaptationType.EASY_READING}:
        adapted = _plain_language(adapted)
        metadata.update({"sentence_target_words": 22, "simplified_vocabulary": True})
    elif payload.adaptation_type in {AdaptationType.STEP_BY_STEP, AdaptationType.OBJECTIVE_INSTRUCTIONS}:
        adapted = _step_by_step(adapted)
        metadata.update({"numbered_steps": True, "single_instruction_per_step": True})
    elif payload.adaptation_type == AdaptationType.SCREEN_READER:
        adapted = f"Título: {payload.title}\n\nConteúdo:\n{adapted}"
        metadata.update({"semantic_headings_required": True, "aria_review_required": True})
    elif payload.adaptation_type == AdaptationType.LARGE_PRINT:
        metadata.update({"minimum_font_size_px": 20, "line_height": 1.6, "responsive_zoom": True})
    elif payload.adaptation_type == AdaptationType.HIGH_CONTRAST:
        metadata.update({"minimum_contrast_ratio": "4.5:1", "color_only_information_forbidden": True})
    elif payload.adaptation_type == AdaptationType.REDUCED_VISUAL_STIMULUS:
        metadata.update({"decorative_elements_removed": True, "one_task_per_view": True})
    elif payload.adaptation_type in {AdaptationType.IMAGE_DESCRIPTION, AdaptationType.AUDIO_DESCRIPTION}:
        if payload.source_images_without_description > 0:
            adapted += "\n\n[Descrição das imagens pendente de revisão humana.]"
            warnings.append("Existem imagens sem descrição; a versão não deve ser publicada antes da revisão.")
        metadata.update({"image_descriptions_required": True})
    elif payload.adaptation_type == AdaptationType.KEYBOARD_NAVIGATION:
        metadata.update({"keyboard_order_review_required": True, "visible_focus_required": True})
    elif payload.adaptation_type == AdaptationType.CAPTIONS:
        metadata.update({"captions_required": True, "speaker_identification_required": True})
    elif payload.adaptation_type == AdaptationType.VISUAL_SUPPORT:
        adapted += "\n\n[Apoio visual deve representar as etapas sem revelar a resposta.]"
        metadata.update({"visual_support_required": True})

    equivalence = EquivalenceStatus.NEEDS_PEDAGOGICAL_REVIEW
    if payload.adaptation_type in {
        AdaptationType.LARGE_PRINT,
        AdaptationType.HIGH_CONTRAST,
        AdaptationType.KEYBOARD_NAVIGATION,
    }:
        equivalence = EquivalenceStatus.PRESERVED

    warnings.append("Versão criada automaticamente; revisão pedagógica e de acessibilidade obrigatória.")
    return AccessibleVersionGenerateResult(
        title=f"{payload.title} — versão acessível",
        content=adapted,
        adaptation_type=payload.adaptation_type,
        accessibility_metadata=metadata,
        pedagogical_snapshot={
            "learning_objective": payload.learning_objective,
            "expected_answer": payload.expected_answer,
            "assessment_criteria": payload.assessment_criteria,
        },
        equivalence_status=equivalence,
        generation_method=GenerationMethod.DETERMINISTIC,
        status=AccessibleVersionStatus.NEEDS_REVIEW.value,
        warnings=warnings,
    )
