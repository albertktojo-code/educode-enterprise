from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.auth import AuthSession, Membership, OrganizationRole, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, "access")
        user_id = UUID(payload["sub"])
        token_epoch = int(payload.get("ver", 0))
        session_id = UUID(payload["sid"]) if payload.get("sid") else None
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise credentials_error from exc

    result = await session.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.memberships).selectinload(Membership.organization))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or user.auth_epoch != token_epoch:
        raise credentials_error

    if session_id is not None:
        now = datetime.now(UTC)
        auth_session = await session.scalar(
            select(AuthSession).where(
                AuthSession.id == session_id,
                AuthSession.user_id == user.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                AuthSession.idle_expires_at > now,
            )
        )
        if auth_session is None:
            raise credentials_error
    return user


def require_roles(*roles: OrganizationRole) -> Callable[..., Awaitable[Membership]]:
    async def dependency(
        current_user: User = Depends(get_current_user),
    ) -> Membership:
        active = [
            membership
            for membership in current_user.memberships
            if membership.is_active and membership.organization.is_active
        ]
        membership = next(
            (item for item in active if item.role in roles),
            None,
        )
        if membership is None and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente",
            )
        if membership is None:
            membership = active[0] if active else None
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário sem organização ativa",
            )
        return membership

    return dependency
