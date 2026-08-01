from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_evolution.models import AccessibleResourceVersion
from app.comic_layout_studio.models import HQPreflightFinding
from app.comic_review_publish.models import (
    ComicEditorialRelease,
    ComicEditorialReleaseTarget,
)
from app.models.assessment import QuestionBankItem
from app.models.delivery import MaterialAssignment
from app.models.education import ClassroomEnrollment

from . import models
from .compat import ActorContext
from .policies import accessibility_summary

STAFF_ROLES = {
    "OWNER", "ADMIN", "ORG_ADMIN", "PLATFORM_ADMIN", "TEACHER",
    "COORDINATOR", "PEDAGOGICAL_COORDINATOR", "EDITOR",
}


def is_staff(actor: ActorContext) -> bool:
    return bool(set(actor.roles).intersection(STAFF_ROLES))


def _active_target(target: ComicEditorialReleaseTarget, now: datetime) -> bool:
    if target.status != "ACTIVE":
        return False
    if target.availability_from and target.availability_from > now:
        return False
    if target.availability_until and target.availability_until < now:
        return False
    return True


async def release_for_actor(
    session: AsyncSession,
    *,
    actor: ActorContext,
    release_id: uuid.UUID,
    allow_unpublished_for_staff: bool = False,
) -> ComicEditorialRelease:
    release = await session.scalar(
        select(ComicEditorialRelease).where(
            ComicEditorialRelease.organization_id == actor.organization_id,
            ComicEditorialRelease.id == release_id,
        )
    )
    if release is None:
        raise HTTPException(404, "Release da HQ nao encontrado.")

    if is_staff(actor):
        if allow_unpublished_for_staff or release.status in {"PUBLISHED", "READY", "SCHEDULED"}:
            return release
        raise HTTPException(409, "O release ainda nao esta pronto para leitura.")

    if release.status != "PUBLISHED":
        raise HTTPException(404, "Release da HQ nao encontrado.")

    targets = list(
        (
            await session.scalars(
                select(ComicEditorialReleaseTarget).where(
                    ComicEditorialReleaseTarget.organization_id == actor.organization_id,
                    ComicEditorialReleaseTarget.release_id == release.id,
                )
            )
        ).all()
    )
    active = [target for target in targets if _active_target(target, datetime.now(UTC))]

    if any(target.target_type in {"PUBLIC_CATALOG", "INSTITUTIONAL_LIBRARY"} for target in active):
        return release
    if any(target.target_type == "STUDENT" and target.target_id == actor.user_id for target in active):
        return release

    classroom_ids = {
        target.target_id
        for target in active
        if target.target_type == "CLASSROOM" and target.target_id
    }
    if classroom_ids:
        enrollment_id = await session.scalar(
            select(ClassroomEnrollment.id).where(
                ClassroomEnrollment.user_id == actor.user_id,
                ClassroomEnrollment.classroom_id.in_(classroom_ids),
            )
        )
        if enrollment_id:
            return release

    raise HTTPException(403, "Esta HQ nao foi publicada para o usuario atual.")


async def accessible_releases(
    session: AsyncSession,
    *,
    actor: ActorContext,
) -> list[ComicEditorialRelease]:
    releases = list(
        (
            await session.scalars(
                select(ComicEditorialRelease)
                .where(
                    ComicEditorialRelease.organization_id == actor.organization_id,
                    ComicEditorialRelease.status.in_(["PUBLISHED", "READY", "SCHEDULED"]),
                )
                .order_by(ComicEditorialRelease.updated_at.desc())
            )
        ).all()
    )
    if is_staff(actor):
        return releases

    allowed: list[ComicEditorialRelease] = []
    for release in releases:
        try:
            await release_for_actor(session, actor=actor, release_id=release.id)
        except HTTPException:
            continue
        allowed.append(release)
    return allowed


def snapshot_pages(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    data: Any = snapshot
    if isinstance(data, dict) and isinstance(data.get("comic"), dict):
        data = data["comic"]
    pages = data.get("pages") if isinstance(data, dict) else None
    return pages if isinstance(pages, list) else []


async def release_manifest(
    session: AsyncSession,
    *,
    actor: ActorContext,
    release: ComicEditorialRelease,
) -> dict[str, Any]:
    snapshot = dict(release.snapshot or {})
    pages = snapshot_pages(snapshot)

    narrations = list(
        (
            await session.scalars(
                select(models.ComicNarrationTrack)
                .where(
                    models.ComicNarrationTrack.organization_id == actor.organization_id,
                    models.ComicNarrationTrack.release_id == release.id,
                    models.ComicNarrationTrack.status == "READY",
                )
                .order_by(
                    models.ComicNarrationTrack.page_number,
                    models.ComicNarrationTrack.panel_number,
                )
            )
        ).all()
    )
    glossary = list(
        (
            await session.scalars(
                select(models.ComicGlossaryTerm)
                .where(
                    models.ComicGlossaryTerm.organization_id == actor.organization_id,
                    models.ComicGlossaryTerm.release_id == release.id,
                )
                .order_by(models.ComicGlossaryTerm.term)
            )
        ).all()
    )
    links = list(
        (
            await session.scalars(
                select(models.ComicEmbeddedAssessmentLink)
                .where(
                    models.ComicEmbeddedAssessmentLink.organization_id == actor.organization_id,
                    models.ComicEmbeddedAssessmentLink.release_id == release.id,
                )
                .order_by(
                    models.ComicEmbeddedAssessmentLink.page_number,
                    models.ComicEmbeddedAssessmentLink.display_order,
                )
            )
        ).all()
    )

    questions: dict[uuid.UUID, QuestionBankItem] = {}
    if links:
        values = list(
            (
                await session.scalars(
                    select(QuestionBankItem).where(
                        QuestionBankItem.organization_id == actor.organization_id,
                        QuestionBankItem.id.in_(
                            [link.question_bank_item_id for link in links]
                        ),
                    )
                )
            ).all()
        )
        questions = {item.id: item for item in values}

    assignment_ids = [link.assignment_id for link in links if link.assignment_id]
    assignments: dict[uuid.UUID, MaterialAssignment] = {}
    if assignment_ids:
        values = list(
            (
                await session.scalars(
                    select(MaterialAssignment).where(
                        MaterialAssignment.organization_id == actor.organization_id,
                        MaterialAssignment.id.in_(assignment_ids),
                    )
                )
            ).all()
        )
        assignments = {item.id: item for item in values}

    accessible_versions = list(
        (
            await session.scalars(
                select(AccessibleResourceVersion)
                .where(
                    AccessibleResourceVersion.organization_id == actor.organization_id,
                    AccessibleResourceVersion.source_resource_id.in_(
                        [release.id, release.comic_project_id]
                    ),
                    AccessibleResourceVersion.status == "PUBLISHED",
                )
                .order_by(AccessibleResourceVersion.version.desc())
            )
        ).all()
    )

    findings: list[HQPreflightFinding] = []
    raw_canvas_id = (release.metadata_json or {}).get("canvas_document_id")
    if raw_canvas_id:
        try:
            canvas_id = uuid.UUID(str(raw_canvas_id))
        except ValueError:
            canvas_id = None
        if canvas_id:
            findings = list(
                (
                    await session.scalars(
                        select(HQPreflightFinding).where(
                            HQPreflightFinding.organization_id == actor.organization_id,
                            HQPreflightFinding.document_id == canvas_id,
                            HQPreflightFinding.resolved.is_(False),
                        )
                    )
                ).all()
            )

    return {
        "release": {
            "id": str(release.id),
            "comic_project_id": str(release.comic_project_id),
            "release_number": release.release_number,
            "release_name": release.release_name,
            "release_notes": release.release_notes,
            "release_hash": release.release_hash,
            "status": release.status,
            "published_at": release.published_at,
        },
        "snapshot": snapshot,
        "pages": pages,
        "accessibility": {
            **accessibility_summary(pages),
            "accessible_versions": [
                {
                    "id": str(item.id),
                    "adaptation_type": item.adaptation_type,
                    "title": item.title,
                    "content": item.content,
                    "content_reference": item.content_reference,
                    "metadata": item.accessibility_metadata,
                }
                for item in accessible_versions
            ],
            "preflight_findings": [
                {
                    "id": str(item.id),
                    "severity": item.severity,
                    "code": item.code,
                    "message": item.message,
                    "resource_type": item.resource_type,
                    "resource_id": str(item.resource_id) if item.resource_id else None,
                }
                for item in findings
            ],
        },
        "narrations": [
            {
                "id": str(item.id),
                "page_number": item.page_number,
                "panel_number": item.panel_number,
                "source_type": item.source_type,
                "language": item.language,
                "transcript": item.transcript,
                "audio_url": item.audio_url,
                "duration_ms": item.duration_ms,
                "voice_settings": item.voice_settings,
            }
            for item in narrations
        ],
        "glossary": [
            {
                "id": str(item.id),
                "term": item.term,
                "definition": item.definition,
                "simplified_definition": item.simplified_definition,
                "page_number": item.page_number,
                "panel_number": item.panel_number,
                "pronunciation": item.pronunciation,
                "metadata": item.metadata_json,
            }
            for item in glossary
        ],
        "assessment_links": [
            {
                "id": str(link.id),
                "question_bank_item_id": str(link.question_bank_item_id),
                "assignment_id": str(link.assignment_id) if link.assignment_id else None,
                "assignment_title": (
                    assignments[link.assignment_id].title
                    if link.assignment_id in assignments
                    else None
                ),
                "page_number": link.page_number,
                "panel_number": link.panel_number,
                "display_order": link.display_order,
                "required": link.required,
                "reveal_rule": link.reveal_rule,
                "question": (
                    {
                        "title": questions[link.question_bank_item_id].title,
                        "item_type": questions[link.question_bank_item_id].item_type,
                        "prompt": questions[link.question_bank_item_id].prompt,
                        "options": questions[link.question_bank_item_id].options,
                        "points": questions[link.question_bank_item_id].points,
                        "difficulty": questions[link.question_bank_item_id].difficulty,
                        "curriculum_skill_codes": questions[
                            link.question_bank_item_id
                        ].curriculum_skill_codes,
                        "ct_pillar_codes": questions[
                            link.question_bank_item_id
                        ].ct_pillar_codes,
                    }
                    if link.question_bank_item_id in questions
                    else None
                ),
            }
            for link in links
        ],
    }
