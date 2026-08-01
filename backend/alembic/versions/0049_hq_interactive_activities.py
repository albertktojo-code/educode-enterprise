from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0049_hq_interactive_activities"
down_revision: str | None = "0048_comic_editorial_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hq_activity_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_panel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("publication_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("activity_type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("activity_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("answer_key", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("pedagogical_links", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("accessibility", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("difficulty", sa.String(24), nullable=False, server_default="BASIC"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_score", sa.Float(), nullable=False, server_default="1"),
        sa.Column("teacher_review_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "activity_type IN ('MULTIPLE_CHOICE','TRUE_FALSE','MATCHING','ORDERING','FILL_BLANKS','CROSSWORD','WORD_SEARCH','SHORT_ANSWER','ESSAY','COMPUTATIONAL_THINKING','MATHEMATICS')",
            name="ck_hq_activity_type",
        ),
        sa.CheckConstraint(
            "difficulty IN ('INTRODUCTORY','BASIC','INTERMEDIATE','ADVANCED','CHALLENGE')",
            name="ck_hq_activity_difficulty",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT','IN_REVIEW','APPROVED','PUBLISHED','ARCHIVED')",
            name="ck_hq_activity_status",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "activity_page_id",
            "display_order",
            name="uq_hq_activity_page_order",
        ),
    )
    op.create_index(
        "ix_hq_activity_project_status",
        "hq_activity_bindings",
        ["organization_id", "comic_project_id", "status", "display_order"],
    )
    op.create_index(
        "ix_hq_activity_question_version",
        "hq_activity_bindings",
        ["organization_id", "question_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hq_activity_question_version", table_name="hq_activity_bindings")
    op.drop_index("ix_hq_activity_project_status", table_name="hq_activity_bindings")
    op.drop_table("hq_activity_bindings")
