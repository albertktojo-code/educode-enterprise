from __future__ import annotations

import asyncio
import hashlib
import smtplib
import time
import uuid
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    describe_device,
    hash_secret,
    mask_ip,
    new_opaque_token,
)
from app.db.session import AsyncSessionFactory
from app.models.auth import AuthSession, PasswordResetToken, User
from app.services.platform import append_security_event


GENERIC_RESET_MESSAGE = (
    "Se o endereço estiver cadastrado, você receberá as instruções "
    "para redefinir sua senha."
)


def first_organization_id(user: User) -> uuid.UUID | None:
    for membership in user.memberships:
        if membership.is_active and membership.organization.is_active:
            return membership.organization_id
    return None


def request_ip(request: Any) -> str:
    return request.client.host if request.client else ""


def refresh_cookie_name() -> str:
    return get_settings().auth_refresh_cookie_name


def set_refresh_cookie(response: Any, raw_token: str, remember_me: bool) -> None:
    settings = get_settings()
    max_age = (
        settings.persistent_session_days * 24 * 60 * 60
        if remember_me
        else None
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=raw_token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=settings.auth_refresh_cookie_path,
    )


def clear_refresh_cookie(response: Any) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_refresh_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )


async def create_session(
    session: AsyncSession,
    *,
    user: User,
    organization_id: uuid.UUID | None,
    remember_me: bool,
    ip_address: str,
    user_agent: str,
) -> tuple[AuthSession, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    absolute_delta = timedelta(
        days=settings.persistent_session_days
        if remember_me
        else settings.standard_session_hours / 24
    )
    idle_delta = timedelta(
        days=settings.persistent_session_idle_days
        if remember_me
        else settings.standard_session_idle_hours / 24
    )
    raw_token = new_opaque_token()
    item = AuthSession(
        user_id=user.id,
        organization_id=organization_id,
        refresh_token_hash=hash_secret(raw_token),
        remember_me=remember_me,
        device_name=describe_device(user_agent),
        user_agent=user_agent[:500],
        created_ip_hash=hash_secret(ip_address),
        last_ip_hash=hash_secret(ip_address),
        last_ip_masked=mask_ip(ip_address),
        created_at=now,
        last_used_at=now,
        expires_at=now + absolute_delta,
        idle_expires_at=now + idle_delta,
    )
    session.add(item)
    await session.flush()
    return item, raw_token


async def find_session_by_refresh(
    session: AsyncSession,
    raw_token: str,
) -> tuple[AuthSession | None, bool]:
    token_hash = hash_secret(raw_token)
    item = await session.scalar(
        select(AuthSession)
        .where(
            or_(
                AuthSession.refresh_token_hash == token_hash,
                AuthSession.previous_refresh_token_hash == token_hash,
                AuthSession.legacy_refresh_token_hash == token_hash,
            )
        )
        .with_for_update()
    )
    reused_previous = bool(
        item is not None
        and token_hash in {
            item.previous_refresh_token_hash,
            item.legacy_refresh_token_hash,
        }
    )
    return item, reused_previous


def session_is_active(item: AuthSession, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    return (
        item.revoked_at is None
        and item.expires_at > current
        and item.idle_expires_at > current
    )


async def rotate_session(
    session: AsyncSession,
    *,
    item: AuthSession,
    ip_address: str,
    user_agent: str,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    raw_token = new_opaque_token()
    item.previous_refresh_token_hash = item.refresh_token_hash
    item.refresh_token_hash = hash_secret(raw_token)
    item.rotation_counter += 1
    item.last_used_at = now
    item.last_ip_hash = hash_secret(ip_address)
    item.last_ip_masked = mask_ip(ip_address)
    item.user_agent = user_agent[:500]
    item.device_name = describe_device(user_agent)
    idle_delta = timedelta(
        days=settings.persistent_session_idle_days
        if item.remember_me
        else settings.standard_session_idle_hours / 24
    )
    item.idle_expires_at = min(item.expires_at, now + idle_delta)
    await session.flush()
    return raw_token


async def revoke_session(
    item: AuthSession,
    *,
    reason: str,
) -> None:
    if item.revoked_at is None:
        item.revoked_at = datetime.now(UTC)
        item.revoke_reason = reason[:100]


async def revoke_user_sessions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    reason: str,
    except_session_id: uuid.UUID | None = None,
) -> int:
    query = (
        update(AuthSession)
        .where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .values(
            revoked_at=datetime.now(UTC),
            revoke_reason=reason[:100],
        )
    )
    if except_session_id:
        query = query.where(AuthSession.id != except_session_id)
    result = await session.execute(query)
    return int(result.rowcount or 0)


async def invalidate_reset_tokens(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.invalidated_at.is_(None),
        )
        .values(invalidated_at=datetime.now(UTC))
    )


async def allow_reset_request(email: str, ip_address: str) -> bool:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    email_hash = hashlib.sha256(email.lower().encode("utf-8")).hexdigest()
    ip_hash = hashlib.sha256(ip_address.encode("utf-8")).hexdigest()
    keys = (
        f"{settings.job_queue_prefix}:password-reset:email:{email_hash}",
        f"{settings.job_queue_prefix}:password-reset:ip:{ip_hash}",
    )
    try:
        counts = []
        for key in keys:
            count = int(await redis.incr(key))
            if count == 1:
                await redis.expire(key, settings.password_reset_rate_window_minutes * 60)
            counts.append(count)
        return all(count <= settings.password_reset_rate_limit for count in counts)
    except RedisError:
        # Global middleware still protects the endpoint when Redis is unavailable.
        return True
    finally:
        await redis.aclose()


def build_reset_url(raw_token: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/reset-password?token={raw_token}"


def _write_reset_mail(recipient: str, reset_url: str) -> Path:
    settings = get_settings()
    outbox = Path(settings.auth_mail_outbox_path)
    outbox.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - (24 * 60 * 60)
    for stale in outbox.glob("password-reset-*.txt"):
        try:
            if stale.stat().st_mtime < cutoff:
                stale.unlink()
        except OSError:
            pass
    file_path = outbox / f"password-reset-{uuid.uuid4()}.txt"
    file_path.write_text(
        (
            "EduCode Enterprise 2.0\n"
            "Redefinição de senha\n\n"
            f"Destinatário: {recipient}\n\n"
            "Use o link abaixo dentro do prazo configurado:\n"
            f"{reset_url}\n\n"
            "Caso você não tenha solicitado, ignore esta mensagem.\n"
        ),
        encoding="utf-8",
    )
    try:
        file_path.chmod(0o600)
    except OSError:
        pass
    return file_path


def _send_smtp(recipient: str, reset_url: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = "Redefinição de senha — EduCode"
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message.set_content(
        "Use o link abaixo para redefinir sua senha:\n\n"
        f"{reset_url}\n\n"
        "Caso você não tenha solicitado, ignore esta mensagem."
    )
    if settings.smtp_use_ssl:
        client: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        )
    else:
        client = smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        )
    try:
        if settings.smtp_use_starttls and not settings.smtp_use_ssl:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)
    finally:
        client.quit()


async def deliver_password_reset(recipient: str, reset_url: str) -> str:
    settings = get_settings()
    if settings.auth_mail_delivery_mode == "file":
        await asyncio.to_thread(_write_reset_mail, recipient, reset_url)
        return "file"
    if settings.auth_mail_delivery_mode == "smtp":
        if not settings.smtp_host or not settings.smtp_from_email:
            raise RuntimeError("SMTP não configurado.")
        await asyncio.to_thread(_send_smtp, recipient, reset_url)
        return "smtp"
    raise RuntimeError("Entrega de e-mail de recuperação desabilitada.")


async def deliver_password_reset_task(
    *,
    reset_token_id: uuid.UUID,
    recipient: str,
    reset_url: str,
    organization_id: uuid.UUID | None,
    user_id: uuid.UUID,
    request_id: str,
    ip_address: str,
    user_agent: str,
) -> None:
    try:
        method = await deliver_password_reset(recipient, reset_url)
        status = "delivered"
    except Exception:
        method = get_settings().auth_mail_delivery_mode
        status = "failed"

    async with AsyncSessionFactory() as database:
        item = await database.get(PasswordResetToken, reset_token_id)
        if item is None:
            return
        item.delivery_method = method
        item.delivery_status = status
        if status == "delivered":
            item.delivered_at = datetime.now(UTC)
        else:
            item.invalidated_at = datetime.now(UTC)
            await append_security_event(
                database,
                organization_id=organization_id,
                user_id=user_id,
                event_type="auth.password_reset.delivery_failed",
                severity="error",
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        await database.commit()
