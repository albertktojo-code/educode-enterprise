from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
def test_migration_chain_and_revision_length():
    text = (
        BACKEND / "alembic/versions/0042_auth_session_security.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0042_auth_session_security"' in text
    assert 'down_revision: str | None = "0041_comic_reader_analytics"' in text
    assert len("0042_auth_session_security") <= 32
    assert 'op.create_table(\n        "auth_sessions"' in text
    assert 'op.create_table(\n        "password_reset_tokens"' in text


def test_auth_uses_canonical_user_and_security_events():
    models = (BACKEND / "app/models/auth.py").read_text(encoding="utf-8")
    routes = (BACKEND / "app/api/v1/routes_auth.py").read_text(encoding="utf-8")
    assert 'class AuthSession(Base)' in models
    assert 'class PasswordResetToken(Base)' in models
    assert 'append_security_event' in routes
    assert 'auth_users' not in models
    assert 'user_sessions_v2' not in models


def test_refresh_tokens_are_server_side_and_cookie_based():
    routes = (BACKEND / "app/api/v1/routes_auth.py").read_text(encoding="utf-8")
    security = (BACKEND / "app/core/security.py").read_text(encoding="utf-8")
    assert 'set_refresh_cookie' in routes
    assert 'refresh_token=None' in routes
    assert 'new_opaque_token' in security
    assert 'sid' in security
    assert 'ver' in security


def test_auth_routes_expose_recovery_and_session_management():
    routes = (BACKEND / "app/api/v1/routes_auth.py").read_text(encoding="utf-8")
    for route in (
        '"/forgot-password"',
        '"/reset-password"',
        '"/sessions"',
        '"/sessions/{session_id}"',
        '"/sessions/revoke-all"',
    ):
        assert route in routes
    assert "GENERIC_RESET_MESSAGE" in routes
    assert "set_refresh_cookie" in routes
    assert "clear_refresh_cookie" in routes


def test_config_has_secure_session_controls():
    config = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")
    for setting in (
        "persistent_session_days",
        "auth_cookie_secure",
        "password_reset_expire_minutes",
        "password_reset_rate_limit",
        "auth_mail_delivery_mode",
    ):
        assert setting in config


def test_admin_reset_and_deactivation_revoke_sessions():
    routes = (BACKEND / "app/api/v1/routes_users.py").read_text(encoding="utf-8")
    assert "admin_password_reset" in routes
    assert "account_deactivated" in routes
    assert "revoke_user_sessions" in routes
