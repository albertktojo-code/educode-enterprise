from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.delivery import (
    AssignmentQuestion,
    AssignmentRecipient,
    AssignmentStatus,
    AttemptStatus,
    MaterialAssignment,
    NotificationStatus,
    RecipientStatus,
    StudentAttempt,
    UserNotification,
)
from app.models.education import Classroom, ClassroomEnrollment
from app.schemas.delivery import (
    AnswerSaveRequest,
    AnswerSaveResponse,
    AssignmentCreate,
    AssignmentDuplicateRequest,
    AssignmentProgress,
    AssignmentSummaryRead,
    AssignmentTeacherRead,
    AssignmentUpdate,
    AttemptRead,
    AttemptResult,
    AttemptResultAnswer,
    AttemptStartRequest,
    AttemptSubmitRequest,
    AttemptWorkspace,
    ClassroomAnnouncementCreate,
    ClassroomAnnouncementResult,
    GradingQueueItem,
    GrantExtraAttemptRequest,
    LearningEventCreate,
    ManualGradeRequest,
    NotificationRead,
    QuestionInput,
    RecipientInput,
    RecipientRead,
    RecipientUpdate,
    StudentAssignmentCard,
    StudentAssignmentDetail,
    StudentPreview,
    StudentQuestionRead,
)
from app.services.delivery import (
    DeliveryError,
    answer_key_available,
    assignment_progress,
    create_assignment,
    create_learning_event,
    create_or_resume_attempt,
    duplicate_assignment,
    effective_student_settings,
    get_assignment,
    grade_response,
    grading_queue,
    grant_extra_attempt,
    list_student_assignments,
    load_attempt,
    manual_grade_answer,
    ordered_student_questions,
    publish_assignment,
    reopen_attempt,
    results_available,
    save_answer,
    student_assignment_detail,
    student_material_snapshot,
    submit_attempt,
)
from app.services.platform import append_audit_event

router = APIRouter(tags=["Publicação e aprendizagem"])

TEACHER_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
STUDENT_ROLES = (OrganizationRole.MEMBER,)
READ_ROLES = (*TEACHER_ROLES, OrganizationRole.MEMBER)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def delivery_http_error(exc: DeliveryError) -> HTTPException:
    message = str(exc)
    status = 409 if "desatualizado" in message.casefold() else 422
    return HTTPException(status_code=status, detail=message)


@router.post(
    "/connect/announcements",
    response_model=ClassroomAnnouncementResult,
    status_code=201,
)
async def create_classroom_announcement(
    data: ClassroomAnnouncementCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> ClassroomAnnouncementResult:
    organization_id = org_id(membership)
    classroom_ids = list(dict.fromkeys(data.classroom_ids))
    valid_classrooms = set(
        (
            await session.scalars(
                select(Classroom.id).where(
                    Classroom.id.in_(classroom_ids),
                    Classroom.organization_id == organization_id,
                    Classroom.is_active.is_(True),
                )
            )
        ).all()
    )
    if len(valid_classrooms) != len(classroom_ids):
        raise HTTPException(status_code=422, detail="Uma ou mais turmas são inválidas.")

    student_ids = list(
        dict.fromkeys(
            (
                await session.scalars(
                    select(ClassroomEnrollment.user_id)
                    .join(Classroom, Classroom.id == ClassroomEnrollment.classroom_id)
                    .join(User, User.id == ClassroomEnrollment.user_id)
                    .join(Membership, Membership.user_id == User.id)
                    .where(
                        ClassroomEnrollment.classroom_id.in_(classroom_ids),
                        ClassroomEnrollment.role == "student",
                        Classroom.organization_id == organization_id,
                        User.is_active.is_(True),
                        Membership.organization_id == organization_id,
                        Membership.role == OrganizationRole.MEMBER,
                        Membership.is_active.is_(True),
                    )
                )
            ).all()
        )
    )
    for student_id in student_ids:
        session.add(
            UserNotification(
                organization_id=organization_id,
                user_id=student_id,
                notification_type="classroom_announcement",
                title=data.title.strip(),
                message=data.message.strip(),
                action_path=data.action_path,
            )
        )
    await append_audit_event(
        session,
        organization_id=organization_id,
        user_id=user.id,
        module_name="connect",
        action="announcement.sent",
        entity_type="user_notification",
        details={
            "classroom_ids": [str(item) for item in classroom_ids],
            "recipients": len(student_ids),
            "title": data.title.strip(),
        },
    )
    await session.commit()
    return ClassroomAnnouncementResult(classrooms=len(classroom_ids), recipients=len(student_ids))


async def assignment_or_404(
    session: AsyncSession, membership: Membership, assignment_id: UUID
) -> MaterialAssignment:
    assignment = await get_assignment(session, org_id(membership), assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Publicação não encontrada")
    return assignment


@router.get("/delivery/assignments", response_model=list[AssignmentSummaryRead])
async def list_assignments(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[MaterialAssignment]:
    result = await session.scalars(
        select(MaterialAssignment)
        .where(MaterialAssignment.organization_id == org_id(membership))
        .order_by(MaterialAssignment.updated_at.desc())
    )
    return list(result.all())


@router.post("/delivery/assignments", response_model=AssignmentTeacherRead, status_code=201)
async def create_delivery_assignment(
    data: AssignmentCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> MaterialAssignment:
    try:
        assignment = await create_assignment(
            session,
            organization_id=org_id(membership),
            user_id=user.id,
            user_name=user.full_name,
            data=data,
        )
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.get("/delivery/assignments/{assignment_id}", response_model=AssignmentTeacherRead)
async def read_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    return await assignment_or_404(session, membership, assignment_id)


@router.patch("/delivery/assignments/{assignment_id}", response_model=AssignmentTeacherRead)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    values = data.model_dump(exclude_unset=True)
    if assignment.status not in {AssignmentStatus.DRAFT, AssignmentStatus.SCHEDULED}:
        immutable_fields = {
            "maximum_score",
            "randomize_questions",
            "randomize_options",
        }
        if immutable_fields.intersection(values):
            raise HTTPException(
                status_code=409,
                detail="A estrutura avaliativa publicada é imutável; duplique a publicação.",
            )
    for field, value in values.items():
        setattr(assignment, field, value)
    if (
        assignment.available_from
        and assignment.due_at
        and assignment.due_at <= assignment.available_from
    ):
        raise HTTPException(status_code=422, detail="O prazo deve ser posterior à liberação")
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.post(
    "/delivery/assignments/{assignment_id}/recipients",
    response_model=RecipientRead,
    status_code=201,
)
async def add_assignment_recipient(
    assignment_id: UUID,
    data: RecipientInput,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AssignmentRecipient:
    from app.services.delivery import _validate_recipient

    assignment = await assignment_or_404(session, membership, assignment_id)
    if assignment.status not in {AssignmentStatus.DRAFT, AssignmentStatus.SCHEDULED}:
        raise HTTPException(
            status_code=409,
            detail="Não é possível alterar o público após a publicação",
        )
    try:
        await _validate_recipient(session, org_id(membership), data)
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    recipient = AssignmentRecipient(
        assignment_id=assignment.id,
        recipient_type=data.recipient_type,
        classroom_id=data.classroom_id,
        user_id=data.user_id,
        available_from_override=data.available_from_override,
        due_at_override=data.due_at_override,
        maximum_attempts_override=data.maximum_attempts_override,
        time_limit_minutes_override=data.time_limit_minutes_override,
        accommodations=data.accommodations,
    )
    session.add(recipient)
    await session.commit()
    await session.refresh(recipient)
    return recipient


@router.patch("/delivery/recipients/{recipient_id}", response_model=RecipientRead)
async def update_assignment_recipient(
    recipient_id: UUID,
    data: RecipientUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AssignmentRecipient:
    recipient = await session.scalar(
        select(AssignmentRecipient)
        .join(MaterialAssignment, MaterialAssignment.id == AssignmentRecipient.assignment_id)
        .where(
            AssignmentRecipient.id == recipient_id,
            MaterialAssignment.organization_id == org_id(membership),
        )
    )
    if recipient is None:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(recipient, field, value)
    await session.commit()
    await session.refresh(recipient)
    return recipient


@router.delete("/delivery/recipients/{recipient_id}", status_code=204)
async def remove_assignment_recipient(
    recipient_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> Response:
    recipient = await session.scalar(
        select(AssignmentRecipient)
        .join(MaterialAssignment, MaterialAssignment.id == AssignmentRecipient.assignment_id)
        .where(
            AssignmentRecipient.id == recipient_id,
            MaterialAssignment.organization_id == org_id(membership),
        )
    )
    if recipient is None:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado")
    recipient.status = RecipientStatus.REMOVED
    await session.commit()
    return Response(status_code=204)


@router.post(
    "/delivery/assignments/{assignment_id}/questions",
    response_model=AssignmentTeacherRead,
    status_code=201,
)
async def add_assignment_question(
    assignment_id: UUID,
    data: QuestionInput,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    if assignment.status != AssignmentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Questões só podem ser alteradas no rascunho")
    position = len(assignment.questions) + 1
    assignment.questions.append(
        AssignmentQuestion(
            position=position,
            question_type=data.question_type,
            prompt=data.prompt,
            options=data.options,
            answer_key=data.answer_key,
            explanation=data.explanation,
            points=data.points,
            difficulty=data.difficulty,
            curriculum_skill_codes=data.curriculum_skill_codes,
            ct_pillar_codes=data.ct_pillar_codes,
            source_references=data.source_references,
            manual_grading=data.manual_grading,
            shuffle_options=data.shuffle_options,
        )
    )
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.post("/delivery/assignments/{assignment_id}/publish", response_model=AssignmentTeacherRead)
async def publish_delivery_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    try:
        await publish_assignment(session, assignment)
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.post(
    "/delivery/assignments/{assignment_id}/duplicate",
    response_model=AssignmentTeacherRead,
    status_code=201,
)
async def duplicate_delivery_assignment(
    assignment_id: UUID,
    data: AssignmentDuplicateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    clone = await duplicate_assignment(
        session,
        assignment=assignment,
        user_id=user.id,
        user_name=user.full_name,
        title=data.title,
        copy_recipients=data.copy_recipients,
    )
    await session.commit()
    return await assignment_or_404(session, membership, clone.id)


@router.post("/delivery/assignments/{assignment_id}/cancel", response_model=AssignmentTeacherRead)
async def cancel_delivery_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    assignment.status = AssignmentStatus.CANCELED
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.post("/delivery/assignments/{assignment_id}/close", response_model=AssignmentTeacherRead)
async def close_delivery_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    assignment.status = AssignmentStatus.CLOSED
    assignment.closed_at = datetime.now(UTC)
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.post(
    "/delivery/assignments/{assignment_id}/release-results",
    response_model=AssignmentTeacherRead,
)
async def release_assignment_results(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> MaterialAssignment:
    assignment = await assignment_or_404(session, membership, assignment_id)
    assignment.results_released_at = datetime.now(UTC)
    attempts = list(
        (
            await session.scalars(
                select(StudentAttempt).where(StudentAttempt.assignment_id == assignment.id)
            )
        ).all()
    )
    for attempt in attempts:
        if attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.GRADED}:
            session.add(
                UserNotification(
                    organization_id=assignment.organization_id,
                    user_id=attempt.student_id,
                    assignment_id=assignment.id,
                    notification_type="results_released",
                    title="Resultados liberados",
                    message=f"Os resultados de {assignment.title} estão disponíveis.",
                    action_path=f"/aluno/atividades/{assignment.id}",
                )
            )
    await session.commit()
    return await assignment_or_404(session, membership, assignment.id)


@router.post(
    "/delivery/assignments/{assignment_id}/students/{student_id}/grant-attempt",
    response_model=RecipientRead,
)
async def grant_student_attempt(
    assignment_id: UUID,
    student_id: UUID,
    data: GrantExtraAttemptRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AssignmentRecipient:
    assignment = await assignment_or_404(session, membership, assignment_id)
    try:
        recipient = await grant_extra_attempt(
            session,
            assignment=assignment,
            student_id=student_id,
            additional_attempts=data.additional_attempts,
            due_at_override=data.due_at_override,
            reason=data.reason,
        )
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    await session.refresh(recipient)
    return recipient


@router.get("/delivery/assignments/{assignment_id}/progress", response_model=AssignmentProgress)
async def read_assignment_progress(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AssignmentProgress:
    assignment = await assignment_or_404(session, membership, assignment_id)
    return await assignment_progress(session, assignment)


@router.get(
    "/delivery/assignments/{assignment_id}/grading-queue",
    response_model=list[GradingQueueItem],
)
async def read_grading_queue(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[GradingQueueItem]:
    assignment = await assignment_or_404(session, membership, assignment_id)
    return await grading_queue(session, assignment)


@router.patch("/delivery/answers/{answer_id}/grade", response_model=AttemptRead)
async def grade_manual_answer(
    answer_id: UUID,
    data: ManualGradeRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentAttempt:
    try:
        answer = await manual_grade_answer(
            session,
            organization_id=org_id(membership),
            answer_id=answer_id,
            awarded_score=data.awarded_score,
            is_correct=data.is_correct,
            feedback=data.teacher_feedback,
            grader_id=user.id,
        )
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    attempt = await load_attempt(session, org_id(membership), answer.attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    return attempt


@router.post("/delivery/attempts/{attempt_id}/reopen", response_model=AttemptRead)
async def reopen_student_attempt(
    attempt_id: UUID,
    reason: str = "Nova oportunidade concedida pelo professor",
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentAttempt:
    attempt = await load_attempt(session, org_id(membership), attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    try:
        await reopen_attempt(session, attempt, user.id, reason)
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    refreshed = await load_attempt(session, org_id(membership), attempt.id)
    return refreshed or attempt


@router.get("/delivery/assignments/{assignment_id}/preview", response_model=StudentPreview)
async def preview_assignment_as_student(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> StudentPreview:
    assignment = await assignment_or_404(session, membership, assignment_id)
    detail = StudentAssignmentDetail(
        id=assignment.id,
        title=assignment.title,
        instructions=assignment.instructions,
        assignment_type=assignment.assignment_type,
        available_from=assignment.available_from,
        due_at=assignment.due_at,
        time_limit_minutes=assignment.time_limit_minutes,
        maximum_attempts=assignment.maximum_attempts,
        attempts_used=0,
        maximum_score=assignment.maximum_score,
        material=student_material_snapshot(assignment.material_snapshot),
        progress_status="preview",
        can_start=False,
        active_attempt_id=None,
        accommodations={},
    )
    questions = [
        StudentQuestionRead(
            id=question.id,
            position=question.position,
            question_type=question.question_type,
            prompt=question.prompt,
            options=question.options,
            points=question.points,
            difficulty=question.difficulty,
            curriculum_skill_codes=question.curriculum_skill_codes,
            ct_pillar_codes=question.ct_pillar_codes,
        )
        for question in assignment.questions
    ]
    return StudentPreview(assignment=detail, questions=questions)


@router.get("/student/assignments", response_model=list[StudentAssignmentCard])
async def student_assignments(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    return await list_student_assignments(session, org_id(membership), user.id)


@router.get("/student/assignments/{assignment_id}", response_model=StudentAssignmentDetail)
async def read_student_assignment(
    assignment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    assignment = await assignment_or_404(session, membership, assignment_id)
    try:
        return await student_assignment_detail(session, assignment, user.id)
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc


@router.post(
    "/student/assignments/{assignment_id}/attempts",
    response_model=AttemptWorkspace,
    status_code=201,
)
async def start_student_attempt(
    assignment_id: UUID,
    _: AttemptStartRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> AttemptWorkspace:
    assignment = await assignment_or_404(session, membership, assignment_id)
    try:
        attempt = await create_or_resume_attempt(session, assignment, user.id)
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    refreshed = await load_attempt(session, org_id(membership), attempt.id, user.id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    return AttemptWorkspace(
        attempt=AttemptRead.model_validate(refreshed),
        questions=[
            StudentQuestionRead.model_validate(item)
            for item in ordered_student_questions(assignment, refreshed)
        ],
        material=student_material_snapshot(assignment.material_snapshot),
        feedback_policy=assignment.feedback_policy,
        answer_key_policy=assignment.answer_key_policy,
    )


@router.get("/student/attempts/{attempt_id}", response_model=AttemptWorkspace)
async def read_student_attempt(
    attempt_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> AttemptWorkspace:
    attempt = await load_attempt(session, org_id(membership), attempt_id, user.id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    return AttemptWorkspace(
        attempt=AttemptRead.model_validate(attempt),
        questions=[
            StudentQuestionRead.model_validate(item)
            for item in ordered_student_questions(attempt.assignment, attempt)
        ],
        material=student_material_snapshot(attempt.assignment.material_snapshot),
        feedback_policy=attempt.assignment.feedback_policy,
        answer_key_policy=attempt.assignment.answer_key_policy,
    )


@router.put(
    "/student/attempts/{attempt_id}/answers/{question_id}",
    response_model=AnswerSaveResponse,
)
async def save_student_answer(
    attempt_id: UUID,
    question_id: UUID,
    data: AnswerSaveRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> AnswerSaveResponse:
    attempt = await load_attempt(session, org_id(membership), attempt_id, user.id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    try:
        answer, outcome, immediate = await save_answer(
            session,
            attempt=attempt,
            question_id=question_id,
            answer_payload=data.answer_payload,
            response_time_seconds=data.response_time_seconds,
            expected_revision=data.expected_revision,
        )
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    await session.refresh(answer)
    return AnswerSaveResponse(
        answer=answer,
        autosave_revision=attempt.autosave_revision,
        feedback_available=immediate and outcome.is_correct is not None,
        is_correct=outcome.is_correct if immediate else None,
        feedback=outcome.feedback if immediate else None,
    )


@router.post("/student/attempts/{attempt_id}/submit", response_model=AttemptRead)
async def submit_student_attempt(
    attempt_id: UUID,
    data: AttemptSubmitRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentAttempt:
    attempt = await load_attempt(session, org_id(membership), attempt_id, user.id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    try:
        await submit_attempt(session, attempt, data.time_spent_seconds)
    except DeliveryError as exc:
        raise delivery_http_error(exc) from exc
    await session.commit()
    refreshed = await load_attempt(session, org_id(membership), attempt.id, user.id)
    return refreshed or attempt


@router.get("/student/attempts/{attempt_id}/result", response_model=AttemptResult)
async def read_attempt_result(
    attempt_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> AttemptResult:
    attempt = await load_attempt(session, org_id(membership), attempt_id, user.id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Tentativa não encontrada")
    now = datetime.now(UTC)
    effective = await effective_student_settings(session, attempt.assignment, user.id)
    if effective is None:
        raise HTTPException(status_code=403, detail="Acesso à atividade removido")
    effective_due = effective["due_at"]
    can_result = results_available(attempt.assignment, attempt, now, effective_due)
    can_key = answer_key_available(attempt.assignment, attempt, now, effective_due)
    answers_by_question = {answer.question_id: answer for answer in attempt.answers}
    result_answers: list[AttemptResultAnswer] = []
    if can_result:
        for question in attempt.assignment.questions:
            answer = answers_by_question.get(question.id)
            if answer is None:
                continue
            feedback = answer.teacher_feedback
            if feedback is None and answer.is_correct is not None:
                outcome = grade_response(
                    question.question_type,
                    answer.answer_payload,
                    question.answer_key,
                    question.points,
                )
                feedback = outcome.feedback
            result_answers.append(
                AttemptResultAnswer(
                    question_id=question.id,
                    prompt=question.prompt,
                    answer_payload=answer.answer_payload,
                    awarded_score=answer.awarded_score,
                    is_correct=answer.is_correct,
                    feedback=feedback,
                    correct_answer=question.answer_key if can_key else None,
                    explanation=question.explanation if can_key else None,
                )
            )
    return AttemptResult(
        attempt_id=attempt.id,
        status=attempt.status,
        score=attempt.score if can_result else 0.0,
        percentage=attempt.percentage if can_result else 0.0,
        maximum_score=attempt.assignment.maximum_score,
        grading_complete=attempt.grading_complete,
        result_available=can_result,
        answer_key_available=can_key,
        teacher_feedback=attempt.teacher_feedback if can_result else None,
        answers=result_answers,
    )


@router.post("/student/assignments/{assignment_id}/events", status_code=201)
async def register_learning_event(
    assignment_id: UUID,
    data: LearningEventCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*STUDENT_ROLES)),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    assignment = await assignment_or_404(session, membership, assignment_id)
    effective = await effective_student_settings(session, assignment, user.id)
    if effective is None:
        raise HTTPException(status_code=403, detail="Atividade não atribuída ao estudante")
    if data.attempt_id is not None:
        event_attempt = await load_attempt(session, org_id(membership), data.attempt_id, user.id)
        if event_attempt is None or event_attempt.assignment_id != assignment.id:
            raise HTTPException(status_code=422, detail="Tentativa inválida para este evento")
    if data.question_id is not None and not any(
        question.id == data.question_id for question in assignment.questions
    ):
        raise HTTPException(status_code=422, detail="Questão inválida para este evento")
    await create_learning_event(
        session,
        organization_id=org_id(membership),
        student_id=user.id,
        assignment_id=assignment.id,
        event_type=data.event_type,
        attempt_id=data.attempt_id,
        question_id=data.question_id,
        page_number=data.page_number,
        metadata=data.metadata,
    )
    await session.commit()
    return {"status": "registered"}


@router.get("/student/notifications", response_model=list[NotificationRead])
async def list_student_notifications(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
    user: User = Depends(get_current_user),
) -> list[UserNotification]:
    result = await session.scalars(
        select(UserNotification)
        .where(
            UserNotification.organization_id == org_id(membership),
            UserNotification.user_id == user.id,
            UserNotification.status != NotificationStatus.ARCHIVED,
        )
        .order_by(UserNotification.created_at.desc())
        .limit(100)
    )
    return list(result.all())


@router.patch("/student/notifications/read-all")
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    notifications = list(
        (
            await session.scalars(
                select(UserNotification).where(
                    UserNotification.organization_id == org_id(membership),
                    UserNotification.user_id == user.id,
                    UserNotification.status == NotificationStatus.UNREAD,
                )
            )
        ).all()
    )
    read_at = datetime.now(UTC)
    for notification in notifications:
        notification.status = NotificationStatus.READ
        notification.read_at = read_at
    await session.commit()
    return {"updated": len(notifications)}


@router.patch("/student/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
    user: User = Depends(get_current_user),
) -> UserNotification:
    notification = await session.scalar(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.organization_id == org_id(membership),
            UserNotification.user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    notification.status = NotificationStatus.READ
    notification.read_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(notification)
    return notification
