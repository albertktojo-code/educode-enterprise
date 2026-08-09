from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext, resolve_actor_context
from app.db.session import get_db_session
from app.models.education import Classroom, ClassroomEnrollment
from app.school_admissions.models import (
    ApplicationStatus,
    EnrollmentMovementStatus,
    EnrollmentRenewalRequest,
    EnrollmentStatus,
    EnrollmentTransferRequest,
    EnrollmentTransferType,
    SchoolUnit,
    StudentEnrollment,
    StudentEnrollmentApplication,
    StudentProfile,
)
from app.school_admissions.policies import ensure_admissions_staff
from app.school_admissions.schemas import (
    ActiveEnrollmentRead,
    EnrollmentMovementReview,
    EnrollmentMovementsDashboard,
    EnrollmentRenewalCreate,
    EnrollmentRenewalRead,
    EnrollmentTransferCreate,
    EnrollmentTransferRead,
)
from app.school_admissions.services import approve_application, classroom_or_404
from app.services.platform import append_audit_event

router = APIRouter(prefix="/school-admissions", tags=["Movimentações de matrícula"])


async def _enrollment_or_404(
    session: AsyncSession, organization_id: UUID, enrollment_id: UUID, *, lock: bool = False
) -> StudentEnrollment:
    statement = select(StudentEnrollment).where(
        StudentEnrollment.id == enrollment_id,
        StudentEnrollment.organization_id == organization_id,
    )
    if lock:
        statement = statement.with_for_update()
    enrollment = await session.scalar(statement)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Matrícula ativa não encontrada")
    if enrollment.status not in (EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING_IDENTITY):
        raise HTTPException(status_code=409, detail="O vínculo não permite movimentação")
    return enrollment


async def _movement_context(session: AsyncSession, enrollment: StudentEnrollment):
    student = await session.get(StudentProfile, enrollment.student_profile_id)
    classroom = await session.get(Classroom, enrollment.classroom_id)
    application = await session.get(StudentEnrollmentApplication, enrollment.application_id)
    if student is None or classroom is None or application is None:
        raise HTTPException(status_code=409, detail="Vínculo escolar inconsistente")
    return student, classroom, application


async def _active_enrollment_read(
    session: AsyncSession, enrollment: StudentEnrollment
) -> ActiveEnrollmentRead:
    student, classroom, application = await _movement_context(session, enrollment)
    unit = await session.get(SchoolUnit, application.school_unit_id)
    if unit is None:
        raise HTTPException(status_code=409, detail="Unidade escolar inconsistente")
    return ActiveEnrollmentRead(
        id=enrollment.id,
        student_profile_id=student.id,
        student_name=student.social_name or student.legal_name,
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        school_unit_id=unit.id,
        school_unit_name=unit.name,
        academic_year=application.academic_year,
        status=enrollment.status,
    )


async def _renewal_read(
    session: AsyncSession, item: EnrollmentRenewalRequest
) -> EnrollmentRenewalRead:
    enrollment = await session.get(StudentEnrollment, item.enrollment_id)
    target = await session.get(Classroom, item.target_classroom_id)
    if enrollment is None or target is None:
        raise HTTPException(status_code=409, detail="Rematrícula inconsistente")
    student, source, _ = await _movement_context(session, enrollment)
    return EnrollmentRenewalRead(
        id=item.id,
        enrollment_id=item.enrollment_id,
        student_name=student.social_name or student.legal_name,
        source_classroom_name=source.name,
        target_classroom_id=target.id,
        target_classroom_name=target.name,
        target_academic_year=item.target_academic_year,
        status=item.status,
        reason=item.reason,
        review_note=item.review_note,
        result_application_id=item.result_application_id,
        created_at=item.created_at,
    )


async def _transfer_read(
    session: AsyncSession, item: EnrollmentTransferRequest
) -> EnrollmentTransferRead:
    enrollment = await session.get(StudentEnrollment, item.enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=409, detail="Transferência inconsistente")
    student, source, _ = await _movement_context(session, enrollment)
    destination = (
        await session.get(Classroom, item.destination_classroom_id)
        if item.destination_classroom_id
        else None
    )
    return EnrollmentTransferRead(
        id=item.id,
        enrollment_id=item.enrollment_id,
        student_name=student.social_name or student.legal_name,
        source_classroom_name=source.name,
        transfer_type=item.transfer_type,
        destination_classroom_id=item.destination_classroom_id,
        destination_name=destination.name if destination else item.destination_name,
        status=item.status,
        reason=item.reason,
        review_note=item.review_note,
        result_application_id=item.result_application_id,
        created_at=item.created_at,
    )


async def _new_application(
    session: AsyncSession,
    actor: ActorContext,
    enrollment: StudentEnrollment,
    target: Classroom,
    academic_year: int,
    note: str,
) -> StudentEnrollmentApplication:
    if target.school_unit_id is None:
        raise HTTPException(status_code=422, detail="Turma de destino sem unidade escolar")
    application = StudentEnrollmentApplication(
        organization_id=actor.organization_id,
        school_unit_id=target.school_unit_id,
        classroom_id=target.id,
        student_profile_id=enrollment.student_profile_id,
        submitted_by_user_id=actor.user_id,
        academic_year=academic_year,
        intended_grade=target.grade or target.name,
        intended_shift=target.shift or "not_informed",
        status=ApplicationStatus.SUBMITTED,
        administrative_notes=note,
    )
    session.add(application)
    await session.flush()
    return application


async def _audit(
    session: AsyncSession,
    actor: ActorContext,
    action: str,
    entity_type: str,
    entity_id: UUID,
    details: dict[str, str],
) -> None:
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details=details,
    )


@router.get("/movements", response_model=EnrollmentMovementsDashboard)
async def movements_dashboard(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentMovementsDashboard:
    await ensure_admissions_staff(session, actor)
    enrollments = list(
        (
            await session.scalars(
                select(StudentEnrollment)
                .where(
                    StudentEnrollment.organization_id == actor.organization_id,
                    StudentEnrollment.status.in_(
                        (EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING_IDENTITY)
                    ),
                )
                .order_by(StudentEnrollment.enrolled_at.desc())
            )
        ).all()
    )
    renewals = list(
        (
            await session.scalars(
                select(EnrollmentRenewalRequest)
                .where(EnrollmentRenewalRequest.organization_id == actor.organization_id)
                .order_by(EnrollmentRenewalRequest.created_at.desc())
            )
        ).all()
    )
    transfers = list(
        (
            await session.scalars(
                select(EnrollmentTransferRequest)
                .where(EnrollmentTransferRequest.organization_id == actor.organization_id)
                .order_by(EnrollmentTransferRequest.created_at.desc())
            )
        ).all()
    )
    return EnrollmentMovementsDashboard(
        enrollments=[await _active_enrollment_read(session, item) for item in enrollments],
        renewals=[await _renewal_read(session, item) for item in renewals],
        transfers=[await _transfer_read(session, item) for item in transfers],
    )


@router.post(
    "/enrollments/{enrollment_id}/renewals", response_model=EnrollmentRenewalRead, status_code=201
)
async def create_renewal(
    enrollment_id: UUID,
    data: EnrollmentRenewalCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentRenewalRead:
    enrollment = await _enrollment_or_404(session, actor.organization_id, enrollment_id)
    _, _, source_application = await _movement_context(session, enrollment)
    await ensure_admissions_staff(session, actor, source_application.school_unit_id)
    target = await classroom_or_404(session, actor.organization_id, data.target_classroom_id)
    if target.school_unit_id is None:
        raise HTTPException(status_code=422, detail="Turma de destino sem unidade escolar")
    await ensure_admissions_staff(session, actor, target.school_unit_id)
    duplicate = await session.scalar(
        select(EnrollmentRenewalRequest.id).where(
            EnrollmentRenewalRequest.enrollment_id == enrollment.id,
            EnrollmentRenewalRequest.target_academic_year == data.target_academic_year,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Rematrícula já solicitada para este ano")
    item = EnrollmentRenewalRequest(
        organization_id=actor.organization_id,
        enrollment_id=enrollment.id,
        target_classroom_id=target.id,
        target_academic_year=data.target_academic_year,
        reason=data.reason.strip(),
        requested_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.flush()
    await _audit(
        session,
        actor,
        "enrollment.renewal.requested",
        "enrollment_renewal_request",
        item.id,
        {"enrollment_id": str(enrollment.id)},
    )
    await session.commit()
    await session.refresh(item)
    return await _renewal_read(session, item)


@router.post("/renewals/{request_id}/review", response_model=EnrollmentRenewalRead)
async def review_renewal(
    request_id: UUID,
    data: EnrollmentMovementReview,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentRenewalRead:
    item = await session.scalar(
        select(EnrollmentRenewalRequest)
        .where(
            EnrollmentRenewalRequest.id == request_id,
            EnrollmentRenewalRequest.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Rematrícula não encontrada")
    enrollment = await _enrollment_or_404(session, actor.organization_id, item.enrollment_id)
    target = await classroom_or_404(session, actor.organization_id, item.target_classroom_id)
    await ensure_admissions_staff(session, actor, target.school_unit_id)
    if item.status != EnrollmentMovementStatus.SUBMITTED:
        raise HTTPException(status_code=409, detail="Rematrícula já analisada")
    if data.decision == "approved":
        application = await _new_application(
            session, actor, enrollment, target, item.target_academic_year, "Rematrícula"
        )
        item.result_application_id = application.id
        await approve_application(session, actor, application, commit=False)
    item.status = data.decision
    item.review_note = data.note.strip()
    item.reviewed_by_user_id = actor.user_id
    item.reviewed_at = datetime.now(UTC)
    await _audit(
        session,
        actor,
        f"enrollment.renewal.{data.decision}",
        "enrollment_renewal_request",
        item.id,
        {"enrollment_id": str(enrollment.id)},
    )
    await session.commit()
    await session.refresh(item)
    return await _renewal_read(session, item)


@router.post(
    "/enrollments/{enrollment_id}/transfers", response_model=EnrollmentTransferRead, status_code=201
)
async def create_transfer(
    enrollment_id: UUID,
    data: EnrollmentTransferCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentTransferRead:
    enrollment = await _enrollment_or_404(session, actor.organization_id, enrollment_id)
    _, _, source_application = await _movement_context(session, enrollment)
    await ensure_admissions_staff(session, actor, source_application.school_unit_id)
    if data.destination_classroom_id:
        target = await classroom_or_404(
            session, actor.organization_id, data.destination_classroom_id
        )
        await ensure_admissions_staff(session, actor, target.school_unit_id)
        if target.id == enrollment.classroom_id:
            raise HTTPException(status_code=422, detail="A turma de destino deve ser diferente")
    pending = await session.scalar(
        select(EnrollmentTransferRequest.id).where(
            EnrollmentTransferRequest.enrollment_id == enrollment.id,
            EnrollmentTransferRequest.status == EnrollmentMovementStatus.SUBMITTED,
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="Já existe transferência pendente")
    item = EnrollmentTransferRequest(
        organization_id=actor.organization_id,
        enrollment_id=enrollment.id,
        transfer_type=data.transfer_type,
        destination_classroom_id=data.destination_classroom_id,
        destination_name=data.destination_name.strip(),
        reason=data.reason.strip(),
        requested_by_user_id=actor.user_id,
    )
    session.add(item)
    await session.flush()
    await _audit(
        session,
        actor,
        "enrollment.transfer.requested",
        "enrollment_transfer_request",
        item.id,
        {"enrollment_id": str(enrollment.id), "type": data.transfer_type},
    )
    await session.commit()
    await session.refresh(item)
    return await _transfer_read(session, item)


@router.post("/transfers/{request_id}/review", response_model=EnrollmentTransferRead)
async def review_transfer(
    request_id: UUID,
    data: EnrollmentMovementReview,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentTransferRead:
    item = await session.scalar(
        select(EnrollmentTransferRequest)
        .where(
            EnrollmentTransferRequest.id == request_id,
            EnrollmentTransferRequest.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Transferência não encontrada")
    enrollment = await _enrollment_or_404(
        session, actor.organization_id, item.enrollment_id, lock=True
    )
    student, _, source_application = await _movement_context(session, enrollment)
    await ensure_admissions_staff(session, actor, source_application.school_unit_id)
    if item.status != EnrollmentMovementStatus.SUBMITTED:
        raise HTTPException(status_code=409, detail="Transferência já analisada")
    if data.decision == "approved":
        if item.transfer_type == EnrollmentTransferType.INTERNAL:
            target = await classroom_or_404(
                session, actor.organization_id, item.destination_classroom_id
            )
            await ensure_admissions_staff(session, actor, target.school_unit_id)
            application = await _new_application(
                session,
                actor,
                enrollment,
                target,
                target.school_year or datetime.now(UTC).year,
                "Transferência interna",
            )
            item.result_application_id = application.id
            await approve_application(session, actor, application, commit=False)
        enrollment.status = EnrollmentStatus.TRANSFERRED
        enrollment.ended_at = datetime.now(UTC)
        if student.user_id:
            await session.execute(
                delete(ClassroomEnrollment).where(
                    ClassroomEnrollment.classroom_id == enrollment.classroom_id,
                    ClassroomEnrollment.user_id == student.user_id,
                )
            )
    item.status = data.decision
    item.review_note = data.note.strip()
    item.reviewed_by_user_id = actor.user_id
    item.reviewed_at = datetime.now(UTC)
    await _audit(
        session,
        actor,
        f"enrollment.transfer.{data.decision}",
        "enrollment_transfer_request",
        item.id,
        {"enrollment_id": str(enrollment.id), "type": item.transfer_type},
    )
    await session.commit()
    await session.refresh(item)
    return await _transfer_read(session, item)
