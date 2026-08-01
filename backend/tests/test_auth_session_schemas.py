import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    LoginRequest,
    ResetPasswordRequest,
    RevokeAllSessionsRequest,
)


def test_login_remember_me_defaults_to_false():
    item = LoginRequest(email="user@example.com", password="Admin@123456")
    assert item.remember_me is False


def test_reset_password_requires_confirmation():
    with pytest.raises(ValidationError):
        ResetPasswordRequest(
            token="x" * 48,
            new_password="Senha@Forte123",
            confirm_password="Senha@Outra123",
        )


def test_revoke_all_keeps_current_by_default():
    assert RevokeAllSessionsRequest().keep_current is True
