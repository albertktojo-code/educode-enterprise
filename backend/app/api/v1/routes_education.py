from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.document import Document, DocumentStatus
from app.models.education import (
    Classroom,
    ClassroomEnrollment,
    ContentItem,
    Project,
    ProjectStatus,
    Subject,
)
from app.schemas.education import (
    ClassroomCreate,
    ClassroomRead,
    ClassroomUpdate,
    ContentCreate,
    ContentRead,
    ContentUpdate,
    DashboardSummary,
    DirectoryUser,
    EnrollmentCreate,
    EnrollmentRead,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
)
from app.school_admissions.models import SchoolUnit

router = APIRouter(tags=["Núcleo educacional"])

READ_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
    OrganizationRole.MEMBER,
)
WRITE_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.TEACHER,
)
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def organization_id(membership: Membership) -> UUID:
    return membership.organization_id


async def get_subject_in_organization(
    subject_id: UUID,
    membership: Membership,
    session: AsyncSession,
) -> Subject:
    subject = await session.scalar(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.organization_id == organization_id(membership),
        )
    )
    if subject is None:
        raise HTTPException(status_code=404, detail="Disciplina não encontrada")
    return subject


async def get_classroom_in_organization(
    classroom_id: UUID,
    membership: Membership,
    session: AsyncSession,
) -> Classroom:
    classroom = await session.scalar(
        select(Classroom).where(
            Classroom.id == classroom_id,
            Classroom.organization_id == organization_id(membership),
        )
    )
    if classroom is None:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    return classroom


async def validate_school_unit(
    school_unit_id: UUID | None,
    membership: Membership,
    session: AsyncSession,
) -> None:
    if school_unit_id is None:
        return
    unit = await session.scalar(
        select(SchoolUnit.id).where(
            SchoolUnit.id == school_unit_id,
            SchoolUnit.organization_id == organization_id(membership),
            SchoolUnit.is_active.is_(True),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade escolar não encontrada")


async def get_project_in_organization(
    project_id: UUID,
    membership: Membership,
    session: AsyncSession,
) -> Project:
    project = await session.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == organization_id(membership),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


async def validate_education_links(
    membership: Membership,
    session: AsyncSession,
    subject_id: UUID | None,
    classroom_id: UUID | None,
) -> None:
    if subject_id is not None:
        await get_subject_in_organization(subject_id, membership, session)
    if classroom_id is not None:
        await get_classroom_in_organization(classroom_id, membership, session)


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> DashboardSummary:
    org_id = organization_id(membership)

    subjects = await session.scalar(
        select(func.count(Subject.id)).where(Subject.organization_id == org_id)
    )
    classrooms = await session.scalar(
        select(func.count(Classroom.id)).where(Classroom.organization_id == org_id)
    )
    active_classrooms = await session.scalar(
        select(func.count(Classroom.id)).where(
            Classroom.organization_id == org_id,
            Classroom.is_active.is_(True),
        )
    )
    users = await session.scalar(
        select(func.count(Membership.id)).where(Membership.organization_id == org_id)
    )
    projects = await session.scalar(
        select(func.count(Project.id)).where(Project.organization_id == org_id)
    )
    project_rows = (
        await session.execute(
            select(Project.status, func.count(Project.id))
            .where(Project.organization_id == org_id)
            .group_by(Project.status)
        )
    ).all()
    project_counts = {row[0]: row[1] for row in project_rows}
    contents = await session.scalar(
        select(func.count(ContentItem.id))
        .join(Project, Project.id == ContentItem.project_id)
        .where(Project.organization_id == org_id)
    )
    published_contents = await session.scalar(
        select(func.count(ContentItem.id))
        .join(Project, Project.id == ContentItem.project_id)
        .where(
            Project.organization_id == org_id,
            ContentItem.is_published.is_(True),
        )
    )
    documents = await session.scalar(
        select(func.count(Document.id)).where(Document.organization_id == org_id)
    )
    ready_documents = await session.scalar(
        select(func.count(Document.id)).where(
            Document.organization_id == org_id,
            Document.status == DocumentStatus.READY,
        )
    )

    return DashboardSummary(
        subjects=subjects or 0,
        classrooms=classrooms or 0,
        active_classrooms=active_classrooms or 0,
        users=users or 0,
        projects=projects or 0,
        draft_projects=project_counts.get(ProjectStatus.DRAFT, 0),
        active_projects=project_counts.get(ProjectStatus.ACTIVE, 0),
        archived_projects=project_counts.get(ProjectStatus.ARCHIVED, 0),
        contents=contents or 0,
        published_contents=published_contents or 0,
        documents=documents or 0,
        ready_documents=ready_documents or 0,
    )


@router.get("/subjects", response_model=list[SubjectRead])
async def list_subjects(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[Subject]:
    result = await session.scalars(
        select(Subject)
        .where(Subject.organization_id == organization_id(membership))
        .order_by(Subject.is_active.desc(), Subject.name)
    )
    return list(result.all())


@router.post("/subjects", response_model=SubjectRead, status_code=201)
async def create_subject(
    data: SubjectCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Subject:
    item = Subject(
        organization_id=organization_id(membership),
        name=data.name.strip(),
        code=data.code.strip().upper(),
        description=data.description,
    )
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Código de disciplina já utilizado") from exc
    await session.refresh(item)
    return item


@router.patch("/subjects/{subject_id}", response_model=SubjectRead)
async def update_subject(
    subject_id: UUID,
    data: SubjectUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Subject:
    subject = await get_subject_in_organization(subject_id, membership, session)
    values = data.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is not None:
        values["name"] = values["name"].strip()
    if "code" in values and values["code"] is not None:
        values["code"] = values["code"].strip().upper()
    for field, value in values.items():
        setattr(subject, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Código de disciplina já utilizado") from exc
    await session.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}", status_code=204)
async def deactivate_subject(
    subject_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    subject = await get_subject_in_organization(subject_id, membership, session)
    subject.is_active = False
    await session.commit()
    return Response(status_code=204)


@router.get("/classrooms", response_model=list[ClassroomRead])
async def list_classrooms(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[Classroom]:
    result = await session.scalars(
        select(Classroom)
        .where(Classroom.organization_id == organization_id(membership))
        .order_by(Classroom.is_active.desc(), Classroom.name)
    )
    return list(result.all())


@router.get("/classrooms/directory", response_model=list[DirectoryUser])
async def classroom_directory(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> list[DirectoryUser]:
    rows = (
        await session.execute(
            select(User, Membership)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.organization_id == organization_id(membership),
                Membership.is_active.is_(True),
                User.is_active.is_(True),
            )
            .order_by(User.full_name)
        )
    ).all()
    return [
        DirectoryUser(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            organization_role=member.role.value,
        )
        for user, member in rows
    ]


@router.post("/classrooms", response_model=ClassroomRead, status_code=201)
async def create_classroom(
    data: ClassroomCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Classroom:
    if data.subject_id is not None:
        await get_subject_in_organization(data.subject_id, membership, session)
    await validate_school_unit(data.school_unit_id, membership, session)
    item = Classroom(
        organization_id=organization_id(membership),
        **data.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/classrooms/{classroom_id}", response_model=ClassroomRead)
async def get_classroom(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> Classroom:
    return await get_classroom_in_organization(classroom_id, membership, session)


@router.patch("/classrooms/{classroom_id}", response_model=ClassroomRead)
async def update_classroom(
    classroom_id: UUID,
    data: ClassroomUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Classroom:
    classroom = await get_classroom_in_organization(classroom_id, membership, session)
    values = data.model_dump(exclude_unset=True)
    if "subject_id" in values and values["subject_id"] is not None:
        await get_subject_in_organization(values["subject_id"], membership, session)
    if "school_unit_id" in values:
        await validate_school_unit(values["school_unit_id"], membership, session)
    for field, value in values.items():
        setattr(classroom, field, value)
    await session.commit()
    await session.refresh(classroom)
    return classroom


@router.delete("/classrooms/{classroom_id}", status_code=204)
async def deactivate_classroom(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    classroom = await get_classroom_in_organization(classroom_id, membership, session)
    classroom.is_active = False
    await session.commit()
    return Response(status_code=204)


@router.get(
    "/classrooms/{classroom_id}/participants",
    response_model=list[EnrollmentRead],
)
async def list_participants(
    classroom_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[EnrollmentRead]:
    await get_classroom_in_organization(classroom_id, membership, session)
    rows = (
        await session.execute(
            select(ClassroomEnrollment, User)
            .join(User, User.id == ClassroomEnrollment.user_id)
            .where(ClassroomEnrollment.classroom_id == classroom_id)
            .order_by(User.full_name)
        )
    ).all()
    return [
        EnrollmentRead(
            id=enrollment.id,
            classroom_id=enrollment.classroom_id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=enrollment.role,
            created_at=enrollment.created_at,
        )
        for enrollment, user in rows
    ]


@router.post(
    "/classrooms/{classroom_id}/participants",
    response_model=EnrollmentRead,
    status_code=201,
)
async def add_participant(
    classroom_id: UUID,
    data: EnrollmentCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> EnrollmentRead:
    await get_classroom_in_organization(classroom_id, membership, session)
    row = (
        await session.execute(
            select(User, Membership)
            .join(Membership, Membership.user_id == User.id)
            .where(
                User.id == data.user_id,
                Membership.organization_id == organization_id(membership),
                Membership.is_active.is_(True),
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuário não pertence à organização")
    user, _ = row

    existing = await session.scalar(
        select(ClassroomEnrollment).where(
            ClassroomEnrollment.classroom_id == classroom_id,
            ClassroomEnrollment.user_id == data.user_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Participante já está na turma")

    enrollment = ClassroomEnrollment(
        classroom_id=classroom_id,
        user_id=data.user_id,
        role=data.role,
    )
    session.add(enrollment)
    await session.commit()
    await session.refresh(enrollment)
    return EnrollmentRead(
        id=enrollment.id,
        classroom_id=enrollment.classroom_id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=enrollment.role,
        created_at=enrollment.created_at,
    )


@router.delete(
    "/classrooms/{classroom_id}/participants/{enrollment_id}",
    status_code=204,
)
async def remove_participant(
    classroom_id: UUID,
    enrollment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    await get_classroom_in_organization(classroom_id, membership, session)
    enrollment = await session.scalar(
        select(ClassroomEnrollment).where(
            ClassroomEnrollment.id == enrollment_id,
            ClassroomEnrollment.classroom_id == classroom_id,
        )
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Participante não encontrado")
    await session.delete(enrollment)
    await session.commit()
    return Response(status_code=204)


@router.get("/projects", response_model=list[ProjectRead])
async def list_projects(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[Project]:
    result = await session.scalars(
        select(Project)
        .where(Project.organization_id == organization_id(membership))
        .order_by(Project.updated_at.desc())
    )
    return list(result.all())


@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    current_user: User = Depends(get_current_user),
) -> Project:
    await validate_education_links(
        membership,
        session,
        data.subject_id,
        data.classroom_id,
    )
    item = Project(
        organization_id=organization_id(membership),
        owner_id=current_user.id,
        **data.model_dump(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> Project:
    return await get_project_in_organization(project_id, membership, session)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Project:
    project = await get_project_in_organization(project_id, membership, session)
    values = data.model_dump(exclude_unset=True)
    await validate_education_links(
        membership,
        session,
        values.get("subject_id", project.subject_id),
        values.get("classroom_id", project.classroom_id),
    )
    for field, value in values.items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*ADMIN_ROLES)),
) -> Response:
    project = await get_project_in_organization(project_id, membership, session)
    await session.delete(project)
    await session.commit()
    return Response(status_code=204)


@router.get("/projects/{project_id}/contents", response_model=list[ContentRead])
async def list_contents(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[ContentItem]:
    await get_project_in_organization(project_id, membership, session)
    result = await session.scalars(
        select(ContentItem)
        .where(ContentItem.project_id == project_id)
        .order_by(ContentItem.position, ContentItem.created_at)
    )
    return list(result.all())


@router.post(
    "/projects/{project_id}/contents",
    response_model=ContentRead,
    status_code=201,
)
async def create_content(
    project_id: UUID,
    data: ContentCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> ContentItem:
    await get_project_in_organization(project_id, membership, session)
    item = ContentItem(project_id=project_id, **data.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.patch(
    "/projects/{project_id}/contents/{content_id}",
    response_model=ContentRead,
)
async def update_content(
    project_id: UUID,
    content_id: UUID,
    data: ContentUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> ContentItem:
    await get_project_in_organization(project_id, membership, session)
    content = await session.scalar(
        select(ContentItem).where(
            ContentItem.id == content_id,
            ContentItem.project_id == project_id,
        )
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(content, field, value)
    await session.commit()
    await session.refresh(content)
    return content


@router.delete(
    "/projects/{project_id}/contents/{content_id}",
    status_code=204,
)
async def delete_content(
    project_id: UUID,
    content_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    await get_project_in_organization(project_id, membership, session)
    content = await session.scalar(
        select(ContentItem).where(
            ContentItem.id == content_id,
            ContentItem.project_id == project_id,
        )
    )
    if content is None:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")
    await session.delete(content)
    await session.commit()
    return Response(status_code=204)
