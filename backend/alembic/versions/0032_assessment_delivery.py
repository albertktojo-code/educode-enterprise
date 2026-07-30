"""Sprint 15.2 - assessment delivery and monitored sessions.

Revision ID: 0032_assessment_delivery
Revises: 0031_assessment_hub
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0032_assessment_delivery"
down_revision: str | None = "0031_assessment_hub"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "assessment_delivery_publications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", UUID, nullable=False),
        sa.Column("item_snapshot", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("navigation_mode", sa.String(40), nullable=False, server_default="FREE"),
        sa.Column("shuffle_questions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("shuffle_options", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_resume", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("autosave_seconds", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("delivery_rules", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("access_settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("published_by_user_id", UUID),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "code", "version", name="uq_delivery_publication_version"),
    )
    op.create_index("ix_delivery_publications_window", "assessment_delivery_publications", ["organization_id", "status", "starts_at", "ends_at"])

    op.create_table(
        "assessment_delivery_targets",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("publication_id", UUID, nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", UUID, nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True)),
        sa.Column("available_until", sa.DateTime(timezone=True)),
        sa.Column("extra_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("custom_duration_minutes", sa.Integer()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("assigned_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "publication_id", "target_type", "target_id", name="uq_delivery_target"),
    )
    op.create_index("ix_delivery_targets_lookup", "assessment_delivery_targets", ["organization_id", "target_type", "target_id", "status"])

    op.create_table(
        "assessment_delivery_accommodations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("publication_id", UUID, nullable=False),
        sa.Column("student_id", UUID, nullable=False),
        sa.Column("extra_time_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extra_time_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accessible_version_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("screen_reader_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("high_contrast", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reduced_motion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("keyboard_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("simplified_language", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("custom_settings", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("approved_by_user_id", UUID, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "publication_id", "student_id", name="uq_delivery_accommodation"),
    )
    op.create_index("ix_delivery_accommodation_student", "assessment_delivery_accommodations", ["organization_id", "student_id", "status"])

    op.create_table(
        "assessment_delivery_sessions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("publication_id", UUID, nullable=False),
        sa.Column("target_id", UUID),
        sa.Column("student_id", UUID, nullable=False),
        sa.Column("assessment_hub_attempt_id", UUID, nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="CREATED"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remaining_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_item_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resume_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reconnect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_loss_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("integrity_status", sa.String(30), nullable=False, server_default="NORMAL"),
        sa.Column("delivery_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("accessibility_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("device_context", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
    )
    op.create_index("ix_delivery_sessions_student", "assessment_delivery_sessions", ["organization_id", "student_id", "status", "started_at"])
    op.create_index("ix_delivery_sessions_publication", "assessment_delivery_sessions", ["organization_id", "publication_id", "status"])

    op.create_table(
        "assessment_delivery_session_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("question_version_id", UUID, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("original_position", sa.Integer(), nullable=False),
        sa.Column("option_order", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(30), nullable=False, server_default="NOT_SEEN"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.Column("flagged_for_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "session_id", "position", name="uq_delivery_session_position"),
        sa.UniqueConstraint("organization_id", "session_id", "question_version_id", name="uq_delivery_session_question"),
    )
    op.create_index("ix_delivery_session_items_session", "assessment_delivery_session_items", ["organization_id", "session_id", "status"])

    op.create_table(
        "assessment_delivery_autosaves",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("session_item_id", UUID, nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("response_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("client_timestamp", sa.DateTime(timezone=True)),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACCEPTED"),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("organization_id", "session_id", "sequence_number", name="uq_delivery_autosave_sequence"),
    )
    op.create_index("ix_delivery_autosaves_item", "assessment_delivery_autosaves", ["organization_id", "session_id", "session_item_id", "sequence_number"])

    op.create_table(
        "assessment_delivery_session_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="INFO"),
        sa.Column("source", sa.String(30), nullable=False, server_default="CLIENT"),
        sa.Column("client_sequence", sa.Integer()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", UUID),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("description", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_delivery_events_session", "assessment_delivery_session_events", ["organization_id", "session_id", "occurred_at"])
    op.create_index("ix_delivery_events_review", "assessment_delivery_session_events", ["organization_id", "severity", "event_type"])


def downgrade() -> None:
    for table in [
        "assessment_delivery_session_events",
        "assessment_delivery_autosaves",
        "assessment_delivery_session_items",
        "assessment_delivery_sessions",
        "assessment_delivery_accommodations",
        "assessment_delivery_targets",
        "assessment_delivery_publications",
    ]:
        op.drop_table(table)
