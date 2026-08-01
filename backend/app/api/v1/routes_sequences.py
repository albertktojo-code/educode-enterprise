from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.models.creative import TeachingSequence, TeachingSequenceItem
from app.models.pedagogy import GenerationProject
from app.schemas.creative import (
    TeachingSequenceCreate,
    TeachingSequenceItemInput,
    TeachingSequenceRead,
    TeachingSequenceUpdate,
)

router = APIRouter(prefix="/teaching-sequences", tags=["Sequências didáticas"])

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


async def validate_generation_project(
    generation_project_id: UUID | None,
    membership: Membership,
    session: AsyncSession,
) -> None:
    if generation_project_id is None:
        return
    project = await session.scalar(
        select(GenerationProject).where(
            GenerationProject.id == generation_project_id,
            GenerationProject.organization_id == organization_id(membership),
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto de geração não encontrado")


async def get_sequence(
    sequence_id: UUID,
    membership: Membership,
    session: AsyncSession,
    *,
    require_write: bool = False,
) -> TeachingSequence:
    sequence = await session.scalar(
        select(TeachingSequence)
        .where(
            TeachingSequence.id == sequence_id,
            TeachingSequence.organization_id == organization_id(membership),
        )
        .options(selectinload(TeachingSequence.items))
    )
    if sequence is None:
        raise HTTPException(status_code=404, detail="Sequência didática não encontrada")
    if require_write and membership.role not in ADMIN_ROLES:
        if sequence.created_by_user_id != membership.user_id:
            raise HTTPException(
                status_code=403,
                detail="Apenas o autor ou um administrador pode alterar esta sequência",
            )
    return sequence


async def replace_items(
    sequence: TeachingSequence,
    items: list[TeachingSequenceItemInput],
    session: AsyncSession,
) -> None:
    await session.execute(
        delete(TeachingSequenceItem).where(TeachingSequenceItem.sequence_id == sequence.id)
    )
    for item in items:
        session.add(TeachingSequenceItem(sequence_id=sequence.id, **item.model_dump()))


@router.get("", response_model=list[TeachingSequenceRead])
async def list_sequences(
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> list[TeachingSequenceRead]:
    sequences = list(
        (
            await session.scalars(
                select(TeachingSequence)
                .where(TeachingSequence.organization_id == organization_id(membership))
                .options(selectinload(TeachingSequence.items))
                .order_by(TeachingSequence.updated_at.desc())
            )
        ).all()
    )
    return [TeachingSequenceRead.model_validate(sequence) for sequence in sequences]


@router.post("", response_model=TeachingSequenceRead, status_code=201)
async def create_sequence(
    data: TeachingSequenceCreate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
    user: User = Depends(get_current_user),
) -> TeachingSequenceRead:
    await validate_generation_project(data.generation_project_id, membership, session)
    sequence = TeachingSequence(
        organization_id=organization_id(membership),
        generation_project_id=data.generation_project_id,
        title=data.title,
        description=data.description,
        status=data.status,
        created_by_user_id=user.id,
        created_by_name_snapshot=user.full_name,
    )
    session.add(sequence)
    await session.flush()
    await replace_items(sequence, data.items, session)
    await session.commit()
    return TeachingSequenceRead.model_validate(await get_sequence(sequence.id, membership, session))


@router.get("/{sequence_id}", response_model=TeachingSequenceRead)
async def read_sequence(
    sequence_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*READ_ROLES)),
) -> TeachingSequenceRead:
    return TeachingSequenceRead.model_validate(await get_sequence(sequence_id, membership, session))


@router.patch("/{sequence_id}", response_model=TeachingSequenceRead)
async def update_sequence(
    sequence_id: UUID,
    data: TeachingSequenceUpdate,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> TeachingSequenceRead:
    sequence = await get_sequence(sequence_id, membership, session, require_write=True)
    values = data.model_dump(exclude_unset=True, exclude={"items"})
    if "generation_project_id" in values:
        await validate_generation_project(values["generation_project_id"], membership, session)
    for field, value in values.items():
        setattr(sequence, field, value)
    if data.items is not None:
        await replace_items(sequence, data.items, session)
    await session.commit()
    return TeachingSequenceRead.model_validate(await get_sequence(sequence.id, membership, session))


@router.delete("/{sequence_id}", status_code=204)
async def delete_sequence(
    sequence_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    membership: Membership = Depends(require_roles(*WRITE_ROLES)),
) -> Response:
    sequence = await get_sequence(sequence_id, membership, session, require_write=True)
    await session.delete(sequence)
    await session.commit()
    return Response(status_code=204)
