from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment_hub.services.scoring import (
    apply_review_policy,
    score_response,
)

if TYPE_CHECKING:
    from .compat import ActorContext


OBJECTIVE_TYPES = {
    "MULTIPLE_CHOICE",
    "TRUE_FALSE",
    "MATCHING",
    "ORDERING",
    "FILL_BLANKS",
    "CROSSWORD",
    "WORD_SEARCH",
}


def score_objective(
    activity_type: str,
    answer_key: dict[str, Any],
    response: dict[str, Any],
    max_score: float,
    correction_mode: str | None = None,
) -> dict[str, Any]:
    if activity_type not in OBJECTIVE_TYPES:
        return {
            "status": "REQUIRES_REVIEW",
            "score": None,
            "max_score": max_score,
            "percentage": None,
            "correct": None,
        }

    scored = apply_review_policy(
        score_response(
            activity_type,
            answer_key,
            response,
            max_score,
        ),
        correction_mode,
    )
    return {
        "status": (
            "REQUIRES_REVIEW"
            if scored.requires_human_review
            else "SCORED"
        ),
        "score": scored.score,
        "max_score": scored.max_score,
        "percentage": (
            None
            if scored.score is None
            else round((float(scored.score) / scored.max_score) * 100, 2)
        ),
        "correct": scored.is_correct,
    }


def feedback_for_result(
    *,
    result: dict[str, Any],
    templates: dict[str, Any],
    hints: list[dict[str, Any]],
    source_reference: dict[str, Any],
) -> dict[str, Any]:
    if result["status"] == "REQUIRES_REVIEW":
        message = templates.get(
            "requires_review",
            "Sua resposta será analisada pelo professor.",
        )
        return {
            "message": message,
            "hint": None,
            "review_required": True,
            "source_reference": source_reference,
        }

    correct = bool(result.get("correct"))
    key = "correct" if correct else "incorrect"
    default = (
        "Muito bem! Você compreendeu o conceito."
        if correct
        else "Revise a parte indicada da HQ e tente novamente."
    )
    hint = None
    if not correct and hints:
        hint = sorted(
            hints,
            key=lambda item: int(item.get("level", 1)),
        )[0]
    return {
        "message": templates.get(key, default),
        "hint": hint,
        "review_required": False,
        "source_reference": source_reference,
    }


async def upsert_profile(
    session: AsyncSession,
    *,
    actor: ActorContext,
    activity_id: uuid.UUID,
    data: Any,
) -> Any:
    from app.assessment_review.models import ReviewRubric, ReviewRubricVersion

    from . import models

    activity = await session.scalar(
        select(models.HQActivityBinding).where(
            models.HQActivityBinding.organization_id == actor.organization_id,
            models.HQActivityBinding.id == activity_id,
        )
    )
    if activity is None:
        raise HTTPException(404, "Atividade não encontrada.")

    profile = await session.scalar(
        select(models.HQActivityFeedbackProfile)
        .where(
            models.HQActivityFeedbackProfile.organization_id == actor.organization_id,
            models.HQActivityFeedbackProfile.activity_binding_id == activity_id,
        )
        .with_for_update()
    )
    if profile is None:
        profile = models.HQActivityFeedbackProfile(
            organization_id=actor.organization_id,
            activity_binding_id=activity_id,
            created_by_user_id=actor.user_id,
        )
        session.add(profile)

    profile.correction_mode = data.correction_mode
    profile.feedback_templates = data.feedback_templates
    profile.graduated_hints = data.graduated_hints
    profile.common_errors = data.common_errors
    profile.review_rules = data.review_rules
    profile.appeal_enabled = data.appeal_enabled
    profile.status = "DRAFT"

    if data.correction_mode in {"RUBRIC", "ASSISTED", "HUMAN"} and data.rubric:
        code = f"HQ-{str(activity_id)[:8]}-RUBRIC".upper()
        rubric = await session.scalar(
            select(ReviewRubric).where(
                ReviewRubric.organization_id == actor.organization_id,
                ReviewRubric.code == code,
            )
        )
        if rubric is None:
            rubric = ReviewRubric(
                organization_id=actor.organization_id,
                code=code,
                name=data.rubric.get("name", f"Rubrica — {activity.title}"),
                description=data.rubric.get(
                    "description",
                    "Rubrica vinculada à atividade pós-HQ.",
                ),
                scope_type="QUESTION",
                scope_id=activity.question_version_id,
                status="DRAFT",
                current_version=1,
                created_by_user_id=actor.user_id,
            )
            session.add(rubric)
            await session.flush()

        version = await session.scalar(
            select(ReviewRubricVersion).where(
                ReviewRubricVersion.organization_id == actor.organization_id,
                ReviewRubricVersion.rubric_id == rubric.id,
                ReviewRubricVersion.version == rubric.current_version,
            )
        )
        if version is None:
            criteria = data.rubric.get("criteria", [])
            maximum = float(
                data.rubric.get(
                    "maximum_score",
                    sum(float(item.get("maximum_score", 0)) for item in criteria),
                )
            )
            version = ReviewRubricVersion(
                organization_id=actor.organization_id,
                rubric_id=rubric.id,
                version=rubric.current_version,
                status="DRAFT",
                maximum_score=maximum,
                criteria=criteria,
                score_rules=data.rubric.get("score_rules", {}),
                feedback_templates=data.feedback_templates,
                skill_mappings=data.rubric.get("skill_mappings", []),
                accessibility_settings=data.rubric.get("accessibility", {}),
                configuration_hash="hq-activity-feedback",
                created_by_user_id=actor.user_id,
            )
            session.add(version)
            await session.flush()
        profile.rubric_id = rubric.id
        profile.rubric_version_id = version.id

    await session.flush()
    return profile


async def approve_profile(
    session: AsyncSession,
    *,
    actor: ActorContext,
    profile_id: uuid.UUID,
) -> Any:
    from app.assessment_hub.models import QuestionVersion
    from app.assessment_review.models import ReviewRubric, ReviewRubricVersion

    from . import models

    profile = await session.scalar(
        select(models.HQActivityFeedbackProfile)
        .where(
            models.HQActivityFeedbackProfile.organization_id == actor.organization_id,
            models.HQActivityFeedbackProfile.id == profile_id,
        )
        .with_for_update()
    )
    if profile is None:
        raise HTTPException(404, "Perfil de correção não encontrado.")
    profile.status = "APPROVED"
    profile.reviewed_by_user_id = actor.user_id
    profile.reviewed_at = datetime.now(UTC)

    if profile.rubric_id:
        rubric = await session.get(ReviewRubric, profile.rubric_id)
        if rubric:
            rubric.status = "PUBLISHED"
    if profile.rubric_version_id:
        version = await session.get(ReviewRubricVersion, profile.rubric_version_id)
        if version:
            version.status = "PUBLISHED"
            version.published_by_user_id = actor.user_id
            version.published_at = datetime.now(UTC)
    activity = await session.scalar(
        select(models.HQActivityBinding).where(
            models.HQActivityBinding.organization_id == actor.organization_id,
            models.HQActivityBinding.id == profile.activity_binding_id,
        )
    )
    if activity and activity.question_version_id:
        question_version = await session.scalar(
            select(QuestionVersion).where(
                QuestionVersion.organization_id == actor.organization_id,
                QuestionVersion.id == activity.question_version_id,
            )
        )
        if question_version:
            metadata = dict(question_version.metadata_payload)
            metadata["review_profile_id"] = str(profile.id)
            metadata["review_correction_mode"] = profile.correction_mode
            metadata["review_feedback_templates"] = profile.feedback_templates
            metadata["review_rubric_version_id"] = (
                str(profile.rubric_version_id)
                if profile.rubric_version_id
                else None
            )
            question_version.metadata_payload = metadata
    await session.flush()
    return profile
