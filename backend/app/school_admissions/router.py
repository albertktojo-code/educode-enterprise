from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.actor_context import ActorContext, resolve_actor_context
from app.db.session import get_db_session
from app.school_admissions.models import (
    ApplicationStatus,
    ClassCapacity,
    SchoolUnit,
    StudentEnrollmentApplication,
)
from app.school_admissions.policies import ensure_admissions_staff
from app.school_admissions.schemas import (
    AdmissionsDashboard,
    CapacitySnapshot,
    CapacityWrite,
    EnrollmentApplicationCreate,
    EnrollmentApplicationRead,
    EnrollmentApprovalRead,
    SchoolUnitCreate,
    SchoolUnitRead,
    SeatDecisionRead,
)
from app.school_admissions.services import (
    application_or_404,
    application_read,
    approve_application,
    capacity_snapshot,
    classroom_or_404,
    create_application,
    reserve_or_waitlist,
    school_unit_or_404,
)
from app.services.platform import append_audit_event

router = APIRouter(prefix="/school-admissions", tags=["Secretaria e matrículas"])


@router.get("/units", response_model=list[SchoolUnitRead])
async def list_school_units(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[SchoolUnit]:
    await ensure_admissions_staff(session, actor)
    return list(
        (
            await session.scalars(
                select(SchoolUnit)
                .where(SchoolUnit.organization_id == actor.organization_id)
                .order_by(SchoolUnit.name)
            )
        ).all()
    )


@router.post("/units", response_model=SchoolUnitRead, status_code=201)
async def create_school_unit(
    data: SchoolUnitCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> SchoolUnit:
    await ensure_admissions_staff(session, actor)
    if not actor.has_any_role("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Somente a administração cria unidades")
    duplicate = await session.scalar(
        select(SchoolUnit.id).where(
            SchoolUnit.organization_id == actor.organization_id,
            func.lower(SchoolUnit.code) == data.code.casefold(),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Código de unidade já utilizado")
    unit = SchoolUnit(
        organization_id=actor.organization_id,
        name=data.name.strip(),
        code=data.code.strip().upper(),
        address=data.address,
    )
    session.add(unit)
    await session.flush()
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="school_unit.created",
        entity_type="school_unit",
        entity_id=unit.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details={"code": unit.code},
    )
    await session.commit()
    await session.refresh(unit)
    return unit


@router.put("/classrooms/{classroom_id}/capacity", response_model=CapacitySnapshot)
async def configure_capacity(
    classroom_id: UUID,
    data: CapacityWrite,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> CapacitySnapshot:
    classroom = await classroom_or_404(session, actor.organization_id, classroom_id)
    await ensure_admissions_staff(session, actor, classroom.school_unit_id)
    capacity = await session.scalar(
        select(ClassCapacity).where(
            ClassCapacity.organization_id == actor.organization_id,
            ClassCapacity.classroom_id == classroom.id,
        )
    )
    if capacity is None:
        capacity = ClassCapacity(
            organization_id=actor.organization_id,
            classroom_id=classroom.id,
            updated_by_user_id=actor.user_id,
            **data.model_dump(),
        )
        session.add(capacity)
    else:
        for field, value in data.model_dump().items():
            setattr(capacity, field, value)
        capacity.updated_by_user_id = actor.user_id
    await append_audit_event(
        session,
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        module_name="school_admissions",
        action="class_capacity.updated",
        entity_type="classroom",
        entity_id=classroom.id,
        request_id=actor.request_id,
        ip_address=actor.ip_address,
        details=data.model_dump(),
    )
    await session.commit()
    return await capacity_snapshot(session, actor.organization_id, classroom.id)


@router.get("/classrooms/{classroom_id}/capacity", response_model=CapacitySnapshot)
async def get_capacity(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> CapacitySnapshot:
    classroom = await classroom_or_404(session, actor.organization_id, classroom_id)
    await ensure_admissions_staff(session, actor, classroom.school_unit_id)
    return await capacity_snapshot(session, actor.organization_id, classroom.id)


@router.post("/applications", response_model=EnrollmentApplicationRead, status_code=201)
async def submit_application(
    data: EnrollmentApplicationCreate,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentApplicationRead:
    await school_unit_or_404(session, actor.organization_id, data.school_unit_id)
    await ensure_admissions_staff(session, actor, data.school_unit_id)
    application = await create_application(session, actor, data)
    return await application_read(session, application)


@router.get("/applications", response_model=list[EnrollmentApplicationRead])
async def list_applications(
    status: ApplicationStatus | None = None,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> list[EnrollmentApplicationRead]:
    await ensure_admissions_staff(session, actor)
    statement = select(StudentEnrollmentApplication).where(
        StudentEnrollmentApplication.organization_id == actor.organization_id
    )
    if status:
        statement = statement.where(StudentEnrollmentApplication.status == status)
    applications = (
        await session.scalars(statement.order_by(StudentEnrollmentApplication.created_at.desc()))
    ).all()
    return [await application_read(session, item) for item in applications]


@router.post(
    "/applications/{application_id}/reserve",
    response_model=SeatDecisionRead,
)
async def reserve_application_seat(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> SeatDecisionRead:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    outcome, expires_at, position, capacity = await reserve_or_waitlist(session, actor, application)
    return SeatDecisionRead(
        application_id=application.id,
        outcome=outcome,
        capacity=capacity,
        reservation_expires_at=expires_at,
        waitlist_position=position,
    )


@router.post(
    "/applications/{application_id}/approve",
    response_model=EnrollmentApprovalRead,
)
async def approve_enrollment_application(
    application_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> EnrollmentApprovalRead:
    application = await application_or_404(session, actor.organization_id, application_id)
    await ensure_admissions_staff(session, actor, application.school_unit_id)
    enrollment, participant_created = await approve_application(session, actor, application)
    return EnrollmentApprovalRead(
        application_id=application.id,
        enrollment_id=enrollment.id,
        status=enrollment.status,
        classroom_participant_created=participant_created,
    )


@router.get("/dashboard", response_model=AdmissionsDashboard)
async def admissions_dashboard(
    session: AsyncSession = Depends(get_db_session),
    actor: ActorContext = Depends(resolve_actor_context),
) -> AdmissionsDashboard:
    await ensure_admissions_staff(session, actor)
    applications = list(
        (
            await session.scalars(
                select(StudentEnrollmentApplication)
                .where(StudentEnrollmentApplication.organization_id == actor.organization_id)
                .order_by(StudentEnrollmentApplication.created_at.desc())
                .limit(50)
            )
        ).all()
    )
    capacities = list(
        (
            await session.scalars(
                select(ClassCapacity).where(ClassCapacity.organization_id == actor.organization_id)
            )
        ).all()
    )
    counts = dict(
        (
            await session.execute(
                select(
                    StudentEnrollmentApplication.status,
                    func.count(StudentEnrollmentApplication.id),
                )
                .where(StudentEnrollmentApplication.organization_id == actor.organization_id)
                .group_by(StudentEnrollmentApplication.status)
            )
        ).all()
    )
    return AdmissionsDashboard(
        applications=[await application_read(session, item) for item in applications],
        capacities=[
            await capacity_snapshot(session, actor.organization_id, item.classroom_id)
            for item in capacities
        ],
        submitted=int(counts.get(ApplicationStatus.SUBMITTED, 0)),
        under_review=int(counts.get(ApplicationStatus.UNDER_REVIEW, 0)),
        waitlisted=int(counts.get(ApplicationStatus.WAITLISTED, 0)),
        approved=int(counts.get(ApplicationStatus.APPROVED, 0)),
    )
