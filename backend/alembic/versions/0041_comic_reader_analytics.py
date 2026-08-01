from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0041_comic_reader_analytics"
down_revision: str | None = "0040_comic_reader_access"
branch_labels = None
depends_on = None


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def uid(name: str, nullable: bool = False):
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "comic_reader_events",
        uid("id"), uid("organization_id"), uid("release_id"), uid("user_id"),
        uid("presentation_session_id", True),
        sa.Column("client_event_id", sa.String(80), nullable=False),
        sa.Column("session_key", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("panel_number", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("properties", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["presentation_session_id"], ["comic_presentation_sessions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "user_id", "client_event_id", name="uq_comic_reader_event_client"),
    )
    op.create_index(
        "ix_comic_reader_event_release_time",
        "comic_reader_events",
        ["organization_id", "release_id", "occurred_at"],
    )

    op.create_table(
        "comic_reader_session_metrics",
        uid("id"), uid("organization_id"), uid("release_id"), uid("user_id"),
        sa.Column("session_key", sa.String(80), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("panel_views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revisits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("glossary_opens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("narration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accessibility_actions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assessment_opens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("presentation_syncs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organization_id", "release_id", "user_id", "session_key",
            name="uq_comic_reader_session_metric",
        ),
    )
    op.create_index(
        "ix_comic_reader_session_period",
        "comic_reader_session_metrics",
        ["organization_id", "release_id", "started_at"],
    )

    op.create_table(
        "comic_reader_content_metrics",
        uid("id"), uid("organization_id"), uid("release_id"),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("dimension_key", sa.String(80), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("panel_number", sa.Integer(), nullable=True),
        sa.Column("viewer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revisit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_active_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("glossary_opens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("narration_starts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assessment_opens", sa.Integer(), nullable=False, server_default="0"),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organization_id", "release_id", "metric_date", "dimension_key",
            name="uq_comic_reader_content_metric",
        ),
    )

    op.create_table(
        "comic_reader_cohort_metrics",
        uid("id"), uid("organization_id"), uid("classroom_id"), uid("release_id"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("enrolled_students", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_students", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_students", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_active_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("median_progress_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("presentation_participants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("narration_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accessibility_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("privacy_suppressed", sa.Boolean(), nullable=False, server_default=sa.false()),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["classroom_id"], ["classrooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organization_id", "classroom_id", "release_id", "period_start", "period_end",
            name="uq_comic_reader_cohort_metric",
        ),
    )

    op.create_table(
        "comic_reader_learning_metrics",
        uid("id"), uid("organization_id"),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_key", sa.String(80), nullable=False),
        uid("scope_id", True), uid("release_id"), uid("assignment_id"),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_active_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_progress_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("average_score_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reading_score_correlation", sa.Float(), nullable=True),
        sa.Column("completion_score_delta", sa.Float(), nullable=True),
        sa.Column("interpretation", sa.String(80), nullable=False, server_default="INSUFFICIENT_DATA"),
        sa.Column("privacy_suppressed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["comic_editorial_releases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["material_assignments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "organization_id", "scope_key", "release_id", "assignment_id",
            "period_start", "period_end",
            name="uq_comic_reader_learning_metric",
        ),
    )


def downgrade() -> None:
    for table_name in (
        "comic_reader_learning_metrics",
        "comic_reader_cohort_metrics",
        "comic_reader_content_metrics",
        "comic_reader_session_metrics",
        "comic_reader_events",
    ):
        op.drop_table(table_name)
