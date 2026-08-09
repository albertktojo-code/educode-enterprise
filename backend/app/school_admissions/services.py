from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext
from app.models.auth import Membership, OrganizationRole, User
from app.models.delivery import UserNotification
from app.models.education import Classroom, ClassroomEnrollment
from app.school_admissions.models import (
    ApplicationStatus,
    ClassCapacity,
    EnrollmentStatus,
    EnrollmentWaitlist,
    GuardianProfile,
    ReservationStatus,
    SchoolUnit,
    SeatReservation,
    StudentEnrollment,
    StudentEnrollmentApplication,
    StudentGuardianLink,
    StudentProfile,
    WaitlistStatus,
)
from app.school_admissions.schemas import (
    CapacitySnapshot,
    EnrollmentApplicationCreate,
    EnrollmentApplicationRead,
)
from app.services.platform import append_audit_event


async def school_unit_or_404(
    session: AsyncSession, organization_id: UUID, unit_id: UUID
) -> SchoolUnit:
    unit = await session.scalar(
        select(SchoolUnit).where(
            SchoolUnit.id == unit_id,
            SchoolUnit.organization_id == organization_id,
            SchoolUnit.is_active.is_(True),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade escolar não encontrada")
    return unit


async def classroom_or_404(
    session: AsyncSession,
    organization_id: UUID,
    classroom_id: UUID,
    school_unit_id: UUID | None = None,
) -> Classroom:
    statement = select(Classroom).where(
        Classroom.id == classroom_id,
        Classroom.organization_id == organization_id,
        Classroom.is_active.is_(True),
    )
    if school_unit_id is not None:
        statement = statement.where(Classroom.school_unit_id == school_unit_id)
    classroom = await session.scalar(statement)
    if classroom is None:
        raise HTTPException(status_code=404, detail="Turma ativa não encontrada na unidade")
    return classroom


async def _expire_reservations(
    session: AsyncSession, organization_id: UUID, classroom_id: UUID, now: datetime
) -> None:
    await session.execute(
        update(SeatReservation)
        .where(
            SeatReservation.organization_id == organization_id,
            SeatReservation.classroom_id == classroom_id,
            SeatReservation.status == ReservationStatus.ACTIVE,
            SeatReservation.expires_at <= now,
        )
        .values(status=ReservationStatus.EXPIRED, updated_at=now)
    )


async def capacity_snapshot(
    session: AsyncSession,
    organization_id: UUID,
    classroom_id: UUID,
    *,
    lock: bool = False,
) -> CapacitySnapshot:
    statement = select(ClassCapacity).where(
        ClassCapacity.organization_id == organization_id,
        ClassCapacity.classroom_id == classroom_id,
    )
    if lock:
        statement = statement.with_for_update()
    capacity = await session.scalar(statement)
    if capacity is None:
        raise HTTPException(status_code=422, detail="Capacidade da turma não configurada")
    classroom = await classroom_or_404(session, organization_id, classroom_id)
    now = datetime.now(UTC)
    if lock:
        await _expire_reservations(session, organization_id, classroom_id, now)
    occupied = int(
        await session.scalar(
            select(func.count(StudentEnrollment.id)).where(
                StudentEnrollment.organization_id == organization_id,
                StudentEnrollment.classroom_id == classroom_id,
                StudentEnrollment.status.in_(
                    (EnrollmentStatus.ACTIVE, EnrollmentStatus.PENDING_IDENTITY)
                ),
            )
        )
        or 0
    )
    reserved = int(
        await session.scalar(
            select(func.count(SeatReservation.id)).where(
                SeatReservation.organization_id == organization_id,
                SeatReservation.classroom_id == classroom_id,
                SeatReservation.status == ReservationStatus.ACTIVE,
                SeatReservation.expires_at > now,
            )
        )
        or 0
    )
    waitlist = int(
        await session.scalar(
            select(func.count(EnrollmentWaitlist.id)).where(
                EnrollmentWaitlist.organization_id == organization_id,
                EnrollmentWaitlist.classroom_id == classroom_id,
                EnrollmentWaitlist.status.in_((WaitlistStatus.WAITING, WaitlistStatus.OFFERED)),
            )
        )
        or 0
    )
    return CapacitySnapshot(
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        maximum_seats=capacity.maximum_seats,
        occupied_seats=occupied,
        reserved_seats=reserved,
        available_seats=max(capacity.maximum_seats - occupied - reserved, 0),
        waitlist_size=waitlist,
        reservation_duration_minutes=capacity.reservation_duration_minutes,
        waitlist_enabled=capacity.waitlist_enabled,
    )


async def _validate_student_user(
    session: AsyncSession, organization_id: UUID, user_id: UUID | None
) -> None:
    if user_id is None:
        return
    valid = await session.scalar(
        select(Membership.id)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
            Membership.role == OrganizationRole.MEMBER,
            Membership.is_active.is_(True),
            User.is_active.is_(True),
        )
    )
    if valid is None:
        raise HTTPException(status_code=422, detail="Identidade do estudante é inválida")


async def create_application(
    session: AsyncSession,
    actor: ActorContext,
    data: EnrollmentApplicationCreate,
) -> StudentEnrollmentApplication:
    unit = await school_unit_or_404(session, actor.organization_id, data.school_unit_id)
    await classroom_or_404(session, actor.organization_id, data.classroom_id, data.school_unit_id)
    await _validate_student_user(session, actor.organization_id, data.student.user_id)
    student = StudentProfile(
        organization_id=actor.organization_id,
        **data.student.model_dump(mode="python"),
    )
    session.add(student)
    await session.flush()
    for guardian_data in data.guardians:
        email = str(guardian_data.email).casefold()
        guardian = await session.scalar(
            select(GuardianProfile).where(
                GuardianProfile.organization_id == actor.organization_id,
                func.lower(GuardianProfile.email) == email,
            )
        )
        if guardian is None:
            guardian = GuardianProfile(
                organization_id=actor.organization_id,
                full_name=guardian_data.full_name.strip(),
                email=email,
                phone=guardian_data.phone.strip(),
                address=guardian_data.address,
            )
            session.add(guardian)
            await session.flush()
        session.add(
            StudentGuardianLink(
                organization_id=actor.organization_id,
                student_profile_id=student.id,
                guardian_profile_id=guardian.id,
                relationship=guardian_data.relationship.strip(),
                roles=list(guardian_data.roles),
                pickup_authorized=guardian_data.pickup_authorized,
                emergency_contact=guardian_data.emergency_contact,
            )
        )
    application = StudentEnrollmentApplication(
        organization_id=actor.organization_id,
        school_unit_id=unit.id,
        classroom_id=data.classroom_id,
        student_profile_id=student.id,
        submitted_by_user_id=actor.user_id,
        academic_year=data.academic_year,
        intended_grade=data.intended_grade.strip(),
        intended_shift=data.intended_shift.strip(),
        status=ApplicationStatus.SUBMITTED,
        administrative_notes=data.administrative_notes.strip(),
    )
    session.add(application)
    await session.flush()
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment.application.created",
        entity_type="student_enrollment_application",
        entity_id=application.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"school_unit_id": str(unit.id), "classroom_id": str(data.classroom_id)},
    )
    await session.commit()
    await session.refresh(application)
    return application


async def application_or_404(
    session: AsyncSession, organization_id: UUID, application_id: UUID
) -> StudentEnrollmentApplication:
    application = await session.scalar(
        select(StudentEnrollmentApplication).where(
            StudentEnrollmentApplication.id == application_id,
            StudentEnrollmentApplication.organization_id == organization_id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")
    return application


async def application_read(
    session: AsyncSession, application: StudentEnrollmentApplication
) -> EnrollmentApplicationRead:
    student = await session.scalar(
        select(StudentProfile).where(
            StudentProfile.id == application.student_profile_id,
            StudentProfile.organization_id == application.organization_id,
        )
    )
    unit = await session.scalar(
        select(SchoolUnit).where(
            SchoolUnit.id == application.school_unit_id,
            SchoolUnit.organization_id == application.organization_id,
        )
    )
    classroom = await session.scalar(
        select(Classroom).where(
            Classroom.id == application.classroom_id,
            Classroom.organization_id == application.organization_id,
        )
    )
    if student is None or unit is None or classroom is None:
        raise HTTPException(status_code=409, detail="Vínculos da matrícula estão inconsistentes")
    return EnrollmentApplicationRead(
        id=application.id,
        student_profile_id=student.id,
        student_name=student.social_name or student.legal_name,
        school_unit_id=unit.id,
        school_unit_name=unit.name,
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        academic_year=application.academic_year,
        intended_grade=application.intended_grade,
        intended_shift=application.intended_shift,
        status=application.status,
        submitted_at=application.submitted_at,
    )


async def reserve_or_waitlist(
    session: AsyncSession, actor: ActorContext, application: StudentEnrollmentApplication
) -> tuple[str, datetime | None, int | None, CapacitySnapshot]:
    if application.status in (
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.CANCELLED,
    ):
        raise HTTPException(status_code=409, detail="Estado da matrícula não permite reserva")
    existing_reservation = await session.scalar(
        select(SeatReservation).where(SeatReservation.application_id == application.id)
    )
    now = datetime.now(UTC)
    if existing_reservation and existing_reservation.status == ReservationStatus.ACTIVE:
        snapshot = await capacity_snapshot(
            session, actor.organization_id, application.classroom_id, lock=True
        )
        await session.commit()
        return "already_reserved", existing_reservation.expires_at, None, snapshot
    existing_waitlist = await session.scalar(
        select(EnrollmentWaitlist).where(EnrollmentWaitlist.application_id == application.id)
    )
    if existing_waitlist and existing_waitlist.status in (
        WaitlistStatus.WAITING,
        WaitlistStatus.OFFERED,
    ):
        snapshot = await capacity_snapshot(
            session, actor.organization_id, application.classroom_id, lock=True
        )
        await session.commit()
        return "already_waitlisted", None, existing_waitlist.position, snapshot

    snapshot = await capacity_snapshot(
        session, actor.organization_id, application.classroom_id, lock=True
    )
    capacity = await session.scalar(
        select(ClassCapacity).where(ClassCapacity.classroom_id == application.classroom_id)
    )
    if capacity is None:
        raise HTTPException(status_code=422, detail="Capacidade da turma não configurada")
    if snapshot.available_seats > 0:
        expires_at = now + timedelta(minutes=capacity.reservation_duration_minutes)
        reservation = existing_reservation or SeatReservation(
            organization_id=actor.organization_id,
            application_id=application.id,
            classroom_id=application.classroom_id,
            expires_at=expires_at,
        )
        reservation.status = ReservationStatus.ACTIVE
        reservation.expires_at = expires_at
        session.add(reservation)
        outcome = "reserved"
        position = None
        audit_action = "seat.reserved"
    else:
        if not capacity.waitlist_enabled:
            raise HTTPException(status_code=409, detail="Turma sem vagas e fila desabilitada")
        position = (
            int(
                await session.scalar(
                    select(func.coalesce(func.max(EnrollmentWaitlist.position), 0)).where(
                        EnrollmentWaitlist.organization_id == actor.organization_id,
                        EnrollmentWaitlist.classroom_id == application.classroom_id,
                        EnrollmentWaitlist.status.in_(
                            (WaitlistStatus.WAITING, WaitlistStatus.OFFERED)
                        ),
                    )
                )
                or 0
            )
            + 1
        )
        waitlist = existing_waitlist or EnrollmentWaitlist(
            organization_id=actor.organization_id,
            application_id=application.id,
            classroom_id=application.classroom_id,
            position=position,
        )
        waitlist.position = position
        waitlist.status = WaitlistStatus.WAITING
        session.add(waitlist)
        application.status = ApplicationStatus.WAITLISTED
        expires_at = None
        outcome = "waitlisted"
        audit_action = "waitlist.joined"
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action=audit_action,
        entity_type="student_enrollment_application",
        entity_id=application.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"classroom_id": str(application.classroom_id), "position": position},
    )
    await session.commit()
    refreshed = await capacity_snapshot(session, actor.organization_id, application.classroom_id)
    return outcome, expires_at, position, refreshed


async def approve_application(
    session: AsyncSession, actor: ActorContext, application: StudentEnrollmentApplication
) -> tuple[StudentEnrollment, bool]:
    existing = await session.scalar(
        select(StudentEnrollment).where(StudentEnrollment.application_id == application.id)
    )
    if existing is not None:
        return existing, False
    if application.status in (ApplicationStatus.REJECTED, ApplicationStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Matrícula rejeitada ou cancelada")
    snapshot = await capacity_snapshot(
        session, actor.organization_id, application.classroom_id, lock=True
    )
    reservation = await session.scalar(
        select(SeatReservation).where(SeatReservation.application_id == application.id)
    )
    has_active_reservation = bool(
        reservation
        and reservation.status == ReservationStatus.ACTIVE
        and reservation.expires_at > datetime.now(UTC)
    )
    if not has_active_reservation and snapshot.available_seats <= 0:
        raise HTTPException(status_code=409, detail="Não há vaga disponível para aprovação")
    student = await session.scalar(
        select(StudentProfile).where(
            StudentProfile.id == application.student_profile_id,
            StudentProfile.organization_id == actor.organization_id,
        )
    )
    if student is None:
        raise HTTPException(status_code=409, detail="Perfil do estudante não encontrado")
    enrollment = StudentEnrollment(
        organization_id=actor.organization_id,
        application_id=application.id,
        student_profile_id=student.id,
        classroom_id=application.classroom_id,
        approved_by_user_id=actor.user_id,
        status=(EnrollmentStatus.ACTIVE if student.user_id else EnrollmentStatus.PENDING_IDENTITY),
    )
    session.add(enrollment)
    classroom_participant_created = False
    if student.user_id:
        participant = await session.scalar(
            select(ClassroomEnrollment).where(
                ClassroomEnrollment.classroom_id == application.classroom_id,
                ClassroomEnrollment.user_id == student.user_id,
            )
        )
        if participant is None:
            session.add(
                ClassroomEnrollment(
                    classroom_id=application.classroom_id,
                    user_id=student.user_id,
                    role="student",
                )
            )
            classroom_participant_created = True
        session.add(
            UserNotification(
                organization_id=actor.organization_id,
                user_id=student.user_id,
                notification_type="enrollment_approved",
                title="Matrícula aprovada",
                message="Sua matrícula foi aprovada pela Secretaria.",
                action_path="/aluno",
            )
        )
    if reservation and reservation.status == ReservationStatus.ACTIVE:
        reservation.status = ReservationStatus.CONVERTED
    waitlist = await session.scalar(
        select(EnrollmentWaitlist).where(EnrollmentWaitlist.application_id == application.id)
    )
    if waitlist:
        waitlist.status = WaitlistStatus.ACCEPTED
    application.status = ApplicationStatus.APPROVED
    application.reviewed_by_user_id = actor.user_id
    application.reviewed_at = datetime.now(UTC)
    await session.flush()
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="enrollment.application.approved",
        entity_type="student_enrollment",
        entity_id=enrollment.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={
            "application_id": str(application.id),
            "classroom_id": str(application.classroom_id),
            "identity_pending": student.user_id is None,
        },
    )
    await session.commit()
    await session.refresh(enrollment)
    return enrollment, classroom_participant_created
