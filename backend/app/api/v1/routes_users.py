from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.core.security import hash_password, validate_password_strength
from app.db.session import get_db_session
from app.models.auth import Membership, OrganizationRole, User
from app.schemas.auth import UserCreate, UserListItem, UserPasswordReset, UserUpdate
from app.services.auth_sessions import revoke_user_sessions
from app.services.platform import append_security_event

router = APIRouter(prefix="/users", tags=["Usuários"])
admin_access = require_roles(OrganizationRole.OWNER, OrganizationRole.ADMIN)


async def get_user_membership(
    user_id: UUID,
    organization_id: UUID,
    session: AsyncSession,
) -> tuple[User, Membership]:
    row = (
        await session.execute(
            select(User, Membership)
            .join(Membership, Membership.user_id == User.id)
            .where(
                User.id == user_id,
                Membership.organization_id == organization_id,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return row[0], row[1]


async def ensure_not_last_owner(
    membership: Membership,
    requested_role: OrganizationRole | None,
    requested_active: bool | None,
    session: AsyncSession,
) -> None:
    removing_owner = membership.role == OrganizationRole.OWNER and (
        (requested_role is not None and requested_role != OrganizationRole.OWNER)
        or requested_active is False
    )
    if not removing_owner:
        return

    owner_count = await session.scalar(
        select(func.count(Membership.id)).where(
            Membership.organization_id == membership.organization_id,
            Membership.role == OrganizationRole.OWNER,
            Membership.is_active.is_(True),
        )
    )
    if (owner_count or 0) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A organização precisa manter pelo menos um proprietário ativo",
        )


def serialize(user: User, membership: Membership) -> UserListItem:
    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active and membership.is_active,
        role=membership.role,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserListItem])
async def list_users(
    membership: Membership = Depends(admin_access),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserListItem]:
    rows = (
        await session.execute(
            select(User, Membership)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.organization_id == membership.organization_id)
            .order_by(User.full_name)
        )
    ).all()
    return [serialize(user, member) for user, member in rows]


@router.post("", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    membership: Membership = Depends(admin_access),
    session: AsyncSession = Depends(get_db_session),
) -> UserListItem:
    try:
        validate_password_strength(data.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    email = data.email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        existing_membership = await session.scalar(
            select(Membership).where(
                Membership.user_id == existing.id,
                Membership.organization_id == membership.organization_id,
            )
        )
        if existing_membership is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="E-mail já cadastrado nesta organização",
            )
        member = Membership(
            user_id=existing.id,
            organization_id=membership.organization_id,
            role=data.role,
            is_active=True,
        )
        existing.is_active = True
        session.add(member)
        await session.commit()
        return serialize(existing, member)

    user = User(
        email=email,
        full_name=data.full_name.strip(),
        hashed_password=hash_password(data.password),
    )
    session.add(user)
    await session.flush()

    member = Membership(
        user_id=user.id,
        organization_id=membership.organization_id,
        role=data.role,
    )
    session.add(member)
    await session.commit()
    await session.refresh(user)
    return serialize(user, member)


@router.patch("/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    membership: Membership = Depends(admin_access),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserListItem:
    user, target_membership = await get_user_membership(
        user_id,
        membership.organization_id,
        session,
    )
    await ensure_not_last_owner(
        target_membership,
        data.role,
        data.is_active,
        session,
    )

    if user.id == current_user.id and data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar sua própria conta",
        )

    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.role is not None:
        target_membership.role = data.role
    if data.is_active is not None:
        target_membership.is_active = data.is_active
        user.is_active = data.is_active
        if data.is_active is False:
            user.auth_epoch += 1
            await revoke_user_sessions(
                session,
                user_id=user.id,
                reason="account_deactivated",
            )

    await session.commit()
    await session.refresh(user)
    return serialize(user, target_membership)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_password(
    user_id: UUID,
    data: UserPasswordReset,
    request: Request,
    membership: Membership = Depends(admin_access),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        validate_password_strength(data.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user, _ = await get_user_membership(user_id, membership.organization_id, session)
    user.hashed_password = hash_password(data.new_password)
    user.auth_epoch += 1
    user.password_changed_at = datetime.now(UTC)
    revoked = await revoke_user_sessions(
        session,
        user_id=user.id,
        reason="admin_password_reset",
    )
    await append_security_event(
        session,
        organization_id=membership.organization_id,
        user_id=user.id,
        event_type="auth.password_reset.admin_completed",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
        details={
            "administrator_user_id": str(current_user.id),
            "revoked_sessions": revoked,
        },
    )
    await session.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: UUID,
    membership: Membership = Depends(admin_access),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode remover seu próprio acesso",
        )

    user, target_membership = await get_user_membership(
        user_id,
        membership.organization_id,
        session,
    )
    await ensure_not_last_owner(target_membership, OrganizationRole.MEMBER, False, session)

    await session.delete(target_membership)
    remaining = await session.scalar(
        select(func.count(Membership.id)).where(Membership.user_id == user.id)
    )
    if (remaining or 0) <= 1:
        user.is_active = False
        user.auth_epoch += 1
        await revoke_user_sessions(
            session,
            user_id=user.id,
            reason="user_access_removed",
        )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
