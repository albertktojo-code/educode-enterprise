from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0050_hq_activity_feedback"
down_revision: str | None = "0049_hq_interactive_activities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_activity_feedback_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_binding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rubric_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rubric_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correction_mode", sa.String(24), nullable=False, server_default="AUTOMATIC"),
        sa.Column("feedback_templates", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("graduated_hints", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("common_errors", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("review_rules", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("appeal_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "correction_mode IN ('AUTOMATIC','RUBRIC','ASSISTED','HUMAN')",
            name="ck_hq_feedback_correction_mode",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','IN_REVIEW','APPROVED','ARCHIVED')",
            name="ck_hq_feedback_profile_status",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "activity_binding_id",
            name="uq_hq_activity_feedback_profile",
        ),
    )
    op.create_index(
        "ix_hq_activity_feedback_status",
        "hq_activity_feedback_profiles",
        ["organization_id", "status", "correction_mode"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hq_activity_feedback_status",
        table_name="hq_activity_feedback_profiles",
    )
    op.drop_table("hq_activity_feedback_profiles")
