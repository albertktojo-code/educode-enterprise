from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    hash_secret,
    new_opaque_token,
    validate_password_strength,
    verify_password,
)
from app.db.session import get_db_session
from app.models.auth import AuthSession, Membership, PasswordResetToken, User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    MembershipSummary,
    OrganizationSummary,
    ProfileUpdate,
    RefreshRequest,
    ResetPasswordRequest,
    RevokeAllSessionsRequest,
    SessionRead,
    TokenPair,
    UserMe,
)
from app.services.auth_sessions import (
    GENERIC_RESET_MESSAGE,
    allow_reset_request,
    build_reset_url,
    clear_refresh_cookie,
    create_session,
    deliver_password_reset_task,
    find_session_by_refresh,
    first_organization_id,
    invalidate_reset_tokens,
    refresh_cookie_name,
    request_ip,
    revoke_session,
    revoke_user_sessions,
    rotate_session,
    session_is_active,
    set_refresh_cookie,
)
from app.services.platform import append_security_event

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def serialize_user(user: User) -> UserMe:
    return UserMe(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        memberships=[
            MembershipSummary(
                id=membership.id,
                role=membership.role,
                organization=OrganizationSummary.model_validate(membership.organization),
            )
            for membership in user.memberships
            if membership.is_active and membership.organization.is_active
        ],
    )


def request_session_id(request: Request) -> UUID | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = decode_token(authorization.split(" ", 1)[1], "access")
        return UUID(payload["sid"]) if payload.get("sid") else None
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def token_pair(user: User, auth_session: AuthSession) -> TokenPair:
    settings = get_settings()
    return TokenPair(
        access_token=create_access_token(
            user.id,
            session_id=auth_session.id,
            auth_epoch=user.auth_epoch,
        ),
        refresh_token=None,
        expires_in=settings.access_token_expire_minutes * 60,
        session_id=auth_session.id,
        remember_me=auth_session.remember_me,
    )


@router.post("/login", response_model=TokenPair)
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPair:
    result = await session.execute(
        select(User)
        .where(User.email == data.email.lower())
        .options(selectinload(User.memberships).selectinload(Membership.organization))
    )
    user = result.scalar_one_or_none()
    valid = bool(
        user is not None
        and user.is_active
        and verify_password(data.password, user.hashed_password)
    )
    organization_id = first_organization_id(user) if user else None
    await append_security_event(
        session,
        organization_id=organization_id,
        user_id=user.id if user else None,
        event_type="auth.login_succeeded" if valid else "auth.login_failed",
        severity="info" if valid else "warning",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={
            "email_domain": data.email.split("@")[-1].lower(),
            "remember_me": data.remember_me if valid else False,
        },
    )
    if not valid:
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    auth_session, raw_refresh = await create_session(
        session,
        user=user,
        organization_id=organization_id,
        remember_me=data.remember_me,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )
    await append_security_event(
        session,
        organization_id=organization_id,
        user_id=user.id,
        event_type="auth.session.created",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={
            "session_id": str(auth_session.id),
            "remember_me": data.remember_me,
        },
    )
    if data.remember_me:
        await append_security_event(
            session,
            organization_id=organization_id,
            user_id=user.id,
            event_type="auth.login.remember_me",
            request_id=getattr(request.state, "request_id", ""),
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            details={"session_id": str(auth_session.id)},
        )
    await session.commit()
    set_refresh_cookie(response, raw_refresh, data.remember_me)
    return token_pair(user, auth_session)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    request: Request,
    response: Response,
    data: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPair:
    raw_refresh = request.cookies.get(refresh_cookie_name()) or (
        data.refresh_token if data else None
    )
    if not raw_refresh:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Sessão expirada")

    auth_session, reused_previous = await find_session_by_refresh(session, raw_refresh)
    user: User | None = None

    if auth_session is None:
        # Upgrade path for refresh JWTs issued before Sprint 16.6.1.
        try:
            payload = decode_token(raw_refresh, "refresh")
            user_id = UUID(payload["sub"])
            legacy_epoch = int(payload.get("ver", 0))
        except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
            clear_refresh_cookie(response)
            raise HTTPException(status_code=401, detail="Sessão expirada") from exc
        result = await session.execute(
            select(User)
            .where(User.id == user_id, User.is_active.is_(True))
            .options(selectinload(User.memberships).selectinload(Membership.organization))
        )
        user = result.scalar_one_or_none()
        if user is None or user.auth_epoch != legacy_epoch:
            clear_refresh_cookie(response)
            raise HTTPException(status_code=401, detail="Sessão expirada")
        auth_session, new_refresh = await create_session(
            session,
            user=user,
            organization_id=first_organization_id(user),
            remember_me=False,
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        # The legacy JWT hash remains blacklisted after all future rotations.
        auth_session.legacy_refresh_token_hash = hash_secret(raw_refresh)
    else:
        user = await session.scalar(
            select(User).where(User.id == auth_session.user_id, User.is_active.is_(True))
        )
        if reused_previous:
            await revoke_session(auth_session, reason="refresh_token_reuse")
            await append_security_event(
                session,
                organization_id=auth_session.organization_id,
                user_id=auth_session.user_id,
                event_type="auth.session.refresh_reuse_detected",
                severity="critical",
                request_id=getattr(request.state, "request_id", ""),
                ip_address=request_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                details={"session_id": str(auth_session.id)},
            )
            await session.commit()
            clear_refresh_cookie(response)
            raise HTTPException(status_code=401, detail="Sessão revogada")
        if user is None or not session_is_active(auth_session):
            await revoke_session(auth_session, reason="expired_or_invalid")
            await session.commit()
            clear_refresh_cookie(response)
            raise HTTPException(status_code=401, detail="Sessão expirada")
        new_refresh = await rotate_session(
            session,
            item=auth_session,
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )

    await append_security_event(
        session,
        organization_id=auth_session.organization_id,
        user_id=auth_session.user_id,
        event_type="auth.session.refreshed",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={
            "session_id": str(auth_session.id),
            "rotation_counter": auth_session.rotation_counter,
        },
    )
    await session.commit()
    set_refresh_cookie(response, new_refresh, auth_session.remember_me)
    return token_pair(user, auth_session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    raw_refresh = request.cookies.get(refresh_cookie_name())
    auth_session = None
    if raw_refresh:
        auth_session, _ = await find_session_by_refresh(session, raw_refresh)
    if auth_session is None:
        access_session_id = request_session_id(request)
        if access_session_id:
            auth_session = await session.scalar(
                select(AuthSession).where(AuthSession.id == access_session_id)
            )
    if auth_session:
        await revoke_session(auth_session, reason="user_logout")
        await append_security_event(
            session,
            organization_id=auth_session.organization_id,
            user_id=auth_session.user_id,
            event_type="auth.session.revoked",
            request_id=getattr(request.state, "request_id", ""),
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            details={"session_id": str(auth_session.id), "reason": "logout"},
        )
        await session.commit()
    clear_refresh_cookie(response)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
) -> ForgotPasswordResponse:
    email = data.email.lower()
    ip_address = request_ip(request)
    allowed = await allow_reset_request(email, ip_address)
    result = await session.execute(
        select(User)
        .where(User.email == email, User.is_active.is_(True))
        .options(selectinload(User.memberships).selectinload(Membership.organization))
    )
    user = result.scalar_one_or_none()
    organization_id = first_organization_id(user) if user else None

    await append_security_event(
        session,
        organization_id=organization_id,
        user_id=user.id if user else None,
        event_type=(
            "auth.password_reset.requested"
            if allowed
            else "auth.password_reset.rate_limited"
        ),
        severity="info" if allowed else "warning",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", ""),
        details={"email_domain": email.split("@")[-1]},
    )

    if allowed and user:
        await invalidate_reset_tokens(session, user_id=user.id)
        raw_token = new_opaque_token()
        now = datetime.now(UTC)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_secret(raw_token),
            requested_email_hash=hashlib.sha256(email.encode("utf-8")).hexdigest(),
            requested_ip_hash=hashlib.sha256(ip_address.encode("utf-8")).hexdigest(),
            user_agent=request.headers.get("user-agent", "")[:500],
            expires_at=now + timedelta(
                minutes=get_settings().password_reset_expire_minutes
            ),
        )
        session.add(reset_token)
        await session.flush()
        background_tasks.add_task(
            deliver_password_reset_task,
            reset_token_id=reset_token.id,
            recipient=user.email,
            reset_url=build_reset_url(raw_token),
            organization_id=organization_id,
            user_id=user.id,
            request_id=getattr(request.state, "request_id", ""),
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent", ""),
        )
    await session.commit()
    return ForgotPasswordResponse(message=GENERIC_RESET_MESSAGE)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        validate_password_strength(data.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    reset_token = await session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_secret(data.token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    valid = bool(
        reset_token
        and reset_token.used_at is None
        and reset_token.invalidated_at is None
        and reset_token.expires_at > now
    )
    user = (
        await session.scalar(select(User).where(User.id == reset_token.user_id))
        if reset_token
        else None
    )
    if not valid or user is None or not user.is_active:
        await append_security_event(
            session,
            organization_id=None,
            user_id=user.id if user else None,
            event_type="auth.password_reset.invalid_token",
            severity="warning",
            request_id=getattr(request.state, "request_id", ""),
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        await session.commit()
        clear_refresh_cookie(response)
        raise HTTPException(status_code=400, detail="Link inválido ou expirado.")

    if verify_password(data.new_password, user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ser diferente da senha atual.",
        )

    user.hashed_password = hash_password(data.new_password)
    user.auth_epoch += 1
    user.password_changed_at = now
    reset_token.used_at = now
    await invalidate_reset_tokens(session, user_id=user.id)
    revoked = await revoke_user_sessions(
        session,
        user_id=user.id,
        reason="password_reset",
    )
    organization_id = await session.scalar(
        select(Membership.organization_id)
        .where(Membership.user_id == user.id, Membership.is_active.is_(True))
        .limit(1)
    )
    await append_security_event(
        session,
        organization_id=organization_id,
        user_id=user.id,
        event_type="auth.password_reset.completed",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={"revoked_sessions": revoked},
    )
    await session.commit()
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserMe)
async def me(current_user: User = Depends(get_current_user)) -> UserMe:
    return serialize_user(current_user)


@router.patch("/me", response_model=UserMe)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserMe:
    current_user.full_name = data.full_name.strip()
    await session.commit()
    await session.refresh(current_user)
    return serialize_user(current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="A senha atual está incorreta")
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ser diferente da senha atual",
        )
    try:
        validate_password_strength(data.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    current_user.hashed_password = hash_password(data.new_password)
    current_user.auth_epoch += 1
    current_user.password_changed_at = datetime.now(UTC)
    revoked = await revoke_user_sessions(
        session,
        user_id=current_user.id,
        reason="password_changed",
    )
    organization_id = await session.scalar(
        select(Membership.organization_id)
        .where(
            Membership.user_id == current_user.id,
            Membership.is_active.is_(True),
        )
        .limit(1)
    )
    await append_security_event(
        session,
        organization_id=organization_id,
        user_id=current_user.id,
        event_type="auth.password_changed",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={"revoked_sessions": revoked},
    )
    await session.commit()
    clear_refresh_cookie(response)


@router.get("/sessions", response_model=list[SessionRead])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SessionRead]:
    current_session_id = request_session_id(request)
    now = datetime.now(UTC)
    items = list(
        (
            await session.scalars(
                select(AuthSession)
                .where(
                    AuthSession.user_id == current_user.id,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > now,
                    AuthSession.idle_expires_at > now,
                )
                .order_by(AuthSession.last_used_at.desc())
            )
        ).all()
    )
    return [
        SessionRead(
            id=item.id,
            device_name=item.device_name,
            last_ip_masked=item.last_ip_masked,
            remember_me=item.remember_me,
            created_at=item.created_at,
            last_used_at=item.last_used_at,
            expires_at=item.expires_at,
            idle_expires_at=item.idle_expires_at,
            current=item.id == current_session_id,
        )
        for item in items
    ]


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    data: RevokeAllSessionsRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    current_session_id = request_session_id(request)
    revoked = await revoke_user_sessions(
        session,
        user_id=current_user.id,
        reason="user_revoked_all",
        except_session_id=current_session_id if data.keep_current else None,
    )
    organization_id = await session.scalar(
        select(Membership.organization_id)
        .where(
            Membership.user_id == current_user.id,
            Membership.is_active.is_(True),
        )
        .limit(1)
    )
    await append_security_event(
        session,
        organization_id=organization_id,
        user_id=current_user.id,
        event_type="auth.session.revoked_all",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={"revoked_sessions": revoked, "keep_current": data.keep_current},
    )
    await session.commit()
    if not data.keep_current:
        clear_refresh_cookie(response)
    return {"revoked": revoked}

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    item = await session.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == current_user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    await revoke_session(item, reason="user_revoked")
    await append_security_event(
        session,
        organization_id=item.organization_id,
        user_id=current_user.id,
        event_type="auth.session.revoked",
        request_id=getattr(request.state, "request_id", ""),
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        details={"session_id": str(item.id), "reason": "account_security"},
    )
    await session.commit()
    if item.id == request_session_id(request):
        clear_refresh_cookie(response)

