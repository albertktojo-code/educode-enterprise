from __future__ import annotations

import random
import string
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from .compat import ActorContext


ACTIVITY_TYPES = {
    "MULTIPLE_CHOICE": "Múltipla escolha",
    "TRUE_FALSE": "Verdadeiro ou falso",
    "MATCHING": "Associação",
    "ORDERING": "Ordenação",
    "FILL_BLANKS": "Completar lacunas",
    "CROSSWORD": "Palavras cruzadas",
    "WORD_SEARCH": "Caça-palavras",
    "SHORT_ANSWER": "Resposta curta",
    "ESSAY": "Discursiva",
    "COMPUTATIONAL_THINKING": "Pensamento Computacional",
    "MATHEMATICS": "Matemática",
}

CANONICAL_QUESTION_TYPES = {
    "MULTIPLE_CHOICE": "MULTIPLE_CHOICE",
    "TRUE_FALSE": "TRUE_FALSE",
    "MATCHING": "MATCHING",
    "ORDERING": "ORDERING",
    "FILL_BLANKS": "FILL_BLANKS",
    "CROSSWORD": "CROSSWORD",
    "WORD_SEARCH": "WORD_SEARCH",
    "SHORT_ANSWER": "SHORT_TEXT",
    "ESSAY": "ESSAY",
    # These are pedagogical categories. Until an explicit interaction subtype
    # is provided, they must be reviewed by a teacher rather than auto-scored.
    "COMPUTATIONAL_THINKING": "ESSAY",
    "MATHEMATICS": "ESSAY",
}


def canonical_question_type(
    activity_type: str,
    answer_key: dict[str, Any] | None = None,
) -> str:
    if activity_type == "SHORT_ANSWER" and not any(
        key in (answer_key or {})
        for key in ("accepted", "accepted_answers", "value", "answer")
    ):
        return "ESSAY"
    try:
        return CANONICAL_QUESTION_TYPES[activity_type]
    except KeyError as exc:  # pragma: no cover - guarded by the request schema
        raise ValueError(f"Tipo de atividade nao suportado: {activity_type}") from exc


def canonical_answer_key(
    activity_type: str,
    activity_payload: dict[str, Any],
    answer_key: dict[str, Any],
) -> dict[str, Any]:
    canonical = deepcopy(answer_key)
    if activity_type == "MULTIPLE_CHOICE":
        canonical.setdefault(
            "correct_option_ids",
            [
                str(option.get("id"))
                for option in activity_payload.get("options", [])
                if option.get("correct") and option.get("id") is not None
            ],
        )
    elif activity_type == "TRUE_FALSE" and "correct" not in canonical:
        if isinstance(activity_payload.get("correct"), bool):
            canonical["correct"] = activity_payload["correct"]
    elif activity_type == "MATCHING":
        canonical.setdefault("pairs", activity_payload.get("pairs", []))
    elif activity_type == "ORDERING":
        canonical.setdefault("items", activity_payload.get("items", []))
    elif activity_type == "FILL_BLANKS":
        canonical.setdefault("answers", activity_payload.get("answers", []))
    elif activity_type == "CROSSWORD":
        canonical.setdefault("entries", activity_payload.get("entries", []))
    elif activity_type == "WORD_SEARCH":
        canonical.setdefault("words", activity_payload.get("words", []))
    return canonical


def _rotated(values: list[Any]) -> list[Any]:
    if len(values) < 2:
        return values
    return [*values[1:], values[0]]


def student_activity_payload(
    activity_type: str,
    activity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Return only the interaction data that a student is allowed to see."""
    if activity_type == "MULTIPLE_CHOICE":
        options = activity_payload.get("options", [])
        correct_count = sum(
            bool(option.get("correct"))
            for option in options
            if isinstance(option, dict)
        )
        return {
            "options": [
                {
                    "id": str(option.get("id", index + 1)),
                    "text": str(option.get("text", "")),
                }
                for index, option in enumerate(options)
                if isinstance(option, dict)
            ],
            "selection_mode": (
                "MULTIPLE"
                if correct_count > 1
                else str(activity_payload.get("selection_mode", "SINGLE"))
            ),
        }
    if activity_type == "TRUE_FALSE":
        return {}
    if activity_type == "MATCHING":
        pairs = [
            item
            for item in activity_payload.get("pairs", [])
            if isinstance(item, dict)
        ]
        return {
            "left_items": [
                {"id": str(index), "text": str(item.get("left", ""))}
                for index, item in enumerate(pairs)
            ],
            "right_items": _rotated(
                [
                    {"id": str(index), "text": str(item.get("right", ""))}
                    for index, item in enumerate(pairs)
                ]
            ),
        }
    if activity_type == "ORDERING":
        return {"items": _rotated(list(activity_payload.get("items", [])))}
    if activity_type == "FILL_BLANKS":
        blanks = activity_payload.get("blanks", [])
        if not blanks:
            blanks = [
                {"id": str(index), "label": f"Lacuna {index + 1}"}
                for index, _ in enumerate(activity_payload.get("answers", []))
            ]
        return {
            "blanks": [
                {
                    "id": str(item.get("id", index)),
                    "label": str(item.get("label", f"Lacuna {index + 1}")),
                }
                for index, item in enumerate(blanks)
                if isinstance(item, dict)
            ]
        }
    if activity_type == "CROSSWORD":
        return {
            "entries": [
                {
                    "id": str(index),
                    "clue": str(item.get("clue", "")),
                    "length": len(normalize_word(str(item.get("answer", "")))),
                }
                for index, item in enumerate(
                    activity_payload.get("entries", [])
                )
                if isinstance(item, dict)
            ],
            "accessible_list": activity_payload.get("accessible_list", []),
        }
    if activity_type == "WORD_SEARCH":
        return {
            key: deepcopy(activity_payload[key])
            for key in ("size", "grid", "words")
            if key in activity_payload
        }
    return {"prompt": str(activity_payload.get("prompt", ""))}


def normalize_word(value: str) -> str:
    return "".join(ch for ch in value.upper().strip() if ch.isalnum())


def build_word_search(words: list[str], size: int = 12) -> dict[str, Any]:
    normalized = [normalize_word(word) for word in words if normalize_word(word)]
    if not normalized:
        raise ValueError("Informe ao menos uma palavra.")
    size = max(size, max(len(word) for word in normalized), 8)
    if size > 24:
        raise ValueError("A grade não pode exceder 24 posições.")
    grid = [["" for _ in range(size)] for _ in range(size)]
    placements: list[dict[str, Any]] = []
    for index, word in enumerate(normalized):
        row = index % size
        if len(word) <= size:
            for col, letter in enumerate(word):
                grid[row][col] = letter
            placements.append({"word": word, "row": row, "column": 0, "direction": "H"})
    rng = random.Random("|".join(normalized))
    for row in range(size):
        for col in range(size):
            if not grid[row][col]:
                grid[row][col] = rng.choice(string.ascii_uppercase)
    return {"size": size, "grid": grid, "words": normalized, "placements": placements}


def validate_crossword(entries: list[dict[str, Any]]) -> dict[str, Any]:
    words = [normalize_word(str(item.get("answer", ""))) for item in entries]
    if not words or any(not word for word in words):
        return {"valid": False, "errors": ["Todas as respostas devem possuir letras."]}
    duplicates = sorted({word for word in words if words.count(word) > 1})
    errors = [f"Resposta duplicada: {item}" for item in duplicates]
    for item in entries:
        if not str(item.get("clue", "")).strip():
            errors.append(f"Pista ausente para {item.get('answer', '')}.")
    return {
        "valid": not errors,
        "errors": errors,
        "entries": [
            {**item, "answer": normalize_word(str(item.get("answer", "")))}
            for item in entries
        ],
        "accessible_list": [
            {"number": index + 1, "clue": item.get("clue", ""), "length": len(words[index])}
            for index, item in enumerate(entries)
        ],
    }


def validate_activity_payload(activity_type: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if activity_type == "MULTIPLE_CHOICE":
        options = payload.get("options") or []
        correct = [item for item in options if item.get("correct")]
        if len(options) < 2:
            errors.append("A questão precisa de pelo menos duas alternativas.")
        if not correct:
            errors.append("Marque ao menos uma alternativa correta.")
    elif activity_type == "TRUE_FALSE":
        if payload.get("correct") not in {True, False}:
            errors.append("Defina se a afirmação é verdadeira ou falsa.")
    elif activity_type == "ORDERING":
        if len(payload.get("items") or []) < 2:
            errors.append("Informe ao menos dois itens para ordenar.")
    elif activity_type == "MATCHING":
        if len(payload.get("pairs") or []) < 2:
            errors.append("Informe ao menos dois pares.")
    elif activity_type == "FILL_BLANKS":
        if not payload.get("blanks"):
            errors.append("Informe ao menos uma lacuna.")
    elif activity_type == "CROSSWORD":
        errors.extend(validate_crossword(payload.get("entries") or [])["errors"])
    elif activity_type == "WORD_SEARCH":
        if not payload.get("words"):
            errors.append("Informe as palavras do caça-palavras.")
    elif activity_type in {"SHORT_ANSWER", "ESSAY"}:
        if not payload.get("prompt"):
            errors.append("Informe o enunciado da atividade.")
    return errors


def validate_answer_key(
    activity_type: str,
    activity_payload: dict[str, Any],
    answer_key: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if activity_type == "MULTIPLE_CHOICE":
        if not answer_key.get("correct_option_ids"):
            errors.append("Defina ao menos uma alternativa correta no gabarito.")
    elif activity_type == "TRUE_FALSE":
        if not isinstance(answer_key.get("correct"), bool):
            errors.append("Defina verdadeiro ou falso no gabarito.")
    elif activity_type == "MATCHING":
        if len(answer_key.get("pairs") or []) < 2:
            errors.append("O gabarito deve conter todos os pares.")
    elif activity_type == "ORDERING":
        if len(answer_key.get("items") or []) < 2:
            errors.append("O gabarito deve conter a ordem esperada.")
    elif activity_type == "FILL_BLANKS":
        blanks = activity_payload.get("blanks") or []
        answers = answer_key.get("answers") or []
        if not answers or len(answers) != len(blanks):
            errors.append("Cada lacuna deve possuir uma resposta no gabarito.")
    elif activity_type == "CROSSWORD":
        if not answer_key.get("entries"):
            errors.append("A cruzadinha deve possuir respostas no gabarito.")
    elif activity_type == "WORD_SEARCH":
        if not answer_key.get("words"):
            errors.append("O caça-palavras deve possuir palavras no gabarito.")
    return errors


def pedagogical_trace(
    *,
    source_page_id: uuid.UUID | None,
    source_panel_id: uuid.UUID | None,
    bncc_codes: list[str],
    ct_pillars: list[str],
    subject: str,
    theme: str,
) -> dict[str, Any]:
    return {
        "source_page_id": str(source_page_id) if source_page_id else None,
        "source_panel_id": str(source_panel_id) if source_panel_id else None,
        "bncc_codes": bncc_codes,
        "computational_thinking_pillars": ct_pillars,
        "subject": subject,
        "theme": theme,
        "teacher_review_required": True,
    }


async def next_special_page_number(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
) -> int:
    from . import models
    current = await session.scalar(
        select(func.max(models.HQEditorPage.page_number)).where(
            models.HQEditorPage.organization_id == organization_id,
            models.HQEditorPage.comic_project_id == project_id,
        )
    )
    return max(1000, int(current or 0) + 1)


async def create_activity(
    session: AsyncSession,
    *,
    actor: ActorContext,
    project_id: uuid.UUID,
    data: Any,
) -> tuple[Any, Any]:
    from app.assessment_hub.models import (
        QuestionItem,
        QuestionSkillLink,
        QuestionVersion,
    )

    from . import models

    answer_key = canonical_answer_key(
        data.activity_type,
        data.activity_payload,
        data.answer_key,
    )
    errors = validate_activity_payload(data.activity_type, data.activity_payload)
    errors.extend(
        validate_answer_key(
            data.activity_type,
            data.activity_payload,
            answer_key,
        )
    )
    if errors:
        raise HTTPException(422, {"code": "INVALID_ACTIVITY", "errors": errors})

    page = models.HQEditorPage(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        page_number=await next_special_page_number(
            session,
            organization_id=actor.organization_id,
            project_id=project_id,
        ),
        page_type="ACTIVITY",
        title=data.title,
        status="DRAFT",
        page_width=1200,
        page_height=1600,
        background_settings={"activity_layout": data.layout_code},
        accessibility_settings=data.accessibility,
        content_layers=[],
        preservation_settings={},
        continuity_metadata={},
        cover_generation={},
        revision_number=1,
        created_by_user_id=actor.user_id,
    )
    session.add(page)
    await session.flush()

    code = f"HQ-{str(project_id)[:8]}-{uuid.uuid4().hex[:8]}".upper()
    question = QuestionItem(
        organization_id=actor.organization_id,
        code=code,
        title=data.title,
        subject=data.subject,
        school_year=data.school_year,
        source_type="HQ_ACTIVITY",
        status="DRAFT",
        current_version=1,
        created_by_user_id=actor.user_id,
    )
    session.add(question)
    await session.flush()

    version = QuestionVersion(
        organization_id=actor.organization_id,
        question_id=question.id,
        version=1,
        question_type=canonical_question_type(data.activity_type, answer_key),
        statement=data.instructions,
        options=data.activity_payload.get("options", []),
        correct_answer=answer_key,
        explanation=data.explanation,
        rubric=data.rubric,
        predicted_difficulty=data.predicted_difficulty,
        max_score=data.max_score,
        accessibility=data.accessibility,
        metadata_payload={
            "source_type": "HQ_ACTIVITY",
            "hq_activity_type": data.activity_type,
            "comic_project_id": str(project_id),
            "activity_page_id": str(page.id),
            "activity_payload": data.activity_payload,
        },
        status="DRAFT",
        created_by_user_id=actor.user_id,
    )
    session.add(version)
    await session.flush()

    for code_value in data.bncc_codes:
        session.add(QuestionSkillLink(
            organization_id=actor.organization_id,
            question_version_id=version.id,
            skill_type="BNCC",
            skill_code=code_value,
            skill_name=code_value,
            weight=1.0,
            is_primary=False,
        ))
    for pillar in data.ct_pillars:
        session.add(QuestionSkillLink(
            organization_id=actor.organization_id,
            question_version_id=version.id,
            skill_type="COMPUTATIONAL_THINKING",
            skill_code=pillar,
            skill_name=pillar,
            weight=1.0,
            is_primary=False,
        ))

    binding = models.HQActivityBinding(
        organization_id=actor.organization_id,
        comic_project_id=project_id,
        activity_page_id=page.id,
        source_page_id=data.source_page_id,
        source_panel_id=data.source_panel_id,
        question_id=question.id,
        question_version_id=version.id,
        publication_id=None,
        activity_type=data.activity_type,
        title=data.title,
        instructions=data.instructions,
        activity_payload=data.activity_payload,
        answer_key=answer_key,
        pedagogical_links=pedagogical_trace(
            source_page_id=data.source_page_id,
            source_panel_id=data.source_panel_id,
            bncc_codes=data.bncc_codes,
            ct_pillars=data.ct_pillars,
            subject=data.subject,
            theme=data.theme,
        ),
        accessibility=data.accessibility,
        difficulty=data.difficulty,
        status="DRAFT",
        display_order=data.display_order,
        max_score=data.max_score,
        teacher_review_required=True,
        created_by_user_id=actor.user_id,
    )
    session.add(binding)
    await session.flush()
    return binding, page


async def approve_activity(
    session: AsyncSession,
    *,
    actor: ActorContext,
    activity_id: uuid.UUID,
) -> Any:
    from app.assessment_hub.models import QuestionItem, QuestionVersion

    from . import models

    item = await session.scalar(
        select(models.HQActivityBinding)
        .where(
            models.HQActivityBinding.organization_id == actor.organization_id,
            models.HQActivityBinding.id == activity_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Atividade não encontrada.")
    errors = validate_activity_payload(item.activity_type, item.activity_payload)
    errors.extend(
        validate_answer_key(
            item.activity_type,
            item.activity_payload,
            item.answer_key,
        )
    )
    if errors:
        raise HTTPException(409, {"code": "ACTIVITY_NOT_READY", "errors": errors})
    item.status = "APPROVED"
    item.reviewed_by_user_id = actor.user_id
    item.reviewed_at = datetime.now(UTC)
    if item.question_version_id:
        version = await session.get(QuestionVersion, item.question_version_id)
        if version:
            version.status = "PUBLISHED"
            version.published_by_user_id = actor.user_id
            version.published_at = datetime.now(UTC)
    if item.question_id:
        question = await session.get(QuestionItem, item.question_id)
        if question:
            question.status = "PUBLISHED"
            question.updated_by_user_id = actor.user_id
    await session.flush()
    return item
