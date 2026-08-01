from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0042_auth_session_security"
down_revision: str | None = "0041_comic_reader_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_epoch", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "previous_refresh_token_hash",
            sa.String(64),
            nullable=True,
            unique=True,
        ),
        sa.Column(
            "legacy_refresh_token_hash",
            sa.String(64),
            nullable=True,
            unique=True,
        ),
        sa.Column("remember_me", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rotation_counter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("device_name", sa.String(180), nullable=False, server_default="Navegador"),
        sa.Column("user_agent", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_ip_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("last_ip_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("last_ip_masked", sa.String(80), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(100), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_auth_sessions_user_active",
        "auth_sessions",
        ["user_id", "revoked_at", "expires_at"],
    )
    op.create_index("ix_auth_sessions_family", "auth_sessions", ["family_id"])
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index(
        "ix_auth_sessions_organization_id",
        "auth_sessions",
        ["organization_id"],
    )
    op.create_index(
        "ix_auth_sessions_refresh_token_hash",
        "auth_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auth_sessions_previous_refresh_token_hash",
        "auth_sessions",
        ["previous_refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auth_sessions_legacy_refresh_token_hash",
        "auth_sessions",
        ["legacy_refresh_token_hash"],
        unique=True,
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("requested_email_hash", sa.String(64), nullable=False),
        sa.Column("requested_ip_hash", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(500), nullable=False, server_default=""),
        sa.Column("delivery_method", sa.String(30), nullable=False, server_default="file"),
        sa.Column("delivery_status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_password_reset_user_active",
        "password_reset_tokens",
        ["user_id", "used_at", "expires_at"],
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("auth_sessions")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "auth_epoch")
