from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assessment import (
    Assessment,
    AssessmentAuditEvent,
    AssessmentDeliveryLink,
    AssessmentImportJob,
    AssessmentOutcomeEvidence,
    AssessmentSourceType,
    AssessmentStatus,
    AssessmentVersion,
    AssessmentVersionItem,
    ImportJobStatus,
    QuestionBankItem,
    QuestionBankStatus,
)
from app.models.delivery import (
    AnswerKeyPolicy,
    AssignmentQuestion,
    AssignmentRecipient,
    AssignmentStatus,
    AssignmentType,
    AttemptStatus,
    FeedbackPolicy,
    MaterialAssignment,
    QuestionType,
    RecipientType,
    StudentAnswer,
    StudentAttempt,
)
from app.models.statistics import DatasetStatus, StatisticalDataset, StatisticalStudy
from app.schemas.assessment import (
    AiQuestionGenerationRequest,
    AssessmentCreate,
    AssessmentPublishRequest,
    BankItemCreate,
    ImportExecuteRequest,
    ImportJobCreate,
    StatisticalDatasetFromAssessments,
)
from app.services.delivery import _recalculate_attempt, _validate_recipient, publish_assignment


class AssessmentError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def checksum(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bank_item_snapshot(item: QuestionBankItem) -> dict[str, Any]:
    return {
        "bank_item_id": str(item.id),
        "version_number": item.version_number,
        "item_type": item.item_type,
        "prompt": item.prompt,
        "options": item.options,
        "answer_key": item.answer_key,
        "explanation": item.explanation,
        "points": item.points,
        "difficulty": item.difficulty,
        "curriculum_skill_codes": item.curriculum_skill_codes,
        "ct_pillar_codes": item.ct_pillar_codes,
        "source_type": item.source_type,
        "source_metadata": item.source_metadata,
        "ai_generation_metadata": item.ai_generation_metadata,
        "requires_manual_grading": item.requires_manual_grading,
        "content_checksum": item.content_checksum,
    }


async def audit(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    action: str,
    assessment_id: UUID | None = None,
    assessment_version_id: UUID | None = None,
    assignment_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AssessmentAuditEvent(
            organization_id=organization_id,
            assessment_id=assessment_id,
            assessment_version_id=assessment_version_id,
            assignment_id=assignment_id,
            action=action,
            details=details or {},
            performed_by_user_id=user_id,
        )
    )


async def create_bank_item(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    data: BankItemCreate,
    status: str = QuestionBankStatus.DRAFT.value,
) -> QuestionBankItem:
    payload = data.model_dump(mode="json")
    item = QuestionBankItem(
        organization_id=organization_id,
        title=data.title.strip(),
        item_type=data.item_type.value,
        prompt=data.prompt.strip(),
        options=data.options,
        answer_key=data.answer_key,
        explanation=data.explanation.strip(),
        points=data.points,
        difficulty=data.difficulty,
        curriculum_skill_codes=data.curriculum_skill_codes,
        ct_pillar_codes=data.ct_pillar_codes,
        source_type=data.source_type.value,
        source_metadata=data.source_metadata,
        ai_generation_metadata=data.ai_generation_metadata,
        requires_manual_grading=data.requires_manual_grading or data.item_type == QuestionType.ESSAY,
        status=status,
        content_checksum=checksum(payload),
        external_reference=data.external_reference,
        created_by_user_id=user_id,
    )
    session.add(item)
    await session.flush()
    return item


async def get_assessment(
    session: AsyncSession, organization_id: UUID, assessment_id: UUID
) -> Assessment | None:
    return await session.scalar(
        select(Assessment)
        .where(Assessment.id == assessment_id, Assessment.organization_id == organization_id)
        .options(
            selectinload(Assessment.versions)
            .selectinload(AssessmentVersion.items)
            .selectinload(AssessmentVersionItem.bank_item)
        )
    )


async def get_version(
    session: AsyncSession, organization_id: UUID, version_id: UUID
) -> AssessmentVersion | None:
    return await session.scalar(
        select(AssessmentVersion)
        .where(
            AssessmentVersion.id == version_id,
            AssessmentVersion.organization_id == organization_id,
        )
        .options(
            selectinload(AssessmentVersion.items).selectinload(AssessmentVersionItem.bank_item),
            selectinload(AssessmentVersion.assessment),
        )
    )


async def _attach_items(
    session: AsyncSession,
    *,
    version: AssessmentVersion,
    organization_id: UUID,
    item_ids: Iterable[UUID],
) -> None:
    ids = list(dict.fromkeys(item_ids))
    if not ids:
        return
    result = await session.scalars(
        select(QuestionBankItem).where(
            QuestionBankItem.organization_id == organization_id,
            QuestionBankItem.id.in_(ids),
        )
    )
    by_id = {item.id: item for item in result.all()}
    missing = [str(item_id) for item_id in ids if item_id not in by_id]
    if missing:
        raise AssessmentError(f"Questões não encontradas: {', '.join(missing)}")
    start = len(version.items) + 1
    for offset, item_id in enumerate(ids):
        item = by_id[item_id]
        snapshot = bank_item_snapshot(item)
        version.items.append(
            AssessmentVersionItem(
                question_bank_item_id=item.id,
                position=start + offset,
                points_override=None,
                item_snapshot=snapshot,
                snapshot_checksum=checksum(snapshot),
            )
        )


async def refresh_version_checksum(version: AssessmentVersion) -> None:
    payload = {
        "version_number": version.version_number,
        "instructions": version.instructions,
        "scoring_policy": version.scoring_policy,
        "delivery_defaults": version.delivery_defaults,
        "source_metadata": version.source_metadata,
        "items": [
            {
                "position": item.position,
                "snapshot_checksum": item.snapshot_checksum,
                "points_override": item.points_override,
            }
            for item in sorted(version.items, key=lambda row: row.position)
        ],
    }
    version.content_checksum = checksum(payload)


async def create_assessment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    data: AssessmentCreate,
) -> Assessment:
    assessment = Assessment(
        organization_id=organization_id,
        title=data.title.strip(),
        description=data.description.strip(),
        assessment_type=data.assessment_type.value,
        source_type=data.source_type.value,
        status=AssessmentStatus.DRAFT.value,
        created_by_user_id=user_id,
    )
    session.add(assessment)
    await session.flush()
    version = AssessmentVersion(
        assessment_id=assessment.id,
        organization_id=organization_id,
        version_number=1,
        instructions=data.instructions.strip(),
        scoring_policy=data.scoring_policy,
        delivery_defaults=data.delivery_defaults,
        source_metadata=data.source_metadata,
        created_by_user_id=user_id,
    )
    assessment.versions.append(version)
    await session.flush()
    await _attach_items(
        session,
        version=version,
        organization_id=organization_id,
        item_ids=data.item_ids,
    )
    await refresh_version_checksum(version)
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="assessment_created",
        assessment_id=assessment.id,
        assessment_version_id=version.id,
        details={"source_type": assessment.source_type, "item_count": len(version.items)},
    )
    await session.flush()
    return await get_assessment(session, organization_id, assessment.id) or assessment


async def add_item_to_assessment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    assessment_id: UUID,
    item_id: UUID,
    position: int | None,
    points_override: float | None,
) -> Assessment:
    assessment = await get_assessment(session, organization_id, assessment_id)
    if assessment is None:
        raise AssessmentError("Avaliação não encontrada")
    version = next(
        (version for version in assessment.versions if version.version_number == assessment.current_version_number),
        None,
    )
    if version is None or version.is_locked:
        raise AssessmentError("A versão atual está bloqueada; crie uma nova versão")
    item = await session.scalar(
        select(QuestionBankItem).where(
            QuestionBankItem.id == item_id,
            QuestionBankItem.organization_id == organization_id,
        )
    )
    if item is None:
        raise AssessmentError("Questão não encontrada")
    desired = position or len(version.items) + 1
    for existing in version.items:
        if existing.position >= desired:
            existing.position += 1
    snapshot = bank_item_snapshot(item)
    version.items.append(
        AssessmentVersionItem(
            question_bank_item_id=item.id,
            position=desired,
            points_override=points_override,
            item_snapshot=snapshot,
            snapshot_checksum=checksum(snapshot),
        )
    )
    await refresh_version_checksum(version)
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="assessment_item_added",
        assessment_id=assessment.id,
        assessment_version_id=version.id,
        details={"item_id": str(item.id), "position": desired},
    )
    await session.flush()
    return await get_assessment(session, organization_id, assessment.id) or assessment


async def create_version(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    assessment_id: UUID,
) -> Assessment:
    assessment = await get_assessment(session, organization_id, assessment_id)
    if assessment is None:
        raise AssessmentError("Avaliação não encontrada")
    current = next(
        (version for version in assessment.versions if version.version_number == assessment.current_version_number),
        None,
    )
    if current is None:
        raise AssessmentError("Versão atual não encontrada")
    next_number = max(version.version_number for version in assessment.versions) + 1
    version = AssessmentVersion(
        assessment_id=assessment.id,
        organization_id=organization_id,
        version_number=next_number,
        instructions=current.instructions,
        scoring_policy=current.scoring_policy,
        delivery_defaults=current.delivery_defaults,
        source_metadata={**current.source_metadata, "derived_from_version": current.version_number},
        created_by_user_id=user_id,
    )
    assessment.versions.append(version)
    await session.flush()
    for existing in current.items:
        version.items.append(
            AssessmentVersionItem(
                question_bank_item_id=existing.question_bank_item_id,
                position=existing.position,
                points_override=existing.points_override,
                item_snapshot=existing.item_snapshot,
                snapshot_checksum=existing.snapshot_checksum,
            )
        )
    assessment.current_version_number = next_number
    assessment.status = AssessmentStatus.DRAFT.value
    await refresh_version_checksum(version)
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="assessment_version_created",
        assessment_id=assessment.id,
        assessment_version_id=version.id,
        details={"version_number": next_number, "derived_from": current.version_number},
    )
    await session.flush()
    return await get_assessment(session, organization_id, assessment.id) or assessment


def _mock_question_payloads(data: AiQuestionGenerationRequest) -> list[BankItemCreate]:
    pillars = data.ct_pillar_codes or ["abstraction", "decomposition", "patterns", "algorithms"]
    skills = data.curriculum_skill_codes
    templates = [
        (QuestionType.MULTIPLE_CHOICE, "Qual alternativa melhor explica {topic}?"),
        (QuestionType.TRUE_FALSE, "Julgue a afirmação sobre {topic}: a solução pode ser verificada por evidências."),
        (QuestionType.SHORT_TEXT, "Descreva uma etapa essencial para resolver um problema envolvendo {topic}."),
        (QuestionType.MULTIPLE_SELECT, "Selecione ações adequadas para investigar {topic}."),
        (QuestionType.ESSAY, "Explique como você aplicaria pensamento computacional ao tema {topic}."),
    ]
    rows: list[BankItemCreate] = []
    for index in range(data.quantity):
        question_type, template = templates[index % len(templates)]
        options: list[dict[str, Any]] = []
        answer_key: dict[str, Any] = {}
        manual = question_type == QuestionType.ESSAY
        if question_type == QuestionType.MULTIPLE_CHOICE:
            options = [
                {"id": "A", "text": "Organizar evidências e testar uma solução"},
                {"id": "B", "text": "Ignorar os dados disponíveis"},
                {"id": "C", "text": "Escolher uma resposta sem verificar"},
                {"id": "D", "text": "Evitar decompor o problema"},
            ]
            answer_key = {"correct_option_ids": ["A"]}
        elif question_type == QuestionType.TRUE_FALSE:
            answer_key = {"value": True}
        elif question_type == QuestionType.SHORT_TEXT:
            answer_key = {"accepted_answers": ["decompor", "analisar", "testar", "verificar"]}
        elif question_type == QuestionType.MULTIPLE_SELECT:
            options = [
                {"id": "A", "text": "Observar padrões"},
                {"id": "B", "text": "Dividir o problema"},
                {"id": "C", "text": "Descartar evidências"},
                {"id": "D", "text": "Construir um algoritmo"},
            ]
            answer_key = {"correct_option_ids": ["A", "B", "D"]}
        rows.append(
            BankItemCreate(
                title=f"{data.topic} — questão {index + 1}",
                item_type=question_type,
                prompt=template.format(topic=data.topic),
                options=options,
                answer_key=answer_key,
                explanation="Questão gerada em modo IA mock e sujeita à revisão do professor.",
                points=1.0,
                difficulty=data.difficulty,
                curriculum_skill_codes=skills,
                ct_pillar_codes=[pillars[index % len(pillars)]],
                source_type=AssessmentSourceType.AI,
                source_metadata={"topic": data.topic, "source_context": data.source_context},
                ai_generation_metadata={
                    "provider": "mock",
                    "model": "educode-assessment-mock-v1",
                    "generated_at": utcnow().isoformat(),
                    "review_required": True,
                },
                requires_manual_grading=manual,
            )
        )
    return rows


async def generate_ai_items(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    data: AiQuestionGenerationRequest,
) -> list[QuestionBankItem]:
    assessment = await get_assessment(session, organization_id, data.assessment_id)
    if assessment is None:
        raise AssessmentError("Avaliação não encontrada")
    created: list[QuestionBankItem] = []
    for payload in _mock_question_payloads(data):
        created.append(
            await create_bank_item(
                session,
                organization_id=organization_id,
                user_id=user_id,
                data=payload,
            )
        )
    version = next(
        (version for version in assessment.versions if version.version_number == assessment.current_version_number),
        None,
    )
    if version is None or version.is_locked:
        raise AssessmentError("A versão atual não aceita novas questões")
    await _attach_items(
        session,
        version=version,
        organization_id=organization_id,
        item_ids=[item.id for item in created],
    )
    await refresh_version_checksum(version)
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="ai_items_generated",
        assessment_id=assessment.id,
        assessment_version_id=version.id,
        details={"quantity": len(created), "provider": "mock", "topic": data.topic},
    )
    await session.flush()
    return created


async def review_assessment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    assessment_id: UUID,
    decision: str,
    notes: str,
) -> Assessment:
    assessment = await get_assessment(session, organization_id, assessment_id)
    if assessment is None:
        raise AssessmentError("Avaliação não encontrada")
    version = next(
        (version for version in assessment.versions if version.version_number == assessment.current_version_number),
        None,
    )
    if version is None:
        raise AssessmentError("Versão atual não encontrada")
    if decision == "submit":
        if not version.items:
            raise AssessmentError("Adicione ao menos uma questão antes da revisão")
        assessment.status = AssessmentStatus.IN_REVIEW.value
        assessment.reviewed_by_user_id = user_id
    elif decision == "approve":
        if assessment.status not in {AssessmentStatus.IN_REVIEW.value, AssessmentStatus.DRAFT.value}:
            raise AssessmentError("A avaliação não está disponível para aprovação")
        assessment.status = AssessmentStatus.APPROVED.value
        assessment.approved_by_user_id = user_id
        version.is_locked = True
    elif decision == "return":
        assessment.status = AssessmentStatus.DRAFT.value
        version.is_locked = False
    elif decision == "archive":
        assessment.status = AssessmentStatus.ARCHIVED.value
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action=f"assessment_{decision}",
        assessment_id=assessment.id,
        assessment_version_id=version.id,
        details={"notes": notes},
    )
    await session.flush()
    return await get_assessment(session, organization_id, assessment.id) or assessment


async def publish_assessment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    user_name: str,
    assessment_id: UUID,
    data: AssessmentPublishRequest,
) -> MaterialAssignment:
    assessment = await get_assessment(session, organization_id, assessment_id)
    version = await get_version(session, organization_id, data.version_id)
    if assessment is None or version is None or version.assessment_id != assessment.id:
        raise AssessmentError("Avaliação ou versão não encontrada")
    if assessment.status not in {AssessmentStatus.APPROVED.value, AssessmentStatus.PUBLISHED.value}:
        raise AssessmentError("A avaliação deve ser aprovada antes da publicação")
    if not version.items:
        raise AssessmentError("A avaliação não possui questões")
    if data.due_at and data.available_from and data.due_at <= data.available_from:
        raise AssessmentError("O prazo deve ser posterior à liberação")
    for recipient in data.recipients:
        from app.schemas.delivery import RecipientInput

        await _validate_recipient(
            session,
            organization_id,
            RecipientInput(
                recipient_type=recipient.recipient_type,
                classroom_id=recipient.classroom_id,
                user_id=recipient.user_id,
                accommodations=recipient.accommodations,
            ),
        )
    material_snapshot = {
        "source": "integrated_assessment",
        "assessment_id": str(assessment.id),
        "assessment_version_id": str(version.id),
        "version_number": version.version_number,
        "content_checksum": version.content_checksum,
        "title": assessment.title,
        "instructions": version.instructions,
        "item_count": len(version.items),
    }
    assignment = MaterialAssignment(
        organization_id=organization_id,
        package_id=None,
        assessment_version_id=version.id,
        created_by_user_id=user_id,
        created_by_name_snapshot=user_name,
        title=(data.title_override or assessment.title).strip(),
        instructions=version.instructions,
        assignment_type=AssignmentType(assessment.assessment_type),
        status=AssignmentStatus.DRAFT,
        material_snapshot=material_snapshot,
        available_from=data.available_from,
        due_at=data.due_at,
        time_limit_minutes=data.time_limit_minutes,
        maximum_attempts=data.maximum_attempts,
        maximum_score=data.maximum_score,
        feedback_policy=FeedbackPolicy(data.feedback_policy),
        answer_key_policy=AnswerKeyPolicy(data.answer_key_policy),
        randomize_questions=data.randomize_questions,
        randomize_options=data.randomize_options,
        settings={"assessment_source": assessment.source_type, "assessment_checksum": version.content_checksum},
    )
    session.add(assignment)
    await session.flush()
    for recipient in data.recipients:
        assignment.recipients.append(
            AssignmentRecipient(
                recipient_type=recipient.recipient_type,
                classroom_id=recipient.classroom_id,
                user_id=recipient.user_id,
                accommodations=recipient.accommodations,
            )
        )
    for version_item in sorted(version.items, key=lambda row: row.position):
        snap = version_item.item_snapshot
        assignment.questions.append(
            AssignmentQuestion(
                question_bank_item_id=version_item.question_bank_item_id,
                position=version_item.position,
                question_type=QuestionType(snap["item_type"]),
                prompt=snap["prompt"],
                options=snap.get("options", []),
                answer_key=snap.get("answer_key", {}),
                explanation=snap.get("explanation", ""),
                points=version_item.points_override or float(snap.get("points", 1.0)),
                difficulty=snap.get("difficulty", "medium"),
                curriculum_skill_codes=snap.get("curriculum_skill_codes", []),
                ct_pillar_codes=snap.get("ct_pillar_codes", []),
                source_references=[{"assessment_version_id": str(version.id), "question_bank_item_id": str(version_item.question_bank_item_id)}],
                manual_grading=bool(snap.get("requires_manual_grading", False)),
                source_type=snap.get("source_type", AssessmentSourceType.TEACHER.value),
                source_metadata={
                    **snap.get("source_metadata", {}),
                    "ai_generation_metadata": snap.get("ai_generation_metadata", {}),
                },
                item_version=int(snap.get("version_number", 1)),
                item_snapshot_checksum=version_item.snapshot_checksum,
            )
        )
    session.add(
        AssessmentDeliveryLink(
            organization_id=organization_id,
            assessment_id=assessment.id,
            assessment_version_id=version.id,
            material_assignment_id=assignment.id,
            created_by_user_id=user_id,
        )
    )
    await publish_assignment(session, assignment)
    assessment.status = AssessmentStatus.PUBLISHED.value
    version.is_locked = True
    version.published_at = version.published_at or utcnow()
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="assessment_published",
        assessment_id=assessment.id,
        assessment_version_id=version.id,
        assignment_id=assignment.id,
        details={"recipient_count": len(data.recipients), "question_count": len(version.items)},
    )
    await session.flush()
    return assignment


async def recalculate_attempt_evidence(
    session: AsyncSession,
    *,
    attempt: StudentAttempt,
    calculation_version: int | None = None,
) -> list[AssessmentOutcomeEvidence]:
    await session.execute(delete(AssessmentOutcomeEvidence).where(AssessmentOutcomeEvidence.attempt_id == attempt.id))
    generated: list[AssessmentOutcomeEvidence] = []
    answer_by_question = {answer.question_id: answer for answer in attempt.answers}
    version_number = calculation_version or attempt.grading_revision
    for question in attempt.assignment.questions:
        if question.is_annulled:
            continue
        answer = answer_by_question.get(question.id)
        if answer is None:
            continue
        dimensions = [("bncc", code) for code in question.curriculum_skill_codes]
        dimensions.extend(("ct_pillar", code) for code in question.ct_pillar_codes)
        if not dimensions:
            dimensions.append(("assessment", "overall"))
        evidence_weight = 1.0 / len(dimensions)
        for dimension_type, dimension_code in dimensions:
            evidence = AssessmentOutcomeEvidence(
                organization_id=attempt.organization_id,
                assessment_version_id=attempt.assessment_version_id or attempt.assignment.assessment_version_id,
                assignment_id=attempt.assignment_id,
                attempt_id=attempt.id,
                answer_id=answer.id,
                question_id=question.id,
                student_id=attempt.student_id,
                dimension_type=dimension_type,
                dimension_code=dimension_code,
                score_obtained=answer.awarded_score,
                score_possible=question.points,
                evidence_weight=evidence_weight,
                calculation_version=version_number,
                source_snapshot={
                    "question_checksum": question.item_snapshot_checksum,
                    "source_type": question.source_type,
                    "is_correct": answer.is_correct,
                    "response_time_seconds": answer.response_time_seconds,
                    "attempt_number": attempt.attempt_number,
                },
            )
            session.add(evidence)
            generated.append(evidence)
    attempt.recalculated_at = utcnow()
    await session.flush()
    return generated


async def recalculate_assignment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    assignment_id: UUID,
) -> int:
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt)
                .where(
                    StudentAttempt.organization_id == organization_id,
                    StudentAttempt.assignment_id == assignment_id,
                    StudentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.GRADED]),
                )
                .options(
                    selectinload(StudentAttempt.answers),
                    selectinload(StudentAttempt.assignment).selectinload(MaterialAssignment.questions),
                )
            )
        ).all()
    )
    for attempt in attempts:
        _recalculate_attempt(attempt)
        attempt.grading_revision += 1
        await recalculate_attempt_evidence(session, attempt=attempt)
    await session.flush()
    return len(attempts)


async def annul_question(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    question_id: UUID,
    is_annulled: bool,
    reason: str,
    regrade_attempts: bool,
) -> AssignmentQuestion:
    question = await session.scalar(
        select(AssignmentQuestion)
        .join(MaterialAssignment, MaterialAssignment.id == AssignmentQuestion.assignment_id)
        .where(
            AssignmentQuestion.id == question_id,
            MaterialAssignment.organization_id == organization_id,
        )
    )
    if question is None:
        raise AssessmentError("Questão não encontrada")
    question.is_annulled = is_annulled
    question.annulment_reason = reason if is_annulled else None
    count = 0
    if regrade_attempts:
        count = await recalculate_assignment(
            session,
            organization_id=organization_id,
            assignment_id=question.assignment_id,
        )
    link = await session.scalar(
        select(AssessmentDeliveryLink).where(
            AssessmentDeliveryLink.material_assignment_id == question.assignment_id,
            AssessmentDeliveryLink.organization_id == organization_id,
        )
    )
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="question_annulled" if is_annulled else "question_restored",
        assessment_id=link.assessment_id if link else None,
        assessment_version_id=link.assessment_version_id if link else None,
        assignment_id=question.assignment_id,
        details={"question_id": str(question.id), "reason": reason, "regraded_attempts": count},
    )
    await session.flush()
    return question


async def create_import_job(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    data: ImportJobCreate,
) -> AssessmentImportJob:
    required = {"prompt", "item_type"}
    invalid_rows = [index + 1 for index, row in enumerate(data.rows) if not required.issubset(row)]
    status = ImportJobStatus.NEEDS_MAPPING.value if invalid_rows else ImportJobStatus.READY.value
    job = AssessmentImportJob(
        organization_id=organization_id,
        source_format=data.source_format,
        file_name=data.file_name,
        status=status,
        field_mapping=data.field_mapping,
        rows_snapshot=data.rows,
        validation_summary={
            "row_count": len(data.rows),
            "invalid_rows": invalid_rows,
            "supported_formats": ["csv", "xlsx", "json", "qti", "lti", "xapi", "scorm"],
        },
        created_by_user_id=user_id,
    )
    session.add(job)
    await session.flush()
    return job


def _row_to_bank_item(row: dict[str, Any]) -> BankItemCreate:
    try:
        item_type = QuestionType(str(row.get("item_type", "multiple_choice")))
    except ValueError as exc:
        raise AssessmentError(f"Tipo de questão inválido: {row.get('item_type')}") from exc
    return BankItemCreate(
        title=str(row.get("title", "")),
        item_type=item_type,
        prompt=str(row.get("prompt", "")).strip(),
        options=list(row.get("options") or []),
        answer_key=dict(row.get("answer_key") or {}),
        explanation=str(row.get("explanation", "")),
        points=float(row.get("points", 1.0)),
        difficulty=str(row.get("difficulty", "medium")),
        curriculum_skill_codes=list(row.get("curriculum_skill_codes") or []),
        ct_pillar_codes=list(row.get("ct_pillar_codes") or []),
        source_type=AssessmentSourceType.IMPORTED,
        source_metadata={"import_row": row, "external_system": row.get("external_system")},
        requires_manual_grading=bool(row.get("requires_manual_grading", item_type == QuestionType.ESSAY)),
        external_reference=str(row["external_reference"]) if row.get("external_reference") else None,
    )


async def execute_import(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    job: AssessmentImportJob,
    data: ImportExecuteRequest,
) -> Assessment:
    if job.organization_id != organization_id:
        raise AssessmentError("Importação não encontrada")
    if job.status != ImportJobStatus.READY.value:
        raise AssessmentError("A importação precisa estar validada e mapeada")
    items: list[QuestionBankItem] = []
    for row in job.rows_snapshot:
        payload = _row_to_bank_item(row)
        items.append(
            await create_bank_item(
                session,
                organization_id=organization_id,
                user_id=user_id,
                data=payload,
                status=QuestionBankStatus.IN_REVIEW.value,
            )
        )
    assessment = await create_assessment(
        session,
        organization_id=organization_id,
        user_id=user_id,
        data=AssessmentCreate(
            title=data.title,
            description=data.description,
            assessment_type=data.assessment_type,
            source_type=AssessmentSourceType.IMPORTED,
            source_metadata={"import_job_id": str(job.id), "source_format": job.source_format},
            item_ids=[item.id for item in items],
        ),
    )
    job.status = ImportJobStatus.IMPORTED.value
    job.imported_assessment_id = assessment.id
    job.completed_at = utcnow()
    await audit(
        session,
        organization_id=organization_id,
        user_id=user_id,
        action="assessment_imported",
        assessment_id=assessment.id,
        details={"job_id": str(job.id), "source_format": job.source_format, "item_count": len(items)},
    )
    await session.flush()
    return assessment


def select_attempts(attempts: Iterable[StudentAttempt], policy: str) -> list[StudentAttempt]:
    grouped: dict[tuple[UUID, UUID], list[StudentAttempt]] = defaultdict(list)
    for attempt in attempts:
        grouped[(attempt.student_id, attempt.assignment_id)].append(attempt)
    selected: list[StudentAttempt] = []
    for values in grouped.values():
        if policy == "first":
            selected.append(min(values, key=lambda row: row.attempt_number))
        elif policy == "latest":
            selected.append(max(values, key=lambda row: row.attempt_number))
        elif policy == "best":
            selected.append(max(values, key=lambda row: row.percentage))
        else:
            selected.extend(values)
    return selected


async def freeze_assessment_dataset(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    data: StatisticalDatasetFromAssessments,
) -> StatisticalDataset:
    study = await session.scalar(
        select(StatisticalStudy).where(
            StatisticalStudy.id == data.study_id,
            StatisticalStudy.organization_id == organization_id,
        )
    )
    if study is None:
        raise AssessmentError("Estudo estatístico não encontrado")
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt)
                .join(MaterialAssignment, MaterialAssignment.id == StudentAttempt.assignment_id)
                .where(
                    StudentAttempt.organization_id == organization_id,
                    MaterialAssignment.assessment_version_id.in_(data.assessment_version_ids),
                    StudentAttempt.status.in_([AttemptStatus.SUBMITTED, AttemptStatus.GRADED]),
                )
                .options(
                    selectinload(StudentAttempt.assignment),
                    selectinload(StudentAttempt.answers).selectinload(StudentAnswer.question),
                )
            )
        ).all()
    )
    chosen = select_attempts(attempts, data.attempt_policy)
    anonymous: dict[UUID, str] = {}
    rows: list[dict[str, Any]] = []
    for attempt in chosen:
        anonymous.setdefault(attempt.student_id, f"EST-{len(anonymous) + 1:04d}")
        student_key = anonymous[attempt.student_id] if data.anonymized else str(attempt.student_id)
        base = {
            "student_id": student_key,
            "assessment_version_id": str(attempt.assignment.assessment_version_id),
            "assignment_id": str(attempt.assignment_id),
            "attempt_id": str(attempt.id),
            "attempt_number": attempt.attempt_number,
            "score": attempt.score,
            "percentage": attempt.percentage,
            "time_spent_seconds": attempt.time_spent_seconds,
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        }
        if not data.include_item_level:
            rows.append(base)
            continue
        for answer in attempt.answers:
            question = answer.question
            rows.append(
                {
                    **base,
                    "question_id": str(question.id),
                    "question_bank_item_id": str(question.question_bank_item_id) if question.question_bank_item_id else None,
                    "question_type": question.question_type.value,
                    "is_correct": answer.is_correct,
                    "awarded_score": answer.awarded_score,
                    "possible_score": question.points,
                    "response_time_seconds": answer.response_time_seconds,
                    "bncc_codes": question.curriculum_skill_codes,
                    "ct_pillar_codes": question.ct_pillar_codes,
                    "source_type": question.source_type,
                    "question_checksum": question.item_snapshot_checksum,
                }
            )
    payload = canonical_json(rows).encode("utf-8")
    variable_dictionary = [
        {"name": "student_id", "type": "identifier", "description": "Código anonimizado do estudante"},
        {"name": "assessment_version_id", "type": "identifier", "description": "Versão imutável da avaliação"},
        {"name": "percentage", "type": "numeric", "description": "Percentual final da tentativa"},
        {"name": "is_correct", "type": "boolean", "description": "Acerto no exercício"},
        {"name": "bncc_codes", "type": "list", "description": "Habilidades BNCC vinculadas"},
        {"name": "ct_pillar_codes", "type": "list", "description": "Pilares de Pensamento Computacional"},
    ]
    dataset = StatisticalDataset(
        study_id=study.id,
        organization_id=organization_id,
        title=data.title,
        status=DatasetStatus.FROZEN,
        filters={"assessment_version_ids": [str(item) for item in data.assessment_version_ids]},
        attempt_policy=data.attempt_policy,
        participant_count=len({row["student_id"] for row in rows}),
        row_count=len(rows),
        dataset_checksum=hashlib.sha256(payload).hexdigest(),
        quality_summary={
            "source": "integrated_assessment_core",
            "attempt_count": len(chosen),
            "item_level": data.include_item_level,
            "missing_values": sum(1 for row in rows for value in row.values() if value is None),
        },
        variable_dictionary=variable_dictionary,
        rows_snapshot=rows,
        anonymized=data.anonymized,
        created_by_user_id=user_id,
    )
    session.add(dataset)
    await session.flush()
    return dataset
