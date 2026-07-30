from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0052_hq_student_experience"
down_revision: str | None = "0051_hq_activity_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_student_experience_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessment_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("release_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_stage", sa.String(24), nullable=False, server_default="READING"),
        sa.Column("current_page_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_panel_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_activity_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reading_progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("activity_progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_activity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resume_token", sa.String(96), nullable=False),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("navigation_state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_feedback", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "current_stage IN ('READING','ACTIVITY','FEEDBACK','COMPLETED')",
            name="ck_hq_student_experience_stage",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "publication_id",
            "student_id",
            name="uq_hq_student_experience_publication",
        ),
    )
    op.create_index(
        "ix_hq_student_experience_progress",
        "hq_student_experience_states",
        ["organization_id", "publication_id", "current_stage", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hq_student_experience_progress",
        table_name="hq_student_experience_states",
    )
    op.drop_table("hq_student_experience_states")
