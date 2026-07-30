from __future__ import annotations

import json
import math
import random
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import Membership, User
from app.models.comic import ComicPage, ComicPanel, GeneratedComic
from app.models.delivery import (
    AnswerKeyPolicy,
    AssignmentQuestion,
    AssignmentRecipient,
    AssignmentStatus,
    AssignmentType,
    AttemptStatus,
    FeedbackPolicy,
    LearningEvent,
    MaterialAssignment,
    QuestionType,
    RecipientStatus,
    RecipientType,
    StudentAnswer,
    StudentAttempt,
    UserNotification,
)
from app.models.education import Classroom, ClassroomEnrollment
from app.models.studio import PedagogicalPackage, StudioMaterialType
from app.schemas.delivery import (
    AssignmentCreate,
    AssignmentProgress,
    GradingQueueItem,
    QuestionInput,
    QuestionProgressRow,
    RecipientInput,
    StudentProgressRow,
)


class DeliveryError(ValueError):
    """Expected delivery-domain failure safe to expose as a 4xx response."""


@dataclass(frozen=True)
class GradeOutcome:
    is_correct: bool | None
    awarded_score: float
    feedback: str | None


def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _numeric(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def grade_response(
    question_type: QuestionType,
    answer_payload: dict[str, Any],
    answer_key: dict[str, Any],
    points: float,
) -> GradeOutcome:
    """Deterministic objective grading. Essay/manual items return an ungraded outcome."""
    if question_type == QuestionType.ESSAY:
        return GradeOutcome(None, 0.0, None)

    correct = False
    if question_type == QuestionType.MULTIPLE_CHOICE:
        selected = answer_payload.get("selected_option_id")
        valid = answer_key.get("correct_option_ids", [])
        correct = selected is not None and str(selected) in {str(item) for item in valid}
    elif question_type == QuestionType.TRUE_FALSE:
        correct = answer_payload.get("value") is answer_key.get("value")
    elif question_type == QuestionType.SHORT_TEXT:
        response = normalize_text(answer_payload.get("text"))
        accepted = {normalize_text(item) for item in answer_key.get("accepted_answers", [])}
        correct = bool(response) and response in accepted
    elif question_type == QuestionType.NUMERIC:
        response = _numeric(answer_payload.get("value"))
        expected = _numeric(answer_key.get("value"))
        tolerance = abs(_numeric(answer_key.get("tolerance")) or 0.0)
        correct = (
            response is not None
            and expected is not None
            and abs(response - expected) <= tolerance
        )
    elif question_type == QuestionType.MULTIPLE_SELECT:
        selected = {str(item) for item in answer_payload.get("selected_option_ids", [])}
        expected_set = {str(item) for item in answer_key.get("correct_option_ids", [])}
        correct = bool(expected_set) and selected == expected_set
    elif question_type == QuestionType.ORDERING:
        selected_order = [str(item) for item in answer_payload.get("ordered_ids", [])]
        expected_order = [str(item) for item in answer_key.get("ordered_ids", [])]
        correct = bool(expected_order) and selected_order == expected_order
    elif question_type == QuestionType.MATCHING:
        selected_pairs = {
            str(key): str(value) for key, value in answer_payload.get("pairs", {}).items()
        }
        expected_pairs = {
            str(key): str(value) for key, value in answer_key.get("pairs", {}).items()
        }
        correct = bool(expected_pairs) and selected_pairs == expected_pairs

    feedback = str(answer_key.get("correct_feedback", "Resposta correta.")) if correct else str(
        answer_key.get("incorrect_feedback", "Revise o conteúdo e tente novamente.")
    )
    return GradeOutcome(correct, float(points if correct else 0.0), feedback)


def _comic_snapshot(comic: GeneratedComic | None) -> dict[str, Any] | None:
    if comic is None:
        return None
    return {
        "id": str(comic.id),
        "title": comic.title,
        "synopsis": comic.synopsis,
        "version": comic.current_version,
        "art_direction": comic.art_direction,
        "reading_support": comic.canvas_config,
        "pages": [
            {
                "id": str(page.id),
                "page_number": page.page_number,
                "title": page.title,
                "role": page.page_role,
                "format": enum_value(page.page_format),
                "orientation": enum_value(page.orientation),
                "reading_direction": enum_value(page.reading_direction),
                "panels": [
                    {
                        "id": str(panel.id),
                        "reading_order": panel.reading_order,
                        "shape": enum_value(panel.shape),
                        "scene_description": panel.scene_description,
                        "alt_text": panel.alt_text,
                        "audio_description": panel.audio_description,
                        "image_asset_path": panel.image_asset_path,
                        "position": {
                            "x": panel.position_x,
                            "y": panel.position_y,
                            "width": panel.width,
                            "height": panel.height,
                        },
                        "balloons": [
                            {
                                "id": str(balloon.id),
                                "sequence": balloon.sequence_number,
                                "speaker": balloon.speaker_name_snapshot,
                                "type": enum_value(balloon.balloon_type),
                                "text": balloon.text,
                                "emotion": balloon.emotion,
                                "position": {
                                    "x": balloon.position_x,
                                    "y": balloon.position_y,
                                    "width": balloon.width,
                                    "height": balloon.height,
                                },
                            }
                            for balloon in panel.balloons
                        ],
                    }
                    for panel in page.panels
                ],
            }
            for page in comic.pages
        ],
    }


async def snapshot_package(
    session: AsyncSession, package: PedagogicalPackage
) -> dict[str, Any]:
    comic: GeneratedComic | None = None
    if package.comic_id is not None:
        comic = await session.scalar(
            select(GeneratedComic)
            .where(GeneratedComic.id == package.comic_id)
            .options(
                selectinload(GeneratedComic.pages)
                .selectinload(ComicPage.panels)
                .selectinload(ComicPanel.balloons)
            )
        )
    materials = [
        {
            "id": str(material.id),
            "type": enum_value(material.material_type),
            "title": material.title,
            "content": material.content,
            "position": material.position,
        }
        for material in package.materials
    ]
    student_materials = [
        material
        for material in materials
        if material["type"]
        not in {StudioMaterialType.ANSWER_KEY.value, StudioMaterialType.TEACHER_GUIDE.value}
    ]
    return {
        "schema": "educode.assignment.snapshot.v1",
        "captured_at": utcnow().isoformat(),
        "package": {
            "id": str(package.id),
            "title": package.title,
            "shared_context": package.shared_context,
            "art_direction": package.art_direction_snapshot,
            "preparation_report": package.preparation_report,
        },
        "student_materials": student_materials,
        "teacher_materials": materials,
        "comic": _comic_snapshot(comic),
    }


def student_material_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a deep JSON-safe copy without teacher-only materials or hidden answer data."""
    safe = json.loads(json.dumps(snapshot))
    safe.pop("teacher_materials", None)
    for material in safe.get("student_materials", []):
        content = material.get("content", {})
        if isinstance(content, dict):
            for key in ("answers", "answer_key", "gabarito", "teacher_only"):
                content.pop(key, None)
    return safe


def _topic_from_package(package: PedagogicalPackage) -> str:
    return str(package.shared_context.get("topic") or package.title)


def _objective_from_package(package: PedagogicalPackage) -> str:
    return str(package.shared_context.get("objective") or "Compreender o conteúdo estudado.")


def mock_question_inputs(package: PedagogicalPackage) -> list[QuestionInput]:
    topic = _topic_from_package(package)
    objective = _objective_from_package(package)
    return [
        QuestionInput(
            question_type=QuestionType.MULTIPLE_CHOICE,
            prompt=f"Qual alternativa melhor representa o objetivo do material sobre {topic}?",
            options=[
                {"id": "A", "text": objective},
                {"id": "B", "text": "Ignorar os conceitos apresentados."},
                {"id": "C", "text": "Memorizar sem compreender ou aplicar."},
                {"id": "D", "text": "Substituir o estudo por uma resposta aleatória."},
            ],
            answer_key={
                "correct_option_ids": ["A"],
                "incorrect_feedback": "Retome o objetivo apresentado no início do material.",
            },
            explanation=objective,
            points=2,
            difficulty="basic",
        ),
        QuestionInput(
            question_type=QuestionType.TRUE_FALSE,
            prompt=f"O material apresenta {topic} como parte de uma situação de aprendizagem.",
            answer_key={"value": True},
            explanation="O conteúdo foi contextualizado no pacote pedagógico.",
            points=2,
            difficulty="basic",
        ),
        QuestionInput(
            question_type=QuestionType.SHORT_TEXT,
            prompt="Escreva a palavra que completa a frase: aprender envolve compreender e _____.",
            answer_key={"accepted_answers": ["aplicar", "praticar"]},
            explanation="A aprendizagem é fortalecida pela aplicação ou prática.",
            points=2,
            difficulty="medium",
        ),
        QuestionInput(
            question_type=QuestionType.MULTIPLE_SELECT,
            prompt="Selecione ações coerentes com uma aprendizagem investigativa.",
            options=[
                {"id": "A", "text": "Observar pistas"},
                {"id": "B", "text": "Testar hipóteses"},
                {"id": "C", "text": "Ignorar evidências"},
                {"id": "D", "text": "Revisar uma tentativa"},
            ],
            answer_key={"correct_option_ids": ["A", "B", "D"]},
            explanation="Investigar envolve observar, testar e revisar.",
            points=2,
            difficulty="medium",
        ),
        QuestionInput(
            question_type=QuestionType.ESSAY,
            prompt=f"Explique com suas palavras o que você aprendeu sobre {topic}.",
            answer_key={},
            explanation="Resposta pessoal avaliada pelo professor.",
            points=2,
            difficulty="application",
            manual_grading=True,
        ),
    ]


async def get_package_for_delivery(
    session: AsyncSession, organization_id: UUID, package_id: UUID
) -> PedagogicalPackage | None:
    return await session.scalar(
        select(PedagogicalPackage)
        .where(
            PedagogicalPackage.id == package_id,
            PedagogicalPackage.organization_id == organization_id,
        )
        .options(
            selectinload(PedagogicalPackage.materials),
            selectinload(PedagogicalPackage.publication_preparations),
        )
    )


async def get_assignment(
    session: AsyncSession, organization_id: UUID, assignment_id: UUID
) -> MaterialAssignment | None:
    return await session.scalar(
        select(MaterialAssignment)
        .where(
            MaterialAssignment.id == assignment_id,
            MaterialAssignment.organization_id == organization_id,
        )
        .options(
            selectinload(MaterialAssignment.recipients),
            selectinload(MaterialAssignment.questions),
            selectinload(MaterialAssignment.attempts).selectinload(StudentAttempt.answers),
        )
    )


async def _validate_recipient(
    session: AsyncSession, organization_id: UUID, data: RecipientInput
) -> None:
    if data.recipient_type == RecipientType.CLASSROOM:
        classroom = await session.scalar(
            select(Classroom.id).where(
                Classroom.id == data.classroom_id,
                Classroom.organization_id == organization_id,
                Classroom.is_active.is_(True),
            )
        )
        if classroom is None:
            raise DeliveryError("Turma não encontrada na organização")
        return
    user = await session.scalar(
        select(User.id)
        .join(Membership, Membership.user_id == User.id)
        .where(
            User.id == data.user_id,
            User.is_active.is_(True),
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )
    )
    if user is None:
        raise DeliveryError("Usuário destinatário não encontrado na organização")


async def create_assignment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    user_name: str,
    data: AssignmentCreate,
) -> MaterialAssignment:
    package = await get_package_for_delivery(session, organization_id, data.package_id)
    if package is None:
        raise DeliveryError("Pacote pedagógico não encontrado")
    if not package.materials:
        raise DeliveryError("O pacote ainda não possui materiais gerados")
    for recipient in data.recipients:
        await _validate_recipient(session, organization_id, recipient)

    assignment = MaterialAssignment(
        organization_id=organization_id,
        package_id=package.id,
        created_by_user_id=user_id,
        created_by_name_snapshot=user_name,
        title=data.title.strip(),
        instructions=data.instructions.strip(),
        assignment_type=data.assignment_type,
        material_snapshot=await snapshot_package(session, package),
        available_from=data.available_from,
        due_at=data.due_at,
        time_limit_minutes=data.time_limit_minutes,
        maximum_attempts=data.maximum_attempts,
        maximum_score=data.maximum_score,
        minimum_score=data.minimum_score,
        feedback_policy=data.feedback_policy,
        answer_key_policy=data.answer_key_policy,
        randomize_questions=data.randomize_questions,
        randomize_options=data.randomize_options,
        allow_pause=data.allow_pause,
        allow_late_submission=data.allow_late_submission,
        late_penalty_percent=data.late_penalty_percent,
        show_result_immediately=data.show_result_immediately,
        settings=data.settings,
    )
    session.add(assignment)
    await session.flush()

    for recipient_data in data.recipients:
        assignment.recipients.append(
            AssignmentRecipient(
                recipient_type=recipient_data.recipient_type,
                classroom_id=recipient_data.classroom_id,
                user_id=recipient_data.user_id,
                available_from_override=recipient_data.available_from_override,
                due_at_override=recipient_data.due_at_override,
                maximum_attempts_override=recipient_data.maximum_attempts_override,
                time_limit_minutes_override=recipient_data.time_limit_minutes_override,
                accommodations=recipient_data.accommodations,
            )
        )

    inputs = data.questions
    if (
        not inputs
        and data.generate_mock_questions
        and data.assignment_type != AssignmentType.READING
    ):
        inputs = mock_question_inputs(package)
    for position, question_data in enumerate(inputs, start=1):
        manual = question_data.manual_grading or question_data.question_type == QuestionType.ESSAY
        assignment.questions.append(
            AssignmentQuestion(
                position=position,
                question_type=question_data.question_type,
                prompt=question_data.prompt.strip(),
                options=question_data.options,
                answer_key=question_data.answer_key,
                explanation=question_data.explanation,
                points=question_data.points,
                difficulty=question_data.difficulty,
                curriculum_skill_codes=question_data.curriculum_skill_codes,
                ct_pillar_codes=question_data.ct_pillar_codes,
                source_references=question_data.source_references,
                manual_grading=manual,
                shuffle_options=question_data.shuffle_options,
            )
        )
    await session.flush()
    return await get_assignment(session, organization_id, assignment.id) or assignment


def _recipient_to_effective(
    assignment: MaterialAssignment, recipients: list[AssignmentRecipient]
) -> dict[str, Any]:
    effective: dict[str, Any] = {
        "available_from": assignment.available_from,
        "due_at": assignment.due_at,
        "maximum_attempts": assignment.maximum_attempts,
        "time_limit_minutes": assignment.time_limit_minutes,
        "accommodations": {},
    }
    # Classroom defaults first; direct recipient intentionally wins.
    for recipient in sorted(recipients, key=lambda item: item.recipient_type == RecipientType.USER):
        if recipient.available_from_override is not None:
            effective["available_from"] = recipient.available_from_override
        if recipient.due_at_override is not None:
            effective["due_at"] = recipient.due_at_override
        if recipient.maximum_attempts_override is not None:
            effective["maximum_attempts"] = recipient.maximum_attempts_override
        if recipient.time_limit_minutes_override is not None:
            effective["time_limit_minutes"] = recipient.time_limit_minutes_override
        effective["accommodations"].update(recipient.accommodations)
    extra_time_percent = float(effective["accommodations"].get("extra_time_percent", 0) or 0)
    if effective["time_limit_minutes"] and extra_time_percent > 0:
        effective["time_limit_minutes"] = int(
            math.ceil(effective["time_limit_minutes"] * (1 + extra_time_percent / 100))
        )
    return effective


async def matching_recipients(
    session: AsyncSession, assignment_id: UUID, student_id: UUID
) -> list[AssignmentRecipient]:
    classroom_ids = select(ClassroomEnrollment.classroom_id).where(
        ClassroomEnrollment.user_id == student_id,
        ClassroomEnrollment.role == "student",
    )
    result = await session.scalars(
        select(AssignmentRecipient).where(
            AssignmentRecipient.assignment_id == assignment_id,
            AssignmentRecipient.status == RecipientStatus.ACTIVE,
            or_(
                AssignmentRecipient.user_id == student_id,
                AssignmentRecipient.classroom_id.in_(classroom_ids),
            ),
        )
    )
    return list(result.all())


async def effective_student_settings(
    session: AsyncSession, assignment: MaterialAssignment, student_id: UUID
) -> dict[str, Any] | None:
    recipients = await matching_recipients(session, assignment.id, student_id)
    if not recipients:
        return None
    return _recipient_to_effective(assignment, recipients)


async def resolved_students(
    session: AsyncSession, assignment: MaterialAssignment
) -> list[User]:
    direct_ids = [
        recipient.user_id
        for recipient in assignment.recipients
        if recipient.status == RecipientStatus.ACTIVE and recipient.user_id is not None
    ]
    classroom_ids = [
        recipient.classroom_id
        for recipient in assignment.recipients
        if recipient.status == RecipientStatus.ACTIVE and recipient.classroom_id is not None
    ]
    clauses: list[Any] = []
    if direct_ids:
        clauses.append(User.id.in_(direct_ids))
    if classroom_ids:
        enrolled_ids = select(ClassroomEnrollment.user_id).where(
            ClassroomEnrollment.classroom_id.in_(classroom_ids),
            ClassroomEnrollment.role == "student",
        )
        clauses.append(User.id.in_(enrolled_ids))
    if not clauses:
        return []
    result = await session.scalars(
        select(User)
        .join(Membership, Membership.user_id == User.id)
        .where(
            User.is_active.is_(True),
            Membership.organization_id == assignment.organization_id,
            Membership.is_active.is_(True),
            or_(*clauses),
        )
        .distinct()
        .order_by(User.full_name)
    )
    return list(result.all())


async def publish_assignment(
    session: AsyncSession, assignment: MaterialAssignment
) -> MaterialAssignment:
    if not assignment.recipients:
        raise DeliveryError("Adicione ao menos uma turma ou estudante antes de publicar")
    if assignment.assignment_type != AssignmentType.READING and not assignment.questions:
        raise DeliveryError("A publicação avaliativa precisa de questões")
    now = utcnow()
    assignment.status = (
        AssignmentStatus.SCHEDULED
        if assignment.available_from is not None and assignment.available_from > now
        else AssignmentStatus.PUBLISHED
    )
    assignment.published_at = now
    students = await resolved_students(session, assignment)
    for student in students:
        session.add(
            UserNotification(
                organization_id=assignment.organization_id,
                user_id=student.id,
                assignment_id=assignment.id,
                notification_type="assignment_published",
                title="Nova atividade disponível",
                message=f"{assignment.title} foi publicada para você.",
                action_path=f"/aluno/atividades/{assignment.id}",
            )
        )
    await session.flush()
    return assignment


def _availability_status(
    assignment: MaterialAssignment, effective: dict[str, Any], now: datetime
) -> tuple[str, bool, bool]:
    available_from = effective["available_from"]
    due_at = effective["due_at"]
    not_open = available_from is not None and available_from > now
    overdue = due_at is not None and due_at < now
    if assignment.status in {AssignmentStatus.CANCELED, AssignmentStatus.ARCHIVED}:
        return "unavailable", False, overdue
    if assignment.status == AssignmentStatus.CLOSED:
        return "closed", False, overdue
    if not_open:
        return "scheduled", False, False
    if overdue and not assignment.allow_late_submission:
        return "overdue", False, True
    return "available", True, overdue


async def list_student_assignments(
    session: AsyncSession, organization_id: UUID, student_id: UUID
) -> list[dict[str, Any]]:
    assignments = list(
        (
            await session.scalars(
                select(MaterialAssignment)
                .where(
                    MaterialAssignment.organization_id == organization_id,
                    MaterialAssignment.status.in_(
                        [
                            AssignmentStatus.SCHEDULED,
                            AssignmentStatus.PUBLISHED,
                            AssignmentStatus.CLOSED,
                        ]
                    ),
                )
                .options(selectinload(MaterialAssignment.recipients))
                .order_by(
                    MaterialAssignment.due_at.asc().nullslast(),
                    MaterialAssignment.created_at.desc(),
                )
            )
        ).all()
    )
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt).where(
                    StudentAttempt.organization_id == organization_id,
                    StudentAttempt.student_id == student_id,
                )
            )
        ).all()
    )
    by_assignment: dict[UUID, list[StudentAttempt]] = {}
    for attempt in attempts:
        by_assignment.setdefault(attempt.assignment_id, []).append(attempt)

    now = utcnow()
    cards: list[dict[str, Any]] = []
    for assignment in assignments:
        recipients = await matching_recipients(session, assignment.id, student_id)
        if not recipients:
            continue
        effective = _recipient_to_effective(assignment, recipients)
        availability, _, overdue = _availability_status(assignment, effective, now)
        own_attempts = by_assignment.get(assignment.id, [])
        active = next(
            (
                attempt
                for attempt in own_attempts
                if attempt.status in {AttemptStatus.IN_PROGRESS, AttemptStatus.REOPENED}
            ),
            None,
        )
        completed = [
            attempt
            for attempt in own_attempts
            if attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}
        ]
        if active:
            progress = "in_progress"
        elif completed:
            progress = "completed"
        elif availability == "overdue":
            progress = "overdue"
        else:
            progress = "not_started"
        percentages = [attempt.percentage for attempt in completed]
        cards.append(
            {
                "id": assignment.id,
                "title": assignment.title,
                "assignment_type": assignment.assignment_type,
                "status": availability,
                "available_from": effective["available_from"],
                "due_at": effective["due_at"],
                "time_limit_minutes": effective["time_limit_minutes"],
                "maximum_attempts": effective["maximum_attempts"],
                "attempts_used": len(own_attempts),
                "progress_status": progress,
                "best_percentage": max(percentages) if percentages else None,
                "is_late": overdue,
                "accommodations": effective["accommodations"],
            }
        )
    return cards


async def student_assignment_detail(
    session: AsyncSession,
    assignment: MaterialAssignment,
    student_id: UUID,
) -> dict[str, Any]:
    effective = await effective_student_settings(session, assignment, student_id)
    if effective is None:
        raise DeliveryError("Atividade não atribuída a este estudante")
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt)
                .where(
                    StudentAttempt.assignment_id == assignment.id,
                    StudentAttempt.student_id == student_id,
                )
                .order_by(StudentAttempt.attempt_number)
            )
        ).all()
    )
    active = next(
        (
            attempt
            for attempt in reversed(attempts)
            if attempt.status in {AttemptStatus.IN_PROGRESS, AttemptStatus.REOPENED}
        ),
        None,
    )
    status, can_start, _ = _availability_status(assignment, effective, utcnow())
    if len(attempts) >= int(effective["maximum_attempts"]) and active is None:
        can_start = False
    return {
        "id": assignment.id,
        "title": assignment.title,
        "instructions": assignment.instructions,
        "assignment_type": assignment.assignment_type,
        "available_from": effective["available_from"],
        "due_at": effective["due_at"],
        "time_limit_minutes": effective["time_limit_minutes"],
        "maximum_attempts": effective["maximum_attempts"],
        "attempts_used": len(attempts),
        "maximum_score": assignment.maximum_score,
        "material": student_material_snapshot(assignment.material_snapshot),
        "progress_status": "in_progress" if active else status,
        "can_start": can_start,
        "active_attempt_id": active.id if active else None,
        "accommodations": effective["accommodations"],
    }


def _randomization_state(
    assignment: MaterialAssignment, student_id: UUID, attempt_number: int
) -> dict[str, Any]:
    rng = random.Random(f"{assignment.id}:{student_id}:{attempt_number}")
    questions = list(assignment.questions)
    if assignment.randomize_questions:
        rng.shuffle(questions)
    question_order = [str(question.id) for question in questions]
    option_order: dict[str, list[str]] = {}
    for question in questions:
        ids = [str(option.get("id")) for option in question.options if option.get("id") is not None]
        if assignment.randomize_options or question.shuffle_options:
            rng.shuffle(ids)
        option_order[str(question.id)] = ids
    return {"question_order": question_order, "option_order": option_order}


async def create_or_resume_attempt(
    session: AsyncSession,
    assignment: MaterialAssignment,
    student_id: UUID,
) -> StudentAttempt:
    effective = await effective_student_settings(session, assignment, student_id)
    if effective is None:
        raise DeliveryError("Atividade não atribuída a este estudante")
    status, can_start, overdue = _availability_status(assignment, effective, utcnow())
    if not can_start:
        raise DeliveryError(f"A atividade não pode ser iniciada: {status}")
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt)
                .where(
                    StudentAttempt.assignment_id == assignment.id,
                    StudentAttempt.student_id == student_id,
                )
                .order_by(StudentAttempt.attempt_number)
            )
        ).all()
    )
    active = next(
        (
            attempt
            for attempt in reversed(attempts)
            if attempt.status in {AttemptStatus.IN_PROGRESS, AttemptStatus.REOPENED}
        ),
        None,
    )
    if active is not None:
        return active
    max_attempts = int(effective["maximum_attempts"])
    if len(attempts) >= max_attempts:
        raise DeliveryError("Número máximo de tentativas atingido")
    number = len(attempts) + 1
    attempt = StudentAttempt(
        organization_id=assignment.organization_id,
        assignment_id=assignment.id,
        student_id=student_id,
        attempt_number=number,
        time_limit_minutes_snapshot=effective["time_limit_minutes"],
        maximum_attempts_snapshot=max_attempts,
        randomization_state=_randomization_state(assignment, student_id, number),
        is_late=overdue,
        assessment_version_id=assignment.assessment_version_id,
    )
    session.add(attempt)
    await session.flush()
    session.add(
        LearningEvent(
            organization_id=assignment.organization_id,
            student_id=student_id,
            assignment_id=assignment.id,
            attempt_id=attempt.id,
            event_type="attempt_started",
            event_metadata={"attempt_number": number},
        )
    )
    return attempt


async def load_attempt(
    session: AsyncSession,
    organization_id: UUID,
    attempt_id: UUID,
    student_id: UUID | None = None,
) -> StudentAttempt | None:
    conditions: list[Any] = [
        StudentAttempt.id == attempt_id,
        StudentAttempt.organization_id == organization_id,
    ]
    if student_id is not None:
        conditions.append(StudentAttempt.student_id == student_id)
    return await session.scalar(
        select(StudentAttempt)
        .where(*conditions)
        .options(
            selectinload(StudentAttempt.answers).selectinload(StudentAnswer.question),
            selectinload(StudentAttempt.assignment).selectinload(MaterialAssignment.questions),
            selectinload(StudentAttempt.assignment).selectinload(MaterialAssignment.recipients),
        )
    )


def ordered_student_questions(
    assignment: MaterialAssignment, attempt: StudentAttempt
) -> list[dict[str, Any]]:
    by_id = {str(question.id): question for question in assignment.questions}
    order = attempt.randomization_state.get("question_order") or list(by_id)
    option_orders = attempt.randomization_state.get("option_order", {})
    result: list[dict[str, Any]] = []
    for question_id in order:
        question = by_id.get(str(question_id))
        if question is None:
            continue
        options_by_id = {str(option.get("id")): option for option in question.options}
        option_order = option_orders.get(str(question.id), list(options_by_id))
        options = [options_by_id[item] for item in option_order if item in options_by_id]
        result.append(
            {
                "id": question.id,
                "position": question.position,
                "question_type": question.question_type,
                "prompt": question.prompt,
                "options": options,
                "points": question.points,
                "difficulty": question.difficulty,
                "curriculum_skill_codes": question.curriculum_skill_codes,
                "ct_pillar_codes": question.ct_pillar_codes,
            }
        )
    return result


def _attempt_time_expired(attempt: StudentAttempt, now: datetime) -> bool:
    if attempt.time_limit_minutes_snapshot is None:
        return False
    return now > attempt.started_at + timedelta(minutes=attempt.time_limit_minutes_snapshot)


async def save_answer(
    session: AsyncSession,
    *,
    attempt: StudentAttempt,
    question_id: UUID,
    answer_payload: dict[str, Any],
    response_time_seconds: int,
    expected_revision: int | None,
) -> tuple[StudentAnswer, GradeOutcome, bool]:
    if attempt.status not in {AttemptStatus.IN_PROGRESS, AttemptStatus.REOPENED}:
        raise DeliveryError("A tentativa não está aberta para edição")
    if expected_revision is not None and expected_revision != attempt.autosave_revision:
        raise DeliveryError(
            f"Rascunho desatualizado. Revisão atual: {attempt.autosave_revision}"
        )
    if _attempt_time_expired(attempt, utcnow()):
        raise DeliveryError("O tempo da tentativa foi encerrado")
    question = next(
        (question for question in attempt.assignment.questions if question.id == question_id), None
    )
    if question is None:
        raise DeliveryError("Questão não pertence à atividade")
    answer = next((item for item in attempt.answers if item.question_id == question_id), None)
    is_new = answer is None
    if answer is None:
        answer = StudentAnswer(attempt_id=attempt.id, question_id=question.id)
        session.add(answer)
        attempt.answers.append(answer)
    answer.answer_payload = answer_payload
    answer.response_time_seconds = response_time_seconds
    if question.manual_grading:
        outcome = GradeOutcome(None, 0.0, None)
        answer.is_correct = None
        answer.awarded_score = 0.0
    else:
        outcome = grade_response(
            question.question_type, answer_payload, question.answer_key, question.points
        )
        answer.is_correct = outcome.is_correct
        answer.awarded_score = outcome.awarded_score
    attempt.autosave_revision += 1
    attempt.last_saved_at = utcnow()
    session.add(
        LearningEvent(
            organization_id=attempt.organization_id,
            student_id=attempt.student_id,
            assignment_id=attempt.assignment_id,
            attempt_id=attempt.id,
            question_id=question.id,
            event_type="question_answered" if is_new else "answer_changed",
            event_metadata={"autosave_revision": attempt.autosave_revision},
        )
    )
    await session.flush()
    immediate = attempt.assignment.feedback_policy == FeedbackPolicy.IMMEDIATE
    return answer, outcome, immediate


def _recalculate_attempt(attempt: StudentAttempt) -> None:
    questions = [question for question in attempt.assignment.questions if not question.is_annulled]
    answers = {answer.question_id: answer for answer in attempt.answers}
    total_points = sum(question.points for question in questions) or 1.0
    awarded = sum(
        answers[question.id].awarded_score
        for question in questions
        if question.id in answers
    )
    scaled = awarded / total_points * attempt.assignment.maximum_score
    if attempt.is_late and attempt.assignment.late_penalty_percent > 0:
        penalty = scaled * attempt.assignment.late_penalty_percent / 100
        scaled -= penalty
        attempt.late_penalty_applied = penalty
    attempt.score = round(max(scaled, 0.0), 4)
    attempt.percentage = round(
        attempt.score / attempt.assignment.maximum_score * 100
        if attempt.assignment.maximum_score
        else 0.0,
        2,
    )
    manual_pending = any(
        question.manual_grading
        and (
            question.id not in answers
            or answers[question.id].corrected_by_user_id is None
        )
        for question in questions
    )
    attempt.grading_complete = not manual_pending
    if attempt.submitted_at is not None:
        attempt.status = (
            AttemptStatus.GRADED if attempt.grading_complete else AttemptStatus.SUBMITTED
        )
        if attempt.grading_complete:
            attempt.graded_at = utcnow()


async def submit_attempt(
    session: AsyncSession,
    attempt: StudentAttempt,
    time_spent_seconds: int,
) -> StudentAttempt:
    if attempt.status not in {AttemptStatus.IN_PROGRESS, AttemptStatus.REOPENED}:
        raise DeliveryError("A tentativa já foi enviada ou encerrada")
    now = utcnow()
    effective = await effective_student_settings(
        session, attempt.assignment, attempt.student_id
    )
    if effective is None:
        raise DeliveryError("Acesso à atividade removido")
    due_at = effective["due_at"]
    attempt.is_late = due_at is not None and now > due_at
    if attempt.is_late and not attempt.assignment.allow_late_submission:
        raise DeliveryError("O prazo da atividade foi encerrado")
    attempt.submitted_at = now
    attempt.time_spent_seconds = time_spent_seconds
    _recalculate_attempt(attempt)
    session.add(
        LearningEvent(
            organization_id=attempt.organization_id,
            student_id=attempt.student_id,
            assignment_id=attempt.assignment_id,
            attempt_id=attempt.id,
            event_type="attempt_submitted",
            event_metadata={
                "score": attempt.score,
                "percentage": attempt.percentage,
                "grading_complete": attempt.grading_complete,
            },
        )
    )
    session.add(
        UserNotification(
            organization_id=attempt.organization_id,
            user_id=attempt.assignment.created_by_user_id,
            assignment_id=attempt.assignment_id,
            notification_type="attempt_submitted",
            title="Nova entrega recebida",
            message=f"Um estudante enviou {attempt.assignment.title}.",
            action_path=f"/publicacoes/{attempt.assignment_id}",
        )
    )
    from app.services.assessment import recalculate_attempt_evidence

    await recalculate_attempt_evidence(session, attempt=attempt)
    await session.flush()
    return attempt


def results_available(
    assignment: MaterialAssignment,
    attempt: StudentAttempt,
    now: datetime,
    due_at: datetime | None = None,
) -> bool:
    if assignment.show_result_immediately:
        return True
    if assignment.feedback_policy == FeedbackPolicy.IMMEDIATE:
        return True
    if assignment.feedback_policy == FeedbackPolicy.AFTER_SUBMISSION:
        return attempt.submitted_at is not None
    if assignment.feedback_policy == FeedbackPolicy.AFTER_DUE_DATE:
        effective_due = due_at if due_at is not None else assignment.due_at
        return effective_due is not None and now >= effective_due
    return assignment.results_released_at is not None and now >= assignment.results_released_at


def answer_key_available(
    assignment: MaterialAssignment,
    attempt: StudentAttempt,
    now: datetime,
    due_at: datetime | None = None,
) -> bool:
    if assignment.answer_key_policy == AnswerKeyPolicy.NEVER:
        return False
    if assignment.answer_key_policy == AnswerKeyPolicy.AFTER_SUBMISSION:
        return attempt.submitted_at is not None
    if assignment.answer_key_policy == AnswerKeyPolicy.AFTER_DUE_DATE:
        effective_due = due_at if due_at is not None else assignment.due_at
        return effective_due is not None and now >= effective_due
    return assignment.results_released_at is not None and now >= assignment.results_released_at


async def manual_grade_answer(
    session: AsyncSession,
    *,
    organization_id: UUID,
    answer_id: UUID,
    awarded_score: float,
    is_correct: bool | None,
    feedback: str | None,
    grader_id: UUID,
) -> StudentAnswer:
    answer = await session.scalar(
        select(StudentAnswer)
        .join(StudentAttempt, StudentAttempt.id == StudentAnswer.attempt_id)
        .where(StudentAnswer.id == answer_id, StudentAttempt.organization_id == organization_id)
        .options(
            selectinload(StudentAnswer.question),
            selectinload(StudentAnswer.attempt)
            .selectinload(StudentAttempt.assignment)
            .selectinload(MaterialAssignment.questions),
            selectinload(StudentAnswer.attempt).selectinload(StudentAttempt.answers),
        )
    )
    if answer is None:
        raise DeliveryError("Resposta não encontrada")
    if awarded_score > answer.question.points:
        raise DeliveryError("Pontuação superior ao valor da questão")
    answer.awarded_score = awarded_score
    answer.is_correct = is_correct
    answer.teacher_feedback = feedback
    answer.corrected_by_user_id = grader_id
    answer.corrected_at = utcnow()
    _recalculate_attempt(answer.attempt)
    answer.attempt.grading_revision += 1
    from app.services.assessment import recalculate_attempt_evidence

    await recalculate_attempt_evidence(session, attempt=answer.attempt)
    if answer.attempt.grading_complete:
        session.add(
            UserNotification(
                organization_id=organization_id,
                user_id=answer.attempt.student_id,
                assignment_id=answer.attempt.assignment_id,
                notification_type="assignment_graded",
                title="Atividade corrigida",
                message=f"Seu resultado em {answer.attempt.assignment.title} está disponível.",
                action_path=f"/aluno/atividades/{answer.attempt.assignment_id}",
            )
        )
    await session.flush()
    return answer


async def reopen_attempt(
    session: AsyncSession,
    attempt: StudentAttempt,
    teacher_id: UUID,
    reason: str,
) -> StudentAttempt:
    if attempt.status not in {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}:
        raise DeliveryError("Somente tentativas entregues podem ser reabertas")
    attempt.status = AttemptStatus.REOPENED
    attempt.reopened_by_user_id = teacher_id
    attempt.reopened_at = utcnow()
    attempt.submitted_at = None
    attempt.graded_at = None
    attempt.grading_complete = False
    attempt.teacher_feedback = reason
    session.add(
        UserNotification(
            organization_id=attempt.organization_id,
            user_id=attempt.student_id,
            assignment_id=attempt.assignment_id,
            notification_type="attempt_reopened",
            title="Nova oportunidade liberada",
            message=reason,
            action_path=f"/aluno/atividades/{attempt.assignment_id}",
        )
    )
    await session.flush()
    return attempt


async def assignment_progress(
    session: AsyncSession, assignment: MaterialAssignment
) -> AssignmentProgress:
    students = await resolved_students(session, assignment)
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt)
                .where(StudentAttempt.assignment_id == assignment.id)
                .options(selectinload(StudentAttempt.answers))
            )
        ).all()
    )
    attempts_by_student: dict[UUID, list[StudentAttempt]] = {}
    for attempt in attempts:
        attempts_by_student.setdefault(attempt.student_id, []).append(attempt)
    rows: list[StudentProgressRow] = []
    counters: Counter[str] = Counter()
    completed_percentages: list[float] = []
    for student in students:
        own = attempts_by_student.get(student.id, [])
        active = [
            item
            for item in own
            if item.status in {AttemptStatus.IN_PROGRESS, AttemptStatus.REOPENED}
        ]
        submitted = [
            item for item in own if item.status in {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}
        ]
        if any(item.status == AttemptStatus.GRADED for item in own):
            status = "graded"
        elif submitted:
            status = "submitted"
        elif active:
            status = "in_progress"
        else:
            status = "not_started"
        counters[status] += 1
        best = max(submitted, key=lambda item: item.percentage, default=None)
        if best is not None:
            completed_percentages.append(best.percentage)
        last_activity_candidates = [
            item.last_saved_at or item.submitted_at or item.started_at for item in own
        ]
        rows.append(
            StudentProgressRow(
                student_id=student.id,
                student_name=student.full_name,
                student_email=student.email,
                progress_status=status,
                attempts_count=len(own),
                best_score=best.score if best else None,
                best_percentage=best.percentage if best else None,
                last_activity_at=(
                    max(last_activity_candidates) if last_activity_candidates else None
                ),
                is_late=any(item.is_late for item in own),
            )
        )

    question_rows: list[QuestionProgressRow] = []
    for question in assignment.questions:
        question_answers = [
            answer
            for attempt in attempts
            if attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}
            for answer in attempt.answers
            if answer.question_id == question.id
        ]
        automatic = [answer for answer in question_answers if answer.is_correct is not None]
        correct = [answer for answer in automatic if answer.is_correct]
        wrong_counter: Counter[str] = Counter()
        for answer in automatic:
            if not answer.is_correct:
                serialized = json.dumps(
                    answer.answer_payload, sort_keys=True, ensure_ascii=False
                )
                wrong_counter[serialized] += 1
        common_wrong = None
        if wrong_counter:
            common_wrong = json.loads(wrong_counter.most_common(1)[0][0])
        question_rows.append(
            QuestionProgressRow(
                question_id=question.id,
                position=question.position,
                prompt=question.prompt,
                response_count=len(question_answers),
                automatically_graded_count=len(automatic),
                correct_count=len(correct),
                correct_rate=round(len(correct) / len(automatic) * 100, 2) if automatic else None,
                average_score=round(
                    sum(answer.awarded_score for answer in question_answers)
                    / len(question_answers),
                    4,
                )
                if question_answers
                else None,
                most_common_wrong_answer=common_wrong,
            )
        )
    total = len(students)
    completed_count = counters["submitted"] + counters["graded"]
    return AssignmentProgress(
        assignment_id=assignment.id,
        total_students=total,
        not_started=counters["not_started"],
        in_progress=counters["in_progress"],
        submitted=counters["submitted"],
        graded=counters["graded"],
        average_percentage=round(sum(completed_percentages) / len(completed_percentages), 2)
        if completed_percentages
        else None,
        completion_rate=round(completed_count / total * 100, 2) if total else 0.0,
        students=rows,
        questions=question_rows,
    )


async def grading_queue(
    session: AsyncSession, assignment: MaterialAssignment
) -> list[GradingQueueItem]:
    rows = (
        await session.execute(
            select(StudentAnswer, StudentAttempt, AssignmentQuestion, User)
            .join(StudentAttempt, StudentAttempt.id == StudentAnswer.attempt_id)
            .join(AssignmentQuestion, AssignmentQuestion.id == StudentAnswer.question_id)
            .join(User, User.id == StudentAttempt.student_id)
            .where(
                StudentAttempt.assignment_id == assignment.id,
                StudentAttempt.status == AttemptStatus.SUBMITTED,
                AssignmentQuestion.manual_grading.is_(True),
                StudentAnswer.corrected_by_user_id.is_(None),
            )
            .order_by(StudentAttempt.submitted_at, User.full_name, AssignmentQuestion.position)
        )
    ).all()
    return [
        GradingQueueItem(
            answer_id=answer.id,
            attempt_id=attempt.id,
            student_id=student.id,
            student_name=student.full_name,
            question_id=question.id,
            question_prompt=question.prompt,
            answer_payload=answer.answer_payload,
            maximum_points=question.points,
            awarded_score=answer.awarded_score,
            teacher_feedback=answer.teacher_feedback,
        )
        for answer, attempt, question, student in rows
    ]


async def create_learning_event(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
    assignment_id: UUID,
    event_type: str,
    attempt_id: UUID | None,
    question_id: UUID | None,
    page_number: int | None,
    metadata: dict[str, Any],
) -> LearningEvent:
    event = LearningEvent(
        organization_id=organization_id,
        student_id=student_id,
        assignment_id=assignment_id,
        attempt_id=attempt_id,
        question_id=question_id,
        event_type=event_type,
        page_number=page_number,
        event_metadata=metadata,
    )
    session.add(event)
    await session.flush()
    return event


async def grant_extra_attempt(
    session: AsyncSession,
    *,
    assignment: MaterialAssignment,
    student_id: UUID,
    additional_attempts: int,
    due_at_override: datetime | None,
    reason: str,
) -> AssignmentRecipient:
    effective = await effective_student_settings(session, assignment, student_id)
    if effective is None:
        raise DeliveryError("Estudante não pertence ao público desta atividade")
    direct = next(
        (
            recipient
            for recipient in assignment.recipients
            if recipient.recipient_type == RecipientType.USER
            and recipient.user_id == student_id
            and recipient.status == RecipientStatus.ACTIVE
        ),
        None,
    )
    new_limit = int(effective["maximum_attempts"]) + additional_attempts
    if direct is None:
        direct = AssignmentRecipient(
            assignment_id=assignment.id,
            recipient_type=RecipientType.USER,
            user_id=student_id,
            maximum_attempts_override=new_limit,
            due_at_override=due_at_override,
            accommodations=dict(effective["accommodations"]),
        )
        session.add(direct)
        assignment.recipients.append(direct)
    else:
        direct.maximum_attempts_override = new_limit
        if due_at_override is not None:
            direct.due_at_override = due_at_override
    session.add(
        UserNotification(
            organization_id=assignment.organization_id,
            user_id=student_id,
            assignment_id=assignment.id,
            notification_type="extra_attempt_granted",
            title="Tentativa adicional liberada",
            message=reason,
            action_path=f"/aluno/atividades/{assignment.id}",
        )
    )
    await session.flush()
    return direct


async def duplicate_assignment(
    session: AsyncSession,
    *,
    assignment: MaterialAssignment,
    user_id: UUID,
    user_name: str,
    title: str | None,
    copy_recipients: bool,
) -> MaterialAssignment:
    clone = MaterialAssignment(
        organization_id=assignment.organization_id,
        package_id=assignment.package_id,
        created_by_user_id=user_id,
        created_by_name_snapshot=user_name,
        title=title or f"{assignment.title} — cópia",
        instructions=assignment.instructions,
        assignment_type=assignment.assignment_type,
        material_snapshot=json.loads(json.dumps(assignment.material_snapshot)),
        snapshot_version=assignment.snapshot_version,
        available_from=None,
        due_at=None,
        time_limit_minutes=assignment.time_limit_minutes,
        maximum_attempts=assignment.maximum_attempts,
        maximum_score=assignment.maximum_score,
        minimum_score=assignment.minimum_score,
        feedback_policy=assignment.feedback_policy,
        answer_key_policy=assignment.answer_key_policy,
        randomize_questions=assignment.randomize_questions,
        randomize_options=assignment.randomize_options,
        allow_pause=assignment.allow_pause,
        allow_late_submission=assignment.allow_late_submission,
        late_penalty_percent=assignment.late_penalty_percent,
        show_result_immediately=assignment.show_result_immediately,
        settings=json.loads(json.dumps(assignment.settings)),
        status=AssignmentStatus.DRAFT,
    )
    session.add(clone)
    await session.flush()
    for question in assignment.questions:
        clone.questions.append(
            AssignmentQuestion(
                position=question.position,
                question_type=question.question_type,
                prompt=question.prompt,
                options=json.loads(json.dumps(question.options)),
                answer_key=json.loads(json.dumps(question.answer_key)),
                explanation=question.explanation,
                points=question.points,
                difficulty=question.difficulty,
                curriculum_skill_codes=list(question.curriculum_skill_codes),
                ct_pillar_codes=list(question.ct_pillar_codes),
                source_references=json.loads(json.dumps(question.source_references)),
                manual_grading=question.manual_grading,
                shuffle_options=question.shuffle_options,
            )
        )
    if copy_recipients:
        for recipient in assignment.recipients:
            if recipient.status != RecipientStatus.ACTIVE:
                continue
            clone.recipients.append(
                AssignmentRecipient(
                    recipient_type=recipient.recipient_type,
                    classroom_id=recipient.classroom_id,
                    user_id=recipient.user_id,
                    available_from_override=None,
                    due_at_override=None,
                    maximum_attempts_override=recipient.maximum_attempts_override,
                    time_limit_minutes_override=recipient.time_limit_minutes_override,
                    accommodations=json.loads(json.dumps(recipient.accommodations)),
                )
            )
    await session.flush()
    return await get_assignment(session, assignment.organization_id, clone.id) or clone

