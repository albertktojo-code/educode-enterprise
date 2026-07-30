from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analytics import (
    AlertSeverity,
    AlertStatus,
    AnalyticsJobStatus,
    AnalyticsRefreshJob,
    AssignmentItemMetric,
    ClassroomSkillMetric,
    InterventionStatus,
    LearningAlert,
    LearningIntervention,
    StudentProgressSnapshot,
    StudentSkillMetric,
)
from app.models.auth import User
from app.models.delivery import (
    AssignmentQuestion,
    AssignmentRecipient,
    AttemptStatus,
    MaterialAssignment,
    RecipientStatus,
    RecipientType,
    StudentAnswer,
    StudentAttempt,
)
from app.models.education import Classroom, ClassroomEnrollment
from app.schemas.analytics import AnalyticsRefreshRequest

VALID_ATTEMPT_STATUSES = {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}


@dataclass(slots=True)
class SkillAccumulator:
    awarded: float = 0.0
    possible: float = 0.0
    evidence_count: int = 0
    correct_count: int = 0
    last_activity_at: datetime | None = None


@dataclass(slots=True)
class QuestionAccumulator:
    response_count: int = 0
    correct_count: int = 0
    omission_count: int = 0
    awarded_sum: float = 0.0
    response_time_sum: int = 0
    distractors: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.distractors is None:
            self.distractors = {}


def utcnow() -> datetime:
    return datetime.now(UTC)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def mastery_level(score: float, evidence_count: int) -> str:
    if evidence_count <= 0:
        return "not_evaluated"
    if score < 40:
        return "initial"
    if score < 60:
        return "developing"
    if score < 85:
        return "adequate"
    return "advanced"


def confidence_score(evidence_count: int) -> float:
    return round(clamp((evidence_count / 5) * 100), 2)


def difficulty_label(index: float | None) -> str:
    if index is None:
        return "sem dados"
    if index > 0.8:
        return "fácil"
    if index >= 0.4:
        return "moderada"
    return "difícil"


def answer_label(payload: dict[str, Any]) -> str:
    if not payload:
        return "Sem resposta"
    for key in ("selected_option", "value", "answer", "text", "selected"):
        value = payload.get(key)
        if value not in (None, "", []):
            if isinstance(value, list):
                return " | ".join(str(item) for item in value)
            return str(value)
    return str(payload)


def select_attempts(attempts: Iterable[StudentAttempt], policy: str) -> list[StudentAttempt]:
    grouped: dict[tuple[UUID, UUID], list[StudentAttempt]] = defaultdict(list)
    for attempt in attempts:
        if attempt.status in VALID_ATTEMPT_STATUSES:
            grouped[(attempt.assignment_id, attempt.student_id)].append(attempt)

    selected: list[StudentAttempt] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: (item.attempt_number, item.started_at))
        if policy == "all":
            selected.extend(ordered)
        elif policy == "first":
            selected.append(ordered[0])
        elif policy == "latest":
            selected.append(ordered[-1])
        else:
            selected.append(max(ordered, key=lambda item: (item.percentage, item.attempt_number)))
    return selected


def calculate_discrimination(rows: list[tuple[float, bool | None]]) -> float | None:
    valid = [(score, correct) for score, correct in rows if correct is not None]
    if len(valid) < 6:
        return None
    ordered = sorted(valid, key=lambda item: item[0])
    size = max(1, round(len(ordered) * 0.27))
    lower = ordered[:size]
    upper = ordered[-size:]
    lower_rate = sum(1 for _, correct in lower if correct) / len(lower)
    upper_rate = sum(1 for _, correct in upper if correct) / len(upper)
    return round(upper_rate - lower_rate, 4)


def trend_direction(values: list[float]) -> str:
    if len(values) < 2:
        return "stable"
    delta = values[-1] - values[0]
    if delta >= 5:
        return "up"
    if delta <= -5:
        return "down"
    return "stable"


async def load_attempts(
    session: AsyncSession,
    organization_id: UUID,
    *,
    assignment_id: UUID | None = None,
    student_id: UUID | None = None,
) -> list[StudentAttempt]:
    statement = (
        select(StudentAttempt)
        .where(StudentAttempt.organization_id == organization_id)
        .options(
            selectinload(StudentAttempt.answers).selectinload(StudentAnswer.question),
            selectinload(StudentAttempt.assignment).selectinload(MaterialAssignment.recipients),
        )
    )
    if assignment_id is not None:
        statement = statement.where(StudentAttempt.assignment_id == assignment_id)
    if student_id is not None:
        statement = statement.where(StudentAttempt.student_id == student_id)
    return list((await session.scalars(statement)).unique().all())


def _classrooms_for_attempt(attempt: StudentAttempt) -> list[UUID]:
    return [
        recipient.classroom_id
        for recipient in attempt.assignment.recipients
        if recipient.status == RecipientStatus.ACTIVE
        and recipient.recipient_type == RecipientType.CLASSROOM
        and recipient.classroom_id is not None
    ]


async def refresh_analytics(
    session: AsyncSession,
    *,
    organization_id: UUID,
    requested_by_user_id: UUID,
    request: AnalyticsRefreshRequest,
) -> AnalyticsRefreshJob:
    job = AnalyticsRefreshJob(
        organization_id=organization_id,
        requested_by_user_id=requested_by_user_id,
        status=AnalyticsJobStatus.PROCESSING,
        attempt_policy=request.attempt_policy,
        filters=request.model_dump(mode="json", exclude={"create_snapshots", "generate_alerts"}),
        started_at=utcnow(),
    )
    session.add(job)
    await session.flush()

    try:
        attempts = await load_attempts(
            session,
            organization_id,
            assignment_id=request.assignment_id,
            student_id=request.student_id,
        )
        selected = select_attempts(attempts, request.attempt_policy)
        if request.classroom_id is not None:
            selected = [
                attempt for attempt in selected if request.classroom_id in _classrooms_for_attempt(attempt)
            ]

        await _clear_metrics(session, organization_id, request)
        student_metrics, classroom_metrics, question_metrics = _aggregate(selected)
        calculated_at = utcnow()

        for (student_id, skill_code, pillar_code), accumulator in student_metrics.items():
            score = 0.0 if accumulator.possible <= 0 else accumulator.awarded / accumulator.possible * 100
            metric = StudentSkillMetric(
                organization_id=organization_id,
                student_id=student_id,
                subject_id=None,
                skill_code=skill_code,
                ct_pillar_code=pillar_code,
                proficiency_score=round(clamp(score), 2),
                confidence_score=confidence_score(accumulator.evidence_count),
                evidence_count=accumulator.evidence_count,
                correct_count=accumulator.correct_count,
                total_count=accumulator.evidence_count,
                last_activity_at=accumulator.last_activity_at,
                calculated_at=calculated_at,
            )
            session.add(metric)
            if request.create_snapshots:
                session.add(
                    StudentProgressSnapshot(
                        organization_id=organization_id,
                        student_id=student_id,
                        subject_id=None,
                        skill_code=skill_code,
                        ct_pillar_code=pillar_code,
                        proficiency_score=metric.proficiency_score,
                        evidence_count=metric.evidence_count,
                        recorded_at=calculated_at,
                    )
                )

        for (classroom_id, skill_code, pillar_code), student_scores in classroom_metrics.items():
            scores = list(student_scores.values())
            evidence = sum(item[1] for item in student_scores.values())
            session.add(
                ClassroomSkillMetric(
                    organization_id=organization_id,
                    classroom_id=classroom_id,
                    skill_code=skill_code,
                    ct_pillar_code=pillar_code,
                    average_score=round(sum(item[0] for item in scores) / len(scores), 2) if scores else 0.0,
                    median_score=round(median(item[0] for item in scores), 2) if scores else 0.0,
                    student_count=len(scores),
                    evidence_count=evidence,
                    calculated_at=calculated_at,
                )
            )

        attempt_percentage_by_id = {attempt.id: attempt.percentage for attempt in selected}
        for question_id, data in question_metrics.items():
            question = data["question"]
            accumulator: QuestionAccumulator = data["accumulator"]
            discrimination_rows = data["discrimination"]
            response_count = accumulator.response_count
            session.add(
                AssignmentItemMetric(
                    organization_id=organization_id,
                    assignment_id=question.assignment_id,
                    assignment_question_id=question_id,
                    response_count=response_count,
                    correct_count=accumulator.correct_count,
                    omission_count=accumulator.omission_count,
                    difficulty_index=(round(accumulator.correct_count / response_count, 4) if response_count else None),
                    discrimination_index=calculate_discrimination(
                        [(attempt_percentage_by_id.get(attempt_id, score), correct) for attempt_id, score, correct in discrimination_rows]
                    ),
                    average_response_time=(round(accumulator.response_time_sum / response_count, 2) if response_count else None),
                    average_awarded_score=(round(accumulator.awarded_sum / response_count, 3) if response_count else None),
                    distractor_distribution=accumulator.distractors or {},
                    calculated_at=calculated_at,
                )
            )

        alerts_created = 0
        if request.generate_alerts:
            alerts_created = await _generate_alerts(
                session,
                organization_id=organization_id,
                student_metrics=student_metrics,
                classroom_metrics=classroom_metrics,
                question_metrics=question_metrics,
            )

        job.status = AnalyticsJobStatus.COMPLETED
        job.finished_at = utcnow()
        job.result_summary = {
            "attempts_considered": len(selected),
            "student_metrics": len(student_metrics),
            "classroom_metrics": len(classroom_metrics),
            "question_metrics": len(question_metrics),
            "alerts_created": alerts_created,
        }
    except Exception as exc:
        job.status = AnalyticsJobStatus.FAILED
        job.error_message = str(exc)
        job.finished_at = utcnow()
        raise
    return job


async def _clear_metrics(
    session: AsyncSession, organization_id: UUID, request: AnalyticsRefreshRequest
) -> None:
    # Refreshes are deterministic and replace aggregate tables for the organization.
    await session.execute(delete(StudentSkillMetric).where(StudentSkillMetric.organization_id == organization_id))
    await session.execute(delete(ClassroomSkillMetric).where(ClassroomSkillMetric.organization_id == organization_id))
    await session.execute(delete(AssignmentItemMetric).where(AssignmentItemMetric.organization_id == organization_id))
    if request.generate_alerts:
        await session.execute(
            delete(LearningAlert).where(
                LearningAlert.organization_id == organization_id,
                LearningAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            )
        )


def _aggregate(
    attempts: list[StudentAttempt],
) -> tuple[
    dict[tuple[UUID, str, str], SkillAccumulator],
    dict[tuple[UUID, str, str], dict[UUID, tuple[float, int]]],
    dict[UUID, dict[str, Any]],
]:
    student_metrics: dict[tuple[UUID, str, str], SkillAccumulator] = defaultdict(SkillAccumulator)
    classroom_raw: dict[tuple[UUID, str, str, UUID], SkillAccumulator] = defaultdict(SkillAccumulator)
    question_metrics: dict[UUID, dict[str, Any]] = {}

    for attempt in attempts:
        activity_at = attempt.submitted_at or attempt.graded_at or attempt.started_at
        classroom_ids = _classrooms_for_attempt(attempt)
        for answer in attempt.answers:
            question = answer.question
            possible = max(float(question.points), 0.0001)
            dimensions = [(code, "") for code in question.curriculum_skill_codes]
            dimensions.extend(("", code) for code in question.ct_pillar_codes)
            if not dimensions:
                dimensions = [("general", "")]
            for skill_code, pillar_code in dimensions:
                key = (attempt.student_id, skill_code, pillar_code)
                _update_accumulator(student_metrics[key], answer, possible, activity_at)
                for classroom_id in classroom_ids:
                    ckey = (classroom_id, skill_code, pillar_code, attempt.student_id)
                    _update_accumulator(classroom_raw[ckey], answer, possible, activity_at)

            qdata = question_metrics.setdefault(
                question.id,
                {
                    "question": question,
                    "accumulator": QuestionAccumulator(),
                    "discrimination": [],
                },
            )
            qacc: QuestionAccumulator = qdata["accumulator"]
            qacc.response_count += 1
            qacc.correct_count += int(answer.is_correct is True)
            qacc.omission_count += int(not answer.answer_payload)
            qacc.awarded_sum += answer.awarded_score
            qacc.response_time_sum += max(0, answer.response_time_seconds)
            label = answer_label(answer.answer_payload)
            assert qacc.distractors is not None
            qacc.distractors[label] = qacc.distractors.get(label, 0) + 1
            qdata["discrimination"].append((attempt.id, attempt.percentage, answer.is_correct))

    classroom_metrics: dict[tuple[UUID, str, str], dict[UUID, tuple[float, int]]] = defaultdict(dict)
    for (classroom_id, skill_code, pillar_code, student_id), accumulator in classroom_raw.items():
        score = 0.0 if accumulator.possible <= 0 else accumulator.awarded / accumulator.possible * 100
        classroom_metrics[(classroom_id, skill_code, pillar_code)][student_id] = (
            round(clamp(score), 2),
            accumulator.evidence_count,
        )
    return student_metrics, classroom_metrics, question_metrics


def _update_accumulator(
    accumulator: SkillAccumulator,
    answer: StudentAnswer,
    possible: float,
    activity_at: datetime | None,
) -> None:
    accumulator.awarded += max(0.0, answer.awarded_score)
    accumulator.possible += possible
    accumulator.evidence_count += 1
    accumulator.correct_count += int(answer.is_correct is True)
    if activity_at is not None and (
        accumulator.last_activity_at is None or activity_at > accumulator.last_activity_at
    ):
        accumulator.last_activity_at = activity_at


async def _generate_alerts(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_metrics: dict[tuple[UUID, str, str], SkillAccumulator],
    classroom_metrics: dict[tuple[UUID, str, str], dict[UUID, tuple[float, int]]],
    question_metrics: dict[UUID, dict[str, Any]],
) -> int:
    count = 0
    for (student_id, skill_code, pillar_code), accumulator in student_metrics.items():
        score = 0.0 if accumulator.possible <= 0 else accumulator.awarded / accumulator.possible * 100
        if accumulator.evidence_count >= 3 and score < 50:
            dimension = skill_code or pillar_code
            session.add(
                LearningAlert(
                    organization_id=organization_id,
                    student_id=student_id,
                    alert_type="student_low_mastery",
                    severity=AlertSeverity.ATTENTION,
                    title=f"Dificuldade persistente em {dimension}",
                    description=f"O desempenho calculado foi {score:.1f}% em {accumulator.evidence_count} evidências.",
                    explanation="Gerado porque o estudante ficou abaixo de 50% com pelo menos três evidências válidas.",
                    evidence={"dimension": dimension, "score": round(score, 2), "evidence_count": accumulator.evidence_count},
                    rule_code="STUDENT_SCORE_LT_50_EVIDENCE_GTE_3",
                )
            )
            count += 1

    for (classroom_id, skill_code, pillar_code), students in classroom_metrics.items():
        evidence = sum(item[1] for item in students.values())
        average = sum(item[0] for item in students.values()) / len(students) if students else 0.0
        if evidence >= 5 and average < 60:
            dimension = skill_code or pillar_code
            session.add(
                LearningAlert(
                    organization_id=organization_id,
                    classroom_id=classroom_id,
                    alert_type="classroom_skill_gap",
                    severity=AlertSeverity.ATTENTION,
                    title=f"Turma com dificuldade em {dimension}",
                    description=f"A média da turma foi {average:.1f}% em {evidence} evidências.",
                    explanation="Gerado porque a média ficou abaixo de 60% com pelo menos cinco evidências.",
                    evidence={"dimension": dimension, "average": round(average, 2), "evidence_count": evidence},
                    rule_code="CLASSROOM_AVG_LT_60_EVIDENCE_GTE_5",
                )
            )
            count += 1

    for question_id, data in question_metrics.items():
        question: AssignmentQuestion = data["question"]
        accumulator: QuestionAccumulator = data["accumulator"]
        if accumulator.response_count >= 5:
            rate = accumulator.correct_count / accumulator.response_count
            if rate < 0.4:
                session.add(
                    LearningAlert(
                        organization_id=organization_id,
                        assignment_id=question.assignment_id,
                        alert_type="difficult_question",
                        severity=AlertSeverity.PRIORITY if rate < 0.2 else AlertSeverity.ATTENTION,
                        title=f"Questão {question.position} com alto índice de erro",
                        description=f"Apenas {rate * 100:.1f}% das respostas foram corretas.",
                        explanation="Gerado porque a taxa de acerto ficou abaixo de 40% com pelo menos cinco respostas.",
                        evidence={"question_id": str(question_id), "correct_rate": round(rate, 4), "response_count": accumulator.response_count},
                        rule_code="QUESTION_CORRECT_RATE_LT_40_RESPONSES_GTE_5",
                    )
                )
                count += 1
    return count


async def dashboard_summary(
    session: AsyncSession, organization_id: UUID, attempt_policy: str = "best"
) -> dict[str, Any]:
    attempts = select_attempts(await load_attempts(session, organization_id), attempt_policy)
    students = {attempt.student_id for attempt in attempts}
    assignments = {attempt.assignment_id for attempt in attempts}
    valid = [attempt for attempt in attempts if attempt.status in VALID_ATTEMPT_STATUSES]
    average = sum(item.percentage for item in valid) / len(valid) if valid else None
    total_recipients = await session.scalar(
        select(func.count(AssignmentRecipient.id))
        .join(MaterialAssignment, MaterialAssignment.id == AssignmentRecipient.assignment_id)
        .where(
            MaterialAssignment.organization_id == organization_id,
            AssignmentRecipient.status == RecipientStatus.ACTIVE,
        )
    ) or 0
    completion = (len(valid) / total_recipients * 100) if total_recipients else 0.0
    open_alerts = await session.scalar(
        select(func.count(LearningAlert.id)).where(
            LearningAlert.organization_id == organization_id,
            LearningAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
        )
    ) or 0
    attention = await session.scalar(
        select(func.count(func.distinct(LearningAlert.student_id))).where(
            LearningAlert.organization_id == organization_id,
            LearningAlert.student_id.is_not(None),
            LearningAlert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
        )
    ) or 0
    difficult = await session.scalar(
        select(func.count(AssignmentItemMetric.id)).where(
            AssignmentItemMetric.organization_id == organization_id,
            AssignmentItemMetric.difficulty_index < 0.4,
            AssignmentItemMetric.response_count >= 5,
        )
    ) or 0
    pending = await session.scalar(
        select(func.count(StudentAnswer.id))
        .join(StudentAttempt, StudentAttempt.id == StudentAnswer.attempt_id)
        .join(AssignmentQuestion, AssignmentQuestion.id == StudentAnswer.question_id)
        .where(
            StudentAttempt.organization_id == organization_id,
            AssignmentQuestion.manual_grading.is_(True),
            StudentAnswer.corrected_at.is_(None),
        )
    ) or 0
    latest_refresh = await session.scalar(
        select(func.max(AnalyticsRefreshJob.finished_at)).where(
            AnalyticsRefreshJob.organization_id == organization_id,
            AnalyticsRefreshJob.status == AnalyticsJobStatus.COMPLETED,
        )
    )
    return {
        "students_count": len(students),
        "assignments_count": len(assignments),
        "completion_rate": round(clamp(completion), 2),
        "average_percentage": round(average, 2) if average is not None else None,
        "students_needing_attention": int(attention),
        "difficult_questions": int(difficult),
        "open_alerts": int(open_alerts),
        "pending_manual_grading": int(pending),
        "latest_refresh_at": latest_refresh,
        "attempt_policy": attempt_policy,
    }


async def data_quality(session: AsyncSession, organization_id: UUID) -> dict[str, Any]:
    attempts = await load_attempts(session, organization_id)
    valid = [item for item in attempts if item.status in VALID_ATTEMPT_STATUSES]
    incomplete = [item for item in attempts if item.status == AttemptStatus.IN_PROGRESS]
    manual = sum(1 for attempt in attempts for answer in attempt.answers if answer.corrected_at is not None)
    unanswered = sum(
        1 for attempt in valid for answer in attempt.answers if not answer.answer_payload
    )
    assignments_without_questions = await session.scalar(
        select(func.count(MaterialAssignment.id)).where(
            MaterialAssignment.organization_id == organization_id,
            ~MaterialAssignment.questions.any(),
        )
    ) or 0
    notes: list[str] = []
    if incomplete:
        notes.append(f"{len(incomplete)} tentativa(s) incompleta(s) não entram nos indicadores de desempenho.")
    if unanswered:
        notes.append(f"{unanswered} resposta(s) vazia(s) foram consideradas omissões.")
    if assignments_without_questions:
        notes.append(f"{assignments_without_questions} publicação(ões) não possuem questões avaliáveis.")
    status = "good" if len(notes) <= 1 else "attention"
    return {
        "status": status,
        "valid_attempts": len(valid),
        "incomplete_attempts": len(incomplete),
        "manually_graded_answers": manual,
        "unanswered_items": unanswered,
        "assignments_with_no_questions": int(assignments_without_questions),
        "notes": notes,
    }


async def enrolled_student_ids(session: AsyncSession, classroom_id: UUID) -> list[UUID]:
    return list(
        (
            await session.scalars(
                select(ClassroomEnrollment.user_id).where(
                    ClassroomEnrollment.classroom_id == classroom_id,
                    ClassroomEnrollment.role == "student",
                )
            )
        ).all()
    )


async def student_user(session: AsyncSession, student_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == student_id))


async def classroom_or_none(
    session: AsyncSession, organization_id: UUID, classroom_id: UUID
) -> Classroom | None:
    return await session.scalar(
        select(Classroom).where(
            Classroom.id == classroom_id, Classroom.organization_id == organization_id
        )
    )


async def create_intervention(
    session: AsyncSession,
    *,
    organization_id: UUID,
    teacher_id: UUID,
    classroom_id: UUID | None,
    student_id: UUID | None,
    alert_id: UUID | None,
    assignment_id: UUID | None,
    intervention_type: Any,
    reason: str,
    notes: str,
    expected_outcome: str,
) -> LearningIntervention:
    intervention = LearningIntervention(
        organization_id=organization_id,
        teacher_id=teacher_id,
        classroom_id=classroom_id,
        student_id=student_id,
        alert_id=alert_id,
        assignment_id=assignment_id,
        intervention_type=intervention_type,
        reason=reason,
        notes=notes,
        expected_outcome=expected_outcome,
    )
    session.add(intervention)
    await session.flush()
    return intervention


def update_intervention_status(
    intervention: LearningIntervention,
    *,
    status: InterventionStatus | None,
    notes: str | None,
    expected_outcome: str | None,
    result_summary: str | None,
) -> None:
    if status is not None:
        intervention.status = status
        intervention.completed_at = utcnow() if status == InterventionStatus.COMPLETED else None
    if notes is not None:
        intervention.notes = notes
    if expected_outcome is not None:
        intervention.expected_outcome = expected_outcome
    if result_summary is not None:
        intervention.result_summary = result_summary

async def student_analytics(
    session: AsyncSession,
    *,
    organization_id: UUID,
    student_id: UUID,
    attempt_policy: str = "best",
) -> dict[str, Any] | None:
    user = await student_user(session, student_id)
    if user is None:
        return None
    attempts = select_attempts(
        await load_attempts(session, organization_id, student_id=student_id), attempt_policy
    )
    attempts = sorted(attempts, key=lambda item: item.submitted_at or item.started_at)
    average = sum(item.percentage for item in attempts) / len(attempts) if attempts else None
    average_time = sum(item.time_spent_seconds for item in attempts) / len(attempts) if attempts else None
    metrics = list(
        (
            await session.scalars(
                select(StudentSkillMetric).where(
                    StudentSkillMetric.organization_id == organization_id,
                    StudentSkillMetric.student_id == student_id,
                )
            )
        ).all()
    )
    skill_rows = [
        {
            "skill_code": metric.skill_code,
            "ct_pillar_code": metric.ct_pillar_code,
            "proficiency_score": metric.proficiency_score,
            "confidence_score": metric.confidence_score,
            "evidence_count": metric.evidence_count,
            "correct_count": metric.correct_count,
            "total_count": metric.total_count,
            "mastery_level": mastery_level(metric.proficiency_score, metric.evidence_count),
            "last_activity_at": metric.last_activity_at,
        }
        for metric in sorted(metrics, key=lambda item: (item.proficiency_score, item.skill_code, item.ct_pillar_code))
    ]
    recommendations: list[str] = []
    low = [row for row in skill_rows if row["evidence_count"] >= 3 and row["proficiency_score"] < 60]
    for row in low[:3]:
        dimension = row["skill_code"] or row["ct_pillar_code"]
        recommendations.append(f"Propor atividade de reforço em {dimension} com exemplos guiados.")
    if len(attempts) >= 2 and attempts[-1].percentage < attempts[0].percentage - 5:
        recommendations.append("Revisar a sequência recente e oferecer feedback individual antes da próxima atividade.")
    if not recommendations:
        recommendations.append("Manter desafios progressivos e registrar novas evidências de aprendizagem.")
    return {
        "student_id": student_id,
        "student_name": user.full_name,
        "student_email": user.email,
        "average_percentage": round(average, 2) if average is not None else None,
        "activities_completed": len({item.assignment_id for item in attempts}),
        "total_attempts": len(attempts),
        "average_time_seconds": round(average_time, 2) if average_time is not None else None,
        "trend": [
            {
                "label": (item.submitted_at or item.started_at).strftime("%d/%m"),
                "value": round(item.percentage, 2),
                "evidence_count": len(item.answers),
            }
            for item in attempts
        ],
        "skills": skill_rows,
        "activities": [
            {
                "assignment_id": item.assignment_id,
                "assignment_title": item.assignment.title,
                "attempt_number": item.attempt_number,
                "percentage": item.percentage,
                "score": item.score,
                "time_spent_seconds": item.time_spent_seconds,
                "submitted_at": item.submitted_at,
                "status": item.status.value,
            }
            for item in attempts
        ],
        "recommendations": recommendations,
    }


async def classroom_analytics(
    session: AsyncSession,
    *,
    organization_id: UUID,
    classroom_id: UUID,
    attempt_policy: str = "best",
) -> dict[str, Any] | None:
    classroom = await classroom_or_none(session, organization_id, classroom_id)
    if classroom is None:
        return None
    student_ids = await enrolled_student_ids(session, classroom_id)
    attempts = select_attempts(await load_attempts(session, organization_id), attempt_policy)
    attempts = [
        item for item in attempts
        if item.student_id in student_ids and classroom_id in _classrooms_for_attempt(item)
    ]
    percentages = [item.percentage for item in attempts]
    average = sum(percentages) / len(percentages) if percentages else None
    median_value = median(percentages) if percentages else None
    average_time = sum(item.time_spent_seconds for item in attempts) / len(attempts) if attempts else None
    assigned_count = await session.scalar(
        select(func.count(AssignmentRecipient.id)).where(
            AssignmentRecipient.classroom_id == classroom_id,
            AssignmentRecipient.status == RecipientStatus.ACTIVE,
        )
    ) or 0
    completed_pairs = {(item.assignment_id, item.student_id) for item in attempts}
    expected = int(assigned_count) * len(student_ids)
    completion = len(completed_pairs) / expected * 100 if expected else 0.0
    metrics = list(
        (
            await session.scalars(
                select(ClassroomSkillMetric).where(
                    ClassroomSkillMetric.organization_id == organization_id,
                    ClassroomSkillMetric.classroom_id == classroom_id,
                )
            )
        ).all()
    )
    skill_rows = [
        {
            "skill_code": metric.skill_code,
            "ct_pillar_code": metric.ct_pillar_code,
            "proficiency_score": metric.average_score,
            "confidence_score": confidence_score(metric.evidence_count),
            "evidence_count": metric.evidence_count,
            "correct_count": 0,
            "total_count": metric.evidence_count,
            "mastery_level": mastery_level(metric.average_score, metric.evidence_count),
            "last_activity_at": metric.calculated_at,
        }
        for metric in metrics
    ]
    users = {
        user.id: user
        for user in (
            await session.scalars(select(User).where(User.id.in_(student_ids)))
        ).all()
    } if student_ids else {}
    by_student: dict[UUID, list[StudentAttempt]] = defaultdict(list)
    for item in attempts:
        by_student[item.student_id].append(item)
    student_rows: list[dict[str, Any]] = []
    for student_id in student_ids:
        rows = sorted(by_student.get(student_id, []), key=lambda item: item.submitted_at or item.started_at)
        values = [item.percentage for item in rows]
        avg = sum(values) / len(values) if values else None
        attention = "priority" if avg is not None and avg < 40 else "attention" if avg is not None and avg < 60 else "normal"
        student_rows.append(
            {
                "student_id": student_id,
                "student_name": users.get(student_id).full_name if users.get(student_id) else "Estudante",
                "average_percentage": round(avg, 2) if avg is not None else None,
                "assignments_completed": len({item.assignment_id for item in rows}),
                "trend_direction": trend_direction(values),
                "attention_level": attention,
            }
        )
    assignment_groups: dict[UUID, list[float]] = defaultdict(list)
    labels: dict[UUID, str] = {}
    for item in attempts:
        assignment_groups[item.assignment_id].append(item.percentage)
        labels[item.assignment_id] = item.assignment.title
    return {
        "classroom_id": classroom_id,
        "classroom_name": classroom.name,
        "student_count": len(student_ids),
        "assignment_count": len(assignment_groups),
        "average_percentage": round(average, 2) if average is not None else None,
        "median_percentage": round(median_value, 2) if median_value is not None else None,
        "completion_rate": round(clamp(completion), 2),
        "average_time_seconds": round(average_time, 2) if average_time is not None else None,
        "skills": skill_rows,
        "students": sorted(student_rows, key=lambda item: (item["average_percentage"] is None, item["average_percentage"] or 0)),
        "trend": [
            {
                "label": labels[assignment_id][:28],
                "value": round(sum(values) / len(values), 2),
                "evidence_count": len(values),
            }
            for assignment_id, values in assignment_groups.items()
        ],
    }


def _distractor_rows(metric: AssignmentItemMetric, question: AssignmentQuestion) -> list[dict[str, Any]]:
    total = max(metric.response_count, 1)
    correct_values = {str(value) for value in question.answer_key.values() if value is not None}
    rows = []
    for answer, count in sorted(metric.distractor_distribution.items(), key=lambda item: item[1], reverse=True):
        rows.append(
            {
                "answer": answer,
                "count": count,
                "percentage": round(count / total * 100, 2),
                "is_correct_option": answer in correct_values,
            }
        )
    return rows


async def assignment_analytics(
    session: AsyncSession,
    *,
    organization_id: UUID,
    assignment_id: UUID,
    attempt_policy: str = "best",
) -> dict[str, Any] | None:
    assignment = await session.scalar(
        select(MaterialAssignment)
        .where(
            MaterialAssignment.id == assignment_id,
            MaterialAssignment.organization_id == organization_id,
        )
        .options(selectinload(MaterialAssignment.questions))
    )
    if assignment is None:
        return None
    attempts = select_attempts(
        await load_attempts(session, organization_id, assignment_id=assignment_id), attempt_policy
    )
    percentages = [item.percentage for item in attempts]
    average = sum(percentages) / len(percentages) if percentages else None
    median_value = median(percentages) if percentages else None
    average_time = sum(item.time_spent_seconds for item in attempts) / len(attempts) if attempts else None
    recipient_count = len(await resolved_students(session, assignment))
    completion = len({item.student_id for item in attempts}) / recipient_count * 100 if recipient_count else 0.0
    metric_by_question = {
        item.assignment_question_id: item
        for item in (
            await session.scalars(
                select(AssignmentItemMetric).where(
                    AssignmentItemMetric.organization_id == organization_id,
                    AssignmentItemMetric.assignment_id == assignment_id,
                )
            )
        ).all()
    }
    question_rows: list[dict[str, Any]] = []
    for question in sorted(assignment.questions, key=lambda item: item.position):
        metric = metric_by_question.get(question.id)
        response_count = metric.response_count if metric else 0
        correct_count = metric.correct_count if metric else 0
        index = metric.difficulty_index if metric else None
        question_rows.append(
            {
                "question_id": question.id,
                "assignment_id": assignment_id,
                "position": question.position,
                "prompt": question.prompt,
                "response_count": response_count,
                "correct_count": correct_count,
                "correct_rate": round(correct_count / response_count * 100, 2) if response_count else None,
                "difficulty_index": index,
                "difficulty_label": difficulty_label(index),
                "discrimination_index": metric.discrimination_index if metric else None,
                "average_response_time": metric.average_response_time if metric else None,
                "omission_rate": round(metric.omission_count / response_count * 100, 2) if metric and response_count else None,
                "average_awarded_score": metric.average_awarded_score if metric else None,
                "distractors": _distractor_rows(metric, question) if metric else [],
                "curriculum_skill_codes": question.curriculum_skill_codes,
                "ct_pillar_codes": question.ct_pillar_codes,
            }
        )
    by_date: dict[str, list[float]] = defaultdict(list)
    for item in attempts:
        label = (item.submitted_at or item.started_at).strftime("%d/%m")
        by_date[label].append(item.percentage)
    notes: list[str] = []
    incomplete = [item for item in await load_attempts(session, organization_id, assignment_id=assignment_id) if item.status == AttemptStatus.IN_PROGRESS]
    if incomplete:
        notes.append(f"{len(incomplete)} tentativa(s) em andamento foram excluídas do desempenho.")
    if not assignment.questions:
        notes.append("A publicação não possui questões avaliáveis.")
    return {
        "assignment_id": assignment_id,
        "assignment_title": assignment.title,
        "participant_count": recipient_count,
        "attempt_count": len(attempts),
        "completion_rate": round(clamp(completion), 2),
        "average_percentage": round(average, 2) if average is not None else None,
        "median_percentage": round(median_value, 2) if median_value is not None else None,
        "average_time_seconds": round(average_time, 2) if average_time is not None else None,
        "questions": question_rows,
        "trend": [
            {"label": label, "value": round(sum(values) / len(values), 2), "evidence_count": len(values)}
            for label, values in by_date.items()
        ],
        "data_quality_notes": notes,
    }


async def resolved_students(
    session: AsyncSession, assignment: MaterialAssignment
) -> list[UUID]:
    result: set[UUID] = set()
    recipients = list(
        (
            await session.scalars(
                select(AssignmentRecipient).where(
                    AssignmentRecipient.assignment_id == assignment.id,
                    AssignmentRecipient.status == RecipientStatus.ACTIVE,
                )
            )
        ).all()
    )
    for recipient in recipients:
        if recipient.recipient_type == RecipientType.USER and recipient.user_id is not None:
            result.add(recipient.user_id)
        elif recipient.recipient_type == RecipientType.CLASSROOM and recipient.classroom_id is not None:
            result.update(await enrolled_student_ids(session, recipient.classroom_id))
    return list(result)


async def own_progress(
    session: AsyncSession, organization_id: UUID, student_id: UUID
) -> dict[str, Any]:
    data = await student_analytics(
        session,
        organization_id=organization_id,
        student_id=student_id,
        attempt_policy="latest",
    )
    if data is None:
        return {
            "student_id": student_id,
            "average_percentage": None,
            "completed_activities": 0,
            "trend": [],
            "strengths": [],
            "development_areas": [],
            "next_steps": ["Conclua sua primeira atividade para acompanhar o progresso."],
        }
    skills = data["skills"]
    strengths = [item for item in skills if item["evidence_count"] >= 2 and item["proficiency_score"] >= 70]
    development = [item for item in skills if item["evidence_count"] >= 2 and item["proficiency_score"] < 60]
    next_steps = [
        f"Pratique {item['skill_code'] or item['ct_pillar_code']} com uma atividade curta."
        for item in development[:3]
    ] or ["Continue avançando com atividades progressivas."]
    return {
        "student_id": student_id,
        "average_percentage": data["average_percentage"],
        "completed_activities": data["activities_completed"],
        "trend": data["trend"],
        "strengths": strengths[:5],
        "development_areas": development[:5],
        "next_steps": next_steps,
    }
