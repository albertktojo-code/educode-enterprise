from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()
TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def validate_password_strength(password: str) -> None:
    settings = get_settings()
    errors: list[str] = []
    if len(password) < settings.password_min_length:
        errors.append(f"mínimo de {settings.password_min_length} caracteres")
    if not any(character.islower() for character in password):
        errors.append("uma letra minúscula")
    if not any(character.isupper() for character in password):
        errors.append("uma letra maiúscula")
    if not any(character.isdigit() for character in password):
        errors.append("um número")
    if not any(not character.isalnum() for character in password):
        errors.append("um caractere especial")
    if errors:
        raise ValueError("A senha deve conter " + ", ".join(errors) + ".")


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def create_token(
    subject: UUID,
    token_type: TokenType,
    expires_delta: timedelta,
    *,
    session_id: UUID | None = None,
    auth_epoch: int = 0,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
        "ver": auth_epoch,
    }
    if session_id is not None:
        payload["sid"] = str(session_id)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: UUID,
    *,
    session_id: UUID | None = None,
    auth_epoch: int = 0,
) -> str:
    return create_token(
        subject,
        "access",
        timedelta(minutes=get_settings().access_token_expire_minutes),
        session_id=session_id,
        auth_epoch=auth_epoch,
    )


def create_refresh_token(subject: UUID) -> str:
    """Legacy JWT refresh token kept only for migration compatibility."""
    return create_token(
        subject,
        "refresh",
        timedelta(days=get_settings().refresh_token_expire_days),
    )


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Tipo de token inválido")
    return payload


def mask_ip(ip_address: str) -> str:
    if not ip_address:
        return ""
    if ":" in ip_address:
        parts = ip_address.split(":")
        return ":".join(parts[:3]) + "::/48"
    parts = ip_address.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".x"
    return "mascarado"


def describe_device(user_agent: str) -> str:
    value = user_agent.lower()
    browser = (
        "Edge" if "edg/" in value else
        "Chrome" if "chrome/" in value else
        "Firefox" if "firefox/" in value else
        "Safari" if "safari/" in value else
        "Navegador"
    )
    system = (
        "Windows" if "windows" in value else
        "Android" if "android" in value else
        "iOS" if "iphone" in value or "ipad" in value else
        "macOS" if "mac os" in value else
        "Linux" if "linux" in value else
        "Dispositivo"
    )
    return f"{browser} em {system}"
