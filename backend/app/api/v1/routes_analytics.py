from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.analytics import (
    AlertStatus,
    AnalyticsRefreshJob,
    StudentSkillMetric,
    InterventionStatus,
    LearningAlert,
    LearningIntervention,
)
from app.models.auth import Membership, OrganizationRole, User
from app.schemas.analytics import (
    AlertUpdateRequest,
    AnalyticsRefreshRead,
    AnalyticsRefreshRequest,
    AssignmentAnalyticsRead,
    ClassroomAnalyticsRead,
    DashboardSummary,
    DataQualityRead,
    InterventionCreate,
    InterventionRead,
    InterventionUpdate,
    LearningAlertRead,
    StudentAnalyticsRead,
    StudentOwnProgressRead,
)
from app.services.analytics import (
    assignment_analytics,
    classroom_analytics,
    create_intervention,
    dashboard_summary,
    data_quality,
    own_progress,
    refresh_analytics,
    student_analytics,
    update_intervention_status,
)

router = APIRouter(prefix="/analytics", tags=["Learning Analytics"])

TEACHER_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
ALL_ROLES = (*TEACHER_ROLES, OrganizationRole.MEMBER)
AttemptPolicy = Literal["first", "latest", "best", "all"]


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


@router.post("/refresh", response_model=AnalyticsRefreshRead, status_code=201)
async def refresh_metrics(
    data: AnalyticsRefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AnalyticsRefreshJob:
    job = await refresh_analytics(
        session,
        organization_id=org_id(membership),
        requested_by_user_id=user.id,
        request=data,
    )
    await session.commit()
    await session.refresh(job)
    return job


@router.get("/refresh-jobs", response_model=list[AnalyticsRefreshRead])
async def list_refresh_jobs(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AnalyticsRefreshJob]:
    return list(
        (
            await session.scalars(
                select(AnalyticsRefreshJob)
                .where(AnalyticsRefreshJob.organization_id == org_id(membership))
                .order_by(AnalyticsRefreshJob.created_at.desc())
                .limit(20)
            )
        ).all()
    )


@router.get("/dashboard", response_model=DashboardSummary)
async def analytics_dashboard(
    attempt_policy: AttemptPolicy = Query(default="best"),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> DashboardSummary:
    return DashboardSummary.model_validate(
        await dashboard_summary(session, org_id(membership), attempt_policy)
    )


@router.get("/data-quality", response_model=DataQualityRead)
async def analytics_data_quality(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> DataQualityRead:
    return DataQualityRead.model_validate(await data_quality(session, org_id(membership)))


@router.get("/classrooms/{classroom_id}", response_model=ClassroomAnalyticsRead)
async def classroom_metrics(
    classroom_id: UUID,
    attempt_policy: AttemptPolicy = Query(default="best"),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> ClassroomAnalyticsRead:
    result = await classroom_analytics(
        session,
        organization_id=org_id(membership),
        classroom_id=classroom_id,
        attempt_policy=attempt_policy,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    return ClassroomAnalyticsRead.model_validate(result)


@router.get("/students/{student_id}", response_model=StudentAnalyticsRead)
async def student_metrics(
    student_id: UUID,
    attempt_policy: AttemptPolicy = Query(default="best"),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> StudentAnalyticsRead:
    result = await student_analytics(
        session,
        organization_id=org_id(membership),
        student_id=student_id,
        attempt_policy=attempt_policy,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Estudante não encontrado")
    return StudentAnalyticsRead.model_validate(result)


@router.get("/assignments/{assignment_id}", response_model=AssignmentAnalyticsRead)
async def assignment_metrics(
    assignment_id: UUID,
    attempt_policy: AttemptPolicy = Query(default="best"),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AssignmentAnalyticsRead:
    result = await assignment_analytics(
        session,
        organization_id=org_id(membership),
        assignment_id=assignment_id,
        attempt_policy=attempt_policy,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Publicação não encontrada")
    return AssignmentAnalyticsRead.model_validate(result)


@router.get("/alerts", response_model=list[LearningAlertRead])
async def list_alerts(
    status: AlertStatus | None = Query(default=None),
    severity: str | None = Query(default=None),
    classroom_id: UUID | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[LearningAlert]:
    statement = select(LearningAlert).where(
        LearningAlert.organization_id == org_id(membership)
    )
    if status is not None:
        statement = statement.where(LearningAlert.status == status)
    if severity is not None:
        statement = statement.where(LearningAlert.severity == severity)
    if classroom_id is not None:
        statement = statement.where(LearningAlert.classroom_id == classroom_id)
    if student_id is not None:
        statement = statement.where(LearningAlert.student_id == student_id)
    return list(
        (
            await session.scalars(statement.order_by(LearningAlert.created_at.desc()).limit(300))
        ).all()
    )


@router.patch("/alerts/{alert_id}", response_model=LearningAlertRead)
async def update_alert(
    alert_id: UUID,
    data: AlertUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> LearningAlert:
    alert = await session.scalar(
        select(LearningAlert).where(
            LearningAlert.id == alert_id,
            LearningAlert.organization_id == org_id(membership),
        )
    )
    if alert is None:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    alert.status = data.status
    alert.resolved_at = (
        datetime.now(UTC)
        if data.status in {AlertStatus.RESOLVED, AlertStatus.DISMISSED}
        else None
    )
    await session.commit()
    await session.refresh(alert)
    return alert


@router.get("/interventions", response_model=list[InterventionRead])
async def list_interventions(
    status: InterventionStatus | None = Query(default=None),
    student_id: UUID | None = Query(default=None),
    classroom_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[LearningIntervention]:
    statement = select(LearningIntervention).where(
        LearningIntervention.organization_id == org_id(membership)
    )
    if status is not None:
        statement = statement.where(LearningIntervention.status == status)
    if student_id is not None:
        statement = statement.where(LearningIntervention.student_id == student_id)
    if classroom_id is not None:
        statement = statement.where(LearningIntervention.classroom_id == classroom_id)
    return list(
        (
            await session.scalars(
                statement.order_by(LearningIntervention.created_at.desc()).limit(300)
            )
        ).all()
    )


@router.post("/interventions", response_model=InterventionRead, status_code=201)
async def add_intervention(
    data: InterventionCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> LearningIntervention:
    intervention = await create_intervention(
        session,
        organization_id=org_id(membership),
        teacher_id=user.id,
        classroom_id=data.classroom_id,
        student_id=data.student_id,
        alert_id=data.alert_id,
        assignment_id=data.assignment_id,
        intervention_type=data.intervention_type,
        reason=data.reason,
        notes=data.notes,
        expected_outcome=data.expected_outcome,
    )
    await session.commit()
    await session.refresh(intervention)
    return intervention


@router.patch("/interventions/{intervention_id}", response_model=InterventionRead)
async def edit_intervention(
    intervention_id: UUID,
    data: InterventionUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> LearningIntervention:
    intervention = await session.scalar(
        select(LearningIntervention).where(
            LearningIntervention.id == intervention_id,
            LearningIntervention.organization_id == org_id(membership),
        )
    )
    if intervention is None:
        raise HTTPException(status_code=404, detail="Intervenção não encontrada")
    update_intervention_status(
        intervention,
        status=data.status,
        notes=data.notes,
        expected_outcome=data.expected_outcome,
        result_summary=data.result_summary,
    )
    await session.commit()
    await session.refresh(intervention)
    return intervention


@router.get("/exports/student-metrics.csv")
async def export_student_metrics(
    anonymized: bool = Query(default=True),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> StreamingResponse:
    rows = list(
        (
            await session.scalars(
                select(StudentSkillMetric).where(
                    StudentSkillMetric.organization_id == org_id(membership)
                )
            )
        ).all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "student", "skill_code", "ct_pillar_code", "proficiency_score",
        "confidence_score", "evidence_count", "correct_count", "total_count",
        "last_activity_at", "calculated_at",
    ])
    anonymous_codes: dict[UUID, str] = {}
    for row in rows:
        if row.student_id not in anonymous_codes:
            anonymous_codes[row.student_id] = f"EST-{len(anonymous_codes) + 1:04d}"
        student = anonymous_codes[row.student_id] if anonymized else str(row.student_id)
        writer.writerow([
            student, row.skill_code, row.ct_pillar_code, row.proficiency_score,
            row.confidence_score, row.evidence_count, row.correct_count, row.total_count,
            row.last_activity_at.isoformat() if row.last_activity_at else "",
            row.calculated_at.isoformat(),
        ])
    content = buffer.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=educode-analytics.csv"},
    )


@router.get("/student/progress", response_model=StudentOwnProgressRead)
async def my_progress(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ALL_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentOwnProgressRead:
    result = await own_progress(session, org_id(membership), user.id)
    return StudentOwnProgressRead.model_validate(result)
