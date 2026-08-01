from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.adaptive import (
    AdaptiveGroupMember,
    AdaptiveLearningPath,
    AdaptiveLearningProfile,
    AdaptiveModelVersion,
    AdaptivePathStep,
    AdaptiveRecommendation,
    AdaptiveReviewSchedule,
    AdaptiveSkillState,
    AdaptiveStudentGroup,
    SkillPrerequisite,
)
from app.models.auth import Membership, OrganizationRole, User
from app.schemas.adaptive import (
    AdaptiveDashboardRead,
    AdaptiveModelCreate,
    AdaptiveModelRead,
    AdaptiveProfileRead,
    AdaptiveProfileUpdate,
    AdaptiveRefreshRead,
    AdaptiveRefreshRequest,
    AdaptiveStudentListItem,
    GroupMemberUpdate,
    LearningPathCreate,
    LearningPathRead,
    PathOutcomeRead,
    PathStatusUpdate,
    PathStepComplete,
    PathStepRead,
    PrerequisiteCreate,
    PrerequisiteRead,
    RecommendationGenerateRequest,
    RecommendationRead,
    RecommendationReview,
    ReviewComplete,
    ReviewScheduleRead,
    SkillStateRead,
    StudentAdaptiveSummary,
    StudentGroupCreate,
    StudentGroupRead,
    StudentOwnPathRead,
)
from app.services.adaptive import (
    activate_path,
    approve_recommendation_as_path,
    audit,
    calculate_path_outcome,
    classroom_student_ids,
    complete_step,
    create_group,
    create_path,
    create_recommendations_for_states,
    ensure_default_model,
    ensure_profile,
    load_path_with_steps,
    path_student_ids,
    refresh_student_states,
    schedule_reviews_for_path,
    validate_student_membership,
)

router = APIRouter(prefix="/adaptive", tags=["Aprendizagem Adaptativa"])

TEACHER_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)
ALL_ROLES = (*TEACHER_ROLES, OrganizationRole.MEMBER)


def org_id(membership: Membership) -> UUID:
    return membership.organization_id


def path_payload(path: AdaptiveLearningPath, steps: list[AdaptivePathStep]) -> LearningPathRead:
    return LearningPathRead.model_validate(
        {
            **{column.name: getattr(path, column.name) for column in path.__table__.columns},
            "steps": [PathStepRead.model_validate(item) for item in steps],
        }
    )




async def student_can_access_path(
    session: AsyncSession,
    *,
    path: AdaptiveLearningPath,
    student_id: UUID,
) -> bool:
    if path.student_id == student_id:
        return True
    if path.group_id is not None:
        member = await session.scalar(
            select(AdaptiveGroupMember.id).where(
                AdaptiveGroupMember.group_id == path.group_id,
                AdaptiveGroupMember.student_id == student_id,
                AdaptiveGroupMember.removed_at.is_(None),
            )
        )
        if member is not None:
            return True
    if path.classroom_id is not None:
        from app.models.education import ClassroomEnrollment

        enrollment = await session.scalar(
            select(ClassroomEnrollment.id).where(
                ClassroomEnrollment.classroom_id == path.classroom_id,
                ClassroomEnrollment.user_id == student_id,
                ClassroomEnrollment.role == "student",
            )
        )
        return enrollment is not None
    return False


async def require_student(
    session: AsyncSession,
    organization_id: UUID,
    student_id: UUID,
) -> None:
    if not await validate_student_membership(
        session,
        organization_id=organization_id,
        student_id=student_id,
    ):
        raise HTTPException(status_code=404, detail="Estudante não encontrado na organização")


@router.get("/students", response_model=list[AdaptiveStudentListItem])
async def list_adaptive_students(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AdaptiveStudentListItem]:
    rows = (
        await session.execute(
            select(User.id, User.full_name, User.email, User.is_active)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.organization_id == org_id(membership),
                Membership.role == OrganizationRole.MEMBER,
                Membership.is_active.is_(True),
                User.is_active.is_(True),
            )
            .order_by(User.full_name.asc())
        )
    ).all()
    return [
        AdaptiveStudentListItem(
            id=row.id, full_name=row.full_name, email=row.email, is_active=row.is_active
        )
        for row in rows
    ]


@router.get("/dashboard", response_model=AdaptiveDashboardRead)
async def dashboard(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> AdaptiveDashboardRead:
    organization_id = org_id(membership)
    profiles = int(
        await session.scalar(
            select(func.count(AdaptiveLearningProfile.id)).where(
                AdaptiveLearningProfile.organization_id == organization_id
            )
        )
        or 0
    )
    active_paths = int(
        await session.scalar(
            select(func.count(AdaptiveLearningPath.id)).where(
                AdaptiveLearningPath.organization_id == organization_id,
                AdaptiveLearningPath.status == "active",
            )
        )
        or 0
    )
    pending = int(
        await session.scalar(
            select(func.count(AdaptiveRecommendation.id)).where(
                AdaptiveRecommendation.organization_id == organization_id,
                AdaptiveRecommendation.status == "pending_review",
            )
        )
        or 0
    )
    reviews = int(
        await session.scalar(
            select(func.count(AdaptiveReviewSchedule.id)).where(
                AdaptiveReviewSchedule.organization_id == organization_id,
                AdaptiveReviewSchedule.status == "scheduled",
            )
        )
        or 0
    )
    low_confidence = int(
        await session.scalar(
            select(func.count(AdaptiveSkillState.id)).where(
                AdaptiveSkillState.organization_id == organization_id,
                AdaptiveSkillState.confidence_score < 0.6,
            )
        )
        or 0
    )
    attention = int(
        await session.scalar(
            select(func.count(AdaptiveSkillState.id)).where(
                AdaptiveSkillState.organization_id == organization_id,
                AdaptiveSkillState.mastery_score < 0.65,
                AdaptiveSkillState.evidence_count >= 3,
            )
        )
        or 0
    )
    groups = int(
        await session.scalar(
            select(func.count(AdaptiveStudentGroup.id)).where(
                AdaptiveStudentGroup.organization_id == organization_id,
                AdaptiveStudentGroup.status == "active",
            )
        )
        or 0
    )
    recent = list(
        (
            await session.scalars(
                select(AdaptiveRecommendation)
                .where(AdaptiveRecommendation.organization_id == organization_id)
                .order_by(AdaptiveRecommendation.created_at.desc())
                .limit(8)
            )
        ).all()
    )
    path_rows = (
        await session.execute(
            select(AdaptiveLearningPath.status, func.count(AdaptiveLearningPath.id))
            .where(AdaptiveLearningPath.organization_id == organization_id)
            .group_by(AdaptiveLearningPath.status)
        )
    ).all()
    mastery_rows = (
        await session.execute(
            select(AdaptiveSkillState.mastery_level, func.count(AdaptiveSkillState.id))
            .where(AdaptiveSkillState.organization_id == organization_id)
            .group_by(AdaptiveSkillState.mastery_level)
        )
    ).all()
    return AdaptiveDashboardRead(
        students_with_profiles=profiles,
        active_paths=active_paths,
        pending_recommendations=pending,
        scheduled_reviews=reviews,
        low_confidence_states=low_confidence,
        dimensions_needing_attention=attention,
        temporary_groups=groups,
        recent_recommendations=[RecommendationRead.model_validate(item) for item in recent],
        paths_by_status={str(key): int(value) for key, value in path_rows},
        mastery_distribution={str(key): int(value) for key, value in mastery_rows},
    )


@router.post("/refresh", response_model=AdaptiveRefreshRead, status_code=status.HTTP_201_CREATED)
async def refresh_adaptive_data(
    data: AdaptiveRefreshRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AdaptiveRefreshRead:
    organization_id = org_id(membership)
    model = (
        await session.get(AdaptiveModelVersion, data.model_version_id)
        if data.model_version_id
        else await ensure_default_model(session, organization_id=organization_id, user_id=user.id)
    )
    if model is None or model.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Modelo adaptativo não encontrado")
    student_ids = [data.student_id] if data.student_id else await classroom_student_ids(
        session, organization_id=organization_id, classroom_id=data.classroom_id  # type: ignore[arg-type]
    )
    states_updated = 0
    recommendations = 0
    processed = 0
    for student_id in student_ids:
        if student_id is None:
            continue
        await require_student(session, organization_id, student_id)
        states, _ = await refresh_student_states(
            session,
            organization_id=organization_id,
            student_id=student_id,
            model=model,
        )
        states_updated += len(states)
        processed += 1
        if data.generate_recommendations:
            created = await create_recommendations_for_states(
                session,
                organization_id=organization_id,
                student_id=student_id,
                model=model,
                states=states,
                created_by_user_id=user.id,
            )
            recommendations += len(created)
    await audit(
        session,
        organization_id=organization_id,
        actor_user_id=user.id,
        action="adaptive.refresh",
        entity_type="student" if data.student_id else "classroom",
        entity_id=data.student_id or data.classroom_id,
        details={
            "students": processed,
            "states": states_updated,
            "recommendations": recommendations,
            "model_version_id": str(model.id),
        },
    )
    await session.commit()
    return AdaptiveRefreshRead(
        students_processed=processed,
        skill_states_updated=states_updated,
        recommendations_created=recommendations,
        reviews_scheduled=0,
        model_version_id=model.id,
        calculation_version=model.version,
    )


@router.get("/students/{student_id}", response_model=StudentAdaptiveSummary)
async def student_profile(
    student_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> StudentAdaptiveSummary:
    organization_id = org_id(membership)
    await require_student(session, organization_id, student_id)
    profile = await ensure_profile(session, organization_id=organization_id, student_id=student_id)
    states = list(
        (
            await session.scalars(
                select(AdaptiveSkillState)
                .where(
                    AdaptiveSkillState.organization_id == organization_id,
                    AdaptiveSkillState.student_id == student_id,
                )
                .order_by(AdaptiveSkillState.mastery_score.asc())
            )
        ).all()
    )
    active_paths = int(
        await session.scalar(
            select(func.count(AdaptiveLearningPath.id)).where(
                AdaptiveLearningPath.organization_id == organization_id,
                AdaptiveLearningPath.student_id == student_id,
                AdaptiveLearningPath.status.in_(["approved", "active", "paused"]),
            )
        )
        or 0
    )
    pending = int(
        await session.scalar(
            select(func.count(AdaptiveRecommendation.id)).where(
                AdaptiveRecommendation.organization_id == organization_id,
                AdaptiveRecommendation.student_id == student_id,
                AdaptiveRecommendation.status == "pending_review",
            )
        )
        or 0
    )
    reviews = int(
        await session.scalar(
            select(func.count(AdaptiveReviewSchedule.id)).where(
                AdaptiveReviewSchedule.organization_id == organization_id,
                AdaptiveReviewSchedule.student_id == student_id,
                AdaptiveReviewSchedule.status == "scheduled",
            )
        )
        or 0
    )
    return StudentAdaptiveSummary(
        profile=AdaptiveProfileRead.model_validate(profile),
        skill_states=[SkillStateRead.model_validate(item) for item in states],
        active_paths=active_paths,
        pending_recommendations=pending,
        upcoming_reviews=reviews,
        weakest_dimensions=[SkillStateRead.model_validate(item) for item in states[:5]],
        strongest_dimensions=[SkillStateRead.model_validate(item) for item in list(reversed(states))[:5]],
    )


@router.patch("/students/{student_id}/profile", response_model=AdaptiveProfileRead)
async def update_profile(
    student_id: UUID,
    data: AdaptiveProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AdaptiveLearningProfile:
    organization_id = org_id(membership)
    await require_student(session, organization_id, student_id)
    profile = await ensure_profile(session, organization_id=organization_id, student_id=student_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await audit(
        session,
        organization_id=organization_id,
        actor_user_id=user.id,
        student_id=student_id,
        action="profile.updated",
        entity_type="adaptive_profile",
        entity_id=profile.id,
        details={"fields": list(data.model_dump(exclude_unset=True))},
    )
    await session.commit()
    await session.refresh(profile)
    return profile


@router.post("/recommendations/generate", response_model=list[RecommendationRead], status_code=201)
async def generate_recommendations(
    data: RecommendationGenerateRequest,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> list[AdaptiveRecommendation]:
    organization_id = org_id(membership)
    await require_student(session, organization_id, data.student_id)
    model = await ensure_default_model(session, organization_id=organization_id, user_id=user.id)
    states = list(
        (
            await session.scalars(
                select(AdaptiveSkillState).where(
                    AdaptiveSkillState.organization_id == organization_id,
                    AdaptiveSkillState.student_id == data.student_id,
                )
            )
        ).all()
    )
    if not states:
        states, _ = await refresh_student_states(
            session,
            organization_id=organization_id,
            student_id=data.student_id,
            model=model,
        )
    only = (
        (data.dimension_type, data.dimension_code)
        if data.dimension_type and data.dimension_code
        else None
    )
    created = await create_recommendations_for_states(
        session,
        organization_id=organization_id,
        student_id=data.student_id,
        model=model,
        states=states,
        created_by_user_id=user.id,
        maximum=data.maximum_recommendations,
        only_dimension=only,
    )
    await session.commit()
    return created


@router.get("/recommendations", response_model=list[RecommendationRead])
async def recommendations(
    status_filter: str | None = Query(default=None, alias="status"),
    student_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[AdaptiveRecommendation]:
    statement = select(AdaptiveRecommendation).where(
        AdaptiveRecommendation.organization_id == org_id(membership)
    )
    if status_filter:
        statement = statement.where(AdaptiveRecommendation.status == status_filter)
    if student_id:
        statement = statement.where(AdaptiveRecommendation.student_id == student_id)
    return list(
        (
            await session.scalars(
                statement.order_by(AdaptiveRecommendation.created_at.desc()).limit(300)
            )
        ).all()
    )


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationRead)
async def review_recommendation(
    recommendation_id: UUID,
    data: RecommendationReview,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> AdaptiveRecommendation:
    recommendation = await session.scalar(
        select(AdaptiveRecommendation).where(
            AdaptiveRecommendation.id == recommendation_id,
            AdaptiveRecommendation.organization_id == org_id(membership),
        )
    )
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada")
    recommendation.status = data.decision
    recommendation.review_notes = data.review_notes
    recommendation.reviewed_by_user_id = user.id
    recommendation.reviewed_at = datetime.now(UTC)
    if data.proposed_materials is not None:
        recommendation.proposed_materials = data.proposed_materials
    if data.target_mastery is not None:
        recommendation.target_mastery = data.target_mastery
    await audit(
        session,
        organization_id=org_id(membership),
        actor_user_id=user.id,
        student_id=recommendation.student_id,
        action=f"recommendation.{data.decision}",
        entity_type="adaptive_recommendation",
        entity_id=recommendation.id,
        details={"notes": data.review_notes},
    )
    await session.commit()
    await session.refresh(recommendation)
    return recommendation


@router.post("/recommendations/{recommendation_id}/create-path", response_model=LearningPathRead, status_code=201)
async def recommendation_to_path(
    recommendation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> LearningPathRead:
    organization_id = org_id(membership)
    recommendation = await session.scalar(
        select(AdaptiveRecommendation).where(
            AdaptiveRecommendation.id == recommendation_id,
            AdaptiveRecommendation.organization_id == organization_id,
        )
    )
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada")
    if recommendation.status in {"rejected", "changes_requested"}:
        raise HTTPException(status_code=409, detail="A recomendação precisa ser aprovada antes de criar a trilha")
    model = await session.get(AdaptiveModelVersion, recommendation.model_version_id)
    if model is None:
        raise HTTPException(status_code=409, detail="Modelo da recomendação não encontrado")
    path = await approve_recommendation_as_path(
        session,
        organization_id=organization_id,
        recommendation=recommendation,
        teacher_id=user.id,
        model=model,
    )
    await activate_path(session, path=path, actor_user_id=user.id)
    student_ids = await path_student_ids(session, path)
    mastery = float(recommendation.evidence_summary.get("mastery_score", 0.0))
    await schedule_reviews_for_path(
        session,
        organization_id=organization_id,
        path=path,
        student_ids=student_ids,
        mastery_score=mastery,
    )
    await session.commit()
    _, steps = await load_path_with_steps(session, organization_id=organization_id, path=path)
    return path_payload(path, steps)


@router.get("/paths", response_model=list[LearningPathRead])
async def list_paths(
    status_filter: str | None = Query(default=None, alias="status"),
    student_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[LearningPathRead]:
    organization_id = org_id(membership)
    statement = select(AdaptiveLearningPath).where(
        AdaptiveLearningPath.organization_id == organization_id
    )
    if status_filter:
        statement = statement.where(AdaptiveLearningPath.status == status_filter)
    if student_id:
        statement = statement.where(AdaptiveLearningPath.student_id == student_id)
    paths = list(
        (
            await session.scalars(statement.order_by(AdaptiveLearningPath.created_at.desc()).limit(300))
        ).all()
    )
    result: list[LearningPathRead] = []
    for path in paths:
        _, steps = await load_path_with_steps(session, organization_id=organization_id, path=path)
        result.append(path_payload(path, steps))
    return result


@router.post("/paths", response_model=LearningPathRead, status_code=201)
async def add_path(
    data: LearningPathCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> LearningPathRead:
    organization_id = org_id(membership)
    if data.student_id:
        await require_student(session, organization_id, data.student_id)
    model = await ensure_default_model(session, organization_id=organization_id, user_id=user.id)
    path = await create_path(
        session,
        organization_id=organization_id,
        teacher_id=user.id,
        model=model,
        data=data,
    )
    await session.commit()
    _, steps = await load_path_with_steps(session, organization_id=organization_id, path=path)
    return path_payload(path, steps)


@router.get("/paths/{path_id}", response_model=LearningPathRead)
async def get_path(
    path_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> LearningPathRead:
    path = await session.scalar(
        select(AdaptiveLearningPath).where(
            AdaptiveLearningPath.id == path_id,
            AdaptiveLearningPath.organization_id == org_id(membership),
        )
    )
    if path is None:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    _, steps = await load_path_with_steps(session, organization_id=org_id(membership), path=path)
    return path_payload(path, steps)


@router.patch("/paths/{path_id}/status", response_model=LearningPathRead)
async def update_path_status(
    path_id: UUID,
    data: PathStatusUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> LearningPathRead:
    organization_id = org_id(membership)
    path = await session.scalar(
        select(AdaptiveLearningPath).where(
            AdaptiveLearningPath.id == path_id,
            AdaptiveLearningPath.organization_id == organization_id,
        )
    )
    if path is None:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    if data.status == "active":
        await activate_path(session, path=path, actor_user_id=user.id)
        student_ids = await path_student_ids(session, path)
        existing_reviews = int(
            await session.scalar(
                select(func.count(AdaptiveReviewSchedule.id)).where(
                    AdaptiveReviewSchedule.path_id == path.id
                )
            )
            or 0
        )
        if not existing_reviews:
            await schedule_reviews_for_path(
                session,
                organization_id=organization_id,
                path=path,
                student_ids=student_ids,
                mastery_score=0.5,
            )
    else:
        path.status = data.status
        if data.status == "completed":
            path.completed_at = datetime.now(UTC)
            for student_id in await path_student_ids(session, path):
                await calculate_path_outcome(
                    session,
                    organization_id=organization_id,
                    path=path,
                    student_id=student_id,
                )
    await audit(
        session,
        organization_id=organization_id,
        actor_user_id=user.id,
        student_id=path.student_id,
        action=f"path.{data.status}",
        entity_type="learning_path",
        entity_id=path.id,
        details={"notes": data.notes},
    )
    await session.commit()
    _, steps = await load_path_with_steps(session, organization_id=organization_id, path=path)
    return path_payload(path, steps)


@router.post("/steps/{step_id}/complete", response_model=PathStepRead)
async def mark_step_complete(
    step_id: UUID,
    data: PathStepComplete,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ALL_ROLES)),
    user: User = Depends(get_current_user),
) -> AdaptivePathStep:
    organization_id = org_id(membership)
    step = await session.scalar(
        select(AdaptivePathStep).where(
            AdaptivePathStep.id == step_id,
            AdaptivePathStep.organization_id == organization_id,
        )
    )
    if step is None:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    path = await session.get(AdaptiveLearningPath, step.path_id)
    if path is None or path.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Trilha não encontrada")
    if membership.role == OrganizationRole.MEMBER and not await student_can_access_path(
        session, path=path, student_id=user.id
    ):
        raise HTTPException(status_code=403, detail="Esta etapa não pertence à sua trilha")
    await complete_step(
        session,
        organization_id=organization_id,
        step=step,
        score=data.score,
        evidence_count=data.evidence_count,
        notes=data.notes,
    )
    await audit(
        session,
        organization_id=organization_id,
        actor_user_id=user.id,
        student_id=path.student_id,
        action="step.completed",
        entity_type="adaptive_path_step",
        entity_id=step.id,
        details=data.model_dump(),
    )
    await session.commit()
    await session.refresh(step)
    return step


@router.get("/groups", response_model=list[StudentGroupRead])
async def groups(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[StudentGroupRead]:
    organization_id = org_id(membership)
    rows = list(
        (
            await session.scalars(
                select(AdaptiveStudentGroup)
                .where(AdaptiveStudentGroup.organization_id == organization_id)
                .order_by(AdaptiveStudentGroup.created_at.desc())
            )
        ).all()
    )
    result = []
    for group in rows:
        count = int(
            await session.scalar(
                select(func.count(AdaptiveGroupMember.id)).where(
                    AdaptiveGroupMember.group_id == group.id,
                    AdaptiveGroupMember.removed_at.is_(None),
                )
            )
            or 0
        )
        result.append(StudentGroupRead.model_validate({**{c.name: getattr(group, c.name) for c in group.__table__.columns}, "member_count": count}))
    return result


@router.post("/groups", response_model=StudentGroupRead, status_code=201)
async def add_group(
    data: StudentGroupCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentGroupRead:
    organization_id = org_id(membership)
    for student_id in data.student_ids:
        await require_student(session, organization_id, student_id)
    group = await create_group(
        session,
        organization_id=organization_id,
        teacher_id=user.id,
        data=data,
    )
    await session.commit()
    return StudentGroupRead.model_validate(
        {**{c.name: getattr(group, c.name) for c in group.__table__.columns}, "member_count": len(set(data.student_ids))}
    )


@router.post("/groups/{group_id}/members", response_model=StudentGroupRead)
async def add_group_members(
    group_id: UUID,
    data: GroupMemberUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentGroupRead:
    organization_id = org_id(membership)
    group = await session.scalar(
        select(AdaptiveStudentGroup).where(
            AdaptiveStudentGroup.id == group_id,
            AdaptiveStudentGroup.organization_id == organization_id,
        )
    )
    if group is None:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    for student_id in data.student_ids:
        await require_student(session, organization_id, student_id)
        existing = await session.scalar(
            select(AdaptiveGroupMember).where(
                AdaptiveGroupMember.group_id == group.id,
                AdaptiveGroupMember.student_id == student_id,
                AdaptiveGroupMember.removed_at.is_(None),
            )
        )
        if existing is None:
            session.add(
                AdaptiveGroupMember(
                    organization_id=organization_id,
                    group_id=group.id,
                    student_id=student_id,
                    reason_snapshot={"reason": data.reason},
                    added_by_user_id=user.id,
                )
            )
    await session.commit()
    count = int(
        await session.scalar(
            select(func.count(AdaptiveGroupMember.id)).where(
                AdaptiveGroupMember.group_id == group.id,
                AdaptiveGroupMember.removed_at.is_(None),
            )
        )
        or 0
    )
    return StudentGroupRead.model_validate(
        {**{c.name: getattr(group, c.name) for c in group.__table__.columns}, "member_count": count}
    )


@router.get("/prerequisites", response_model=list[PrerequisiteRead])
async def prerequisites(
    dimension_code: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
) -> list[SkillPrerequisite]:
    statement = select(SkillPrerequisite).where(
        SkillPrerequisite.organization_id == org_id(membership)
    )
    if dimension_code:
        statement = statement.where(SkillPrerequisite.dimension_code == dimension_code)
    return list((await session.scalars(statement.order_by(SkillPrerequisite.dimension_code))).all())


@router.post("/prerequisites", response_model=PrerequisiteRead, status_code=201)
async def add_prerequisite(
    data: PrerequisiteCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> SkillPrerequisite:
    item = SkillPrerequisite(
        organization_id=org_id(membership),
        created_by_user_id=user.id,
        **data.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/models", response_model=list[AdaptiveModelRead])
async def models(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
    user: User = Depends(get_current_user),
) -> list[AdaptiveModelVersion]:
    model = await ensure_default_model(session, organization_id=org_id(membership), user_id=user.id)
    await session.commit()
    return list(
        (
            await session.scalars(
                select(AdaptiveModelVersion)
                .where(AdaptiveModelVersion.organization_id == org_id(membership))
                .order_by(AdaptiveModelVersion.code, AdaptiveModelVersion.version.desc())
            )
        ).all()
    ) or [model]


@router.post("/models", response_model=AdaptiveModelRead, status_code=201)
async def add_model(
    data: AdaptiveModelCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
    user: User = Depends(get_current_user),
) -> AdaptiveModelVersion:
    organization_id = org_id(membership)
    latest = await session.scalar(
        select(func.max(AdaptiveModelVersion.version)).where(
            AdaptiveModelVersion.organization_id == organization_id,
            AdaptiveModelVersion.code == data.code,
        )
    )
    if data.is_default:
        existing = list(
            (
                await session.scalars(
                    select(AdaptiveModelVersion).where(
                        AdaptiveModelVersion.organization_id == organization_id,
                        AdaptiveModelVersion.is_default.is_(True),
                    )
                )
            ).all()
        )
        for item in existing:
            item.is_default = False
    model = AdaptiveModelVersion(
        organization_id=organization_id,
        code=data.code,
        name=data.name,
        version=int(latest or 0) + 1,
        status="active",
        description=data.description,
        rules_json=data.rules_json,
        thresholds_json=data.thresholds_json,
        minimum_evidence_count=data.minimum_evidence_count,
        is_default=data.is_default,
        created_by_user_id=user.id,
        approved_by_user_id=user.id,
        approved_at=datetime.now(UTC),
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model


@router.get("/outcomes", response_model=list[PathOutcomeRead])
async def outcomes(
    path_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*TEACHER_ROLES)),
):
    from app.models.adaptive import AdaptivePathOutcome

    statement = select(AdaptivePathOutcome).where(
        AdaptivePathOutcome.organization_id == org_id(membership)
    )
    if path_id:
        statement = statement.where(AdaptivePathOutcome.path_id == path_id)
    return list((await session.scalars(statement.order_by(AdaptivePathOutcome.calculated_at.desc()).limit(300))).all())


@router.get("/me", response_model=StudentOwnPathRead)
async def my_adaptive_path(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ALL_ROLES)),
    user: User = Depends(get_current_user),
) -> StudentOwnPathRead:
    organization_id = org_id(membership)
    profile = await ensure_profile(session, organization_id=organization_id, student_id=user.id)
    states = list(
        (
            await session.scalars(
                select(AdaptiveSkillState)
                .where(
                    AdaptiveSkillState.organization_id == organization_id,
                    AdaptiveSkillState.student_id == user.id,
                )
                .order_by(AdaptiveSkillState.mastery_score.asc())
            )
        ).all()
    )
    from app.models.education import ClassroomEnrollment

    group_ids = list(
        (
            await session.scalars(
                select(AdaptiveGroupMember.group_id).where(
                    AdaptiveGroupMember.organization_id == organization_id,
                    AdaptiveGroupMember.student_id == user.id,
                    AdaptiveGroupMember.removed_at.is_(None),
                )
            )
        ).all()
    )
    classroom_ids = list(
        (
            await session.scalars(
                select(ClassroomEnrollment.classroom_id).where(
                    ClassroomEnrollment.user_id == user.id,
                    ClassroomEnrollment.role == "student",
                )
            )
        ).all()
    )
    targets = [AdaptiveLearningPath.student_id == user.id]
    if group_ids:
        targets.append(AdaptiveLearningPath.group_id.in_(group_ids))
    if classroom_ids:
        targets.append(AdaptiveLearningPath.classroom_id.in_(classroom_ids))
    paths = list(
        (
            await session.scalars(
                select(AdaptiveLearningPath)
                .where(
                    AdaptiveLearningPath.organization_id == organization_id,
                    or_(*targets),
                    AdaptiveLearningPath.status.in_(["approved", "active", "paused", "completed"]),
                )
                .order_by(AdaptiveLearningPath.created_at.desc())
            )
        ).all()
    )
    path_reads: list[LearningPathRead] = []
    for path in paths:
        _, steps = await load_path_with_steps(session, organization_id=organization_id, path=path)
        path_reads.append(path_payload(path, steps))
    reviews = list(
        (
            await session.scalars(
                select(AdaptiveReviewSchedule)
                .where(
                    AdaptiveReviewSchedule.organization_id == organization_id,
                    AdaptiveReviewSchedule.student_id == user.id,
                    AdaptiveReviewSchedule.status == "scheduled",
                )
                .order_by(AdaptiveReviewSchedule.scheduled_for.asc())
            )
        ).all()
    )
    await session.commit()
    return StudentOwnPathRead(
        profile=AdaptiveProfileRead.model_validate(profile),
        skill_states=[SkillStateRead.model_validate(item) for item in states],
        paths=path_reads,
        reviews=[ReviewScheduleRead.model_validate(item) for item in reviews],
        explanation=(
            "Sua trilha usa somente exercícios e avaliações realizados no EduCode. "
            "As recomendações são revisadas pelo professor e não geram ranking entre estudantes."
        ),
    )


@router.post("/me/reviews/{review_id}/complete", response_model=ReviewScheduleRead)
async def complete_review(
    review_id: UUID,
    data: ReviewComplete,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ALL_ROLES)),
    user: User = Depends(get_current_user),
) -> AdaptiveReviewSchedule:
    review = await session.scalar(
        select(AdaptiveReviewSchedule).where(
            AdaptiveReviewSchedule.id == review_id,
            AdaptiveReviewSchedule.organization_id == org_id(membership),
            AdaptiveReviewSchedule.student_id == user.id,
        )
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Revisão não encontrada")
    review.status = "completed"
    review.completed_at = datetime.now(UTC)
    review.outcome_snapshot = {"score": data.score, "notes": data.notes}
    await audit(
        session,
        organization_id=org_id(membership),
        actor_user_id=user.id,
        student_id=user.id,
        action="review.completed",
        entity_type="adaptive_review",
        entity_id=review.id,
        details=review.outcome_snapshot,
    )
    await session.commit()
    await session.refresh(review)
    return review
