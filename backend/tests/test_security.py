from uuid import uuid4

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("Senha@123")
    assert hashed != "Senha@123"
    assert verify_password("Senha@123", hashed)
    assert not verify_password("SenhaErrada", hashed)


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token, "access")
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
