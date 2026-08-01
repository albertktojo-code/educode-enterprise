from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    describe_device,
    hash_secret,
    mask_ip,
    new_opaque_token,
    validate_password_strength,
)


def test_access_token_contains_session_and_epoch():
    user_id = uuid4()
    session_id = uuid4()
    token = create_access_token(
        user_id,
        session_id=session_id,
        auth_epoch=4,
    )
    payload = decode_token(token, "access")
    assert payload["sub"] == str(user_id)
    assert payload["sid"] == str(session_id)
    assert payload["ver"] == 4


def test_opaque_tokens_are_hashed_and_unique():
    first = new_opaque_token()
    second = new_opaque_token()
    assert first != second
    assert len(first) >= 40
    assert len(hash_secret(first)) == 64
    assert hash_secret(first) != hash_secret(second)


def test_password_strength():
    validate_password_strength("Senha@Forte123")
    with pytest.raises(ValueError):
        validate_password_strength("fraca123")


def test_masking_and_device_description():
    assert mask_ip("192.168.10.52") == "192.168.10.x"
    assert "Chrome" in describe_device(
        "Mozilla/5.0 (Windows NT 10.0) Chrome/150.0"
    )
