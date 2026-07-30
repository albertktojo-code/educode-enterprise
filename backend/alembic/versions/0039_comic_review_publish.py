from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0039_comic_review_publish"
down_revision: str | None = "0038_comic_visual_library"
branch_labels = None
depends_on = None


def uuid_col(name: str, *, nullable: bool = False):
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "comic_editorial_review_sessions",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("comic_project_id"),
        uuid_col("comic_version_id", nullable=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        uuid_col("created_by_user_id"), *timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_review_session_project", "comic_editorial_review_sessions",
                    ["organization_id", "comic_project_id", "status"])

    op.create_table(
        "comic_editorial_assignments",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("review_session_id"),
        uuid_col("reviewer_user_id"), sa.Column("reviewer_role", sa.String(48), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        uuid_col("assigned_by_user_id"), *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "review_session_id", "reviewer_user_id", "reviewer_role",
                            name="uq_comic_editorial_assignment"),
    )
    op.create_index("ix_comic_editorial_assignments_reviewer", "comic_editorial_assignments",
                    ["organization_id", "reviewer_user_id", "status"])

    op.create_table(
        "comic_editorial_threads",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("review_session_id"),
        sa.Column("anchor_type", sa.String(16), nullable=False),
        uuid_col("page_id", nullable=True), uuid_col("panel_id", nullable=True), uuid_col("layer_id", nullable=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False, server_default="COMMENT"),
        sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uuid_col("created_by_user_id"), uuid_col("resolved_by_user_id", nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=False, server_default=""),
        *timestamps(), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_editorial_threads_session", "comic_editorial_threads",
                    ["organization_id", "review_session_id", "status"])
    op.create_index("ix_comic_editorial_threads_anchor", "comic_editorial_threads",
                    ["organization_id", "page_id", "panel_id", "layer_id"])

    op.create_table(
        "comic_editorial_comments",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("thread_id"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("attachments", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        uuid_col("created_by_user_id"),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_editorial_comments_thread", "comic_editorial_comments",
                    ["organization_id", "thread_id", "created_at"])

    op.create_table(
        "comic_editorial_change_requests",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("review_session_id"),
        uuid_col("thread_id", nullable=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(24), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
        sa.Column("target_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolution_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uuid_col("requested_by_user_id"), uuid_col("resolved_by_user_id", nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_change_requests_session", "comic_editorial_change_requests",
                    ["organization_id", "review_session_id", "status"])

    op.create_table(
        "comic_editorial_checklists",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("review_session_id"),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("completion_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.true()),
        uuid_col("created_by_user_id"), *timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "review_session_id", "name", "version",
                            name="uq_comic_editorial_checklist"),
    )

    op.create_table(
        "comic_editorial_check_items",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("checklist_id"),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("label", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uuid_col("reviewed_by_user_id", nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "checklist_id", "code",
                            name="uq_comic_editorial_check_item"),
    )
    op.create_index("ix_comic_editorial_check_items_status", "comic_editorial_check_items",
                    ["organization_id", "checklist_id", "status"])

    op.create_table(
        "comic_editorial_workflows",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("review_session_id"),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("minimum_approvals", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("required_roles", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="IN_REVIEW"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uuid_col("created_by_user_id"), *timestamps(), sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_editorial_workflow_session", "comic_editorial_workflows",
                    ["organization_id", "review_session_id", "status"])

    op.create_table(
        "comic_editorial_decisions",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("workflow_id"),
        uuid_col("reviewer_user_id"),
        sa.Column("reviewer_role", sa.String(48), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *timestamps(), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "workflow_id", "reviewer_user_id",
                            name="uq_comic_editorial_decision_reviewer"),
    )
    op.create_index("ix_comic_editorial_decisions_workflow", "comic_editorial_decisions",
                    ["organization_id", "workflow_id", "decision"])

    op.create_table(
        "comic_editorial_releases",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("comic_project_id"),
        uuid_col("source_version_id"), uuid_col("review_session_id"),
        sa.Column("release_number", sa.Integer(), nullable=False),
        sa.Column("release_name", sa.String(180), nullable=False),
        sa.Column("release_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("release_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        uuid_col("created_by_user_id"), *timestamps(), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "comic_project_id", "release_number",
                            name="uq_comic_editorial_release_number"),
    )
    op.create_index("ix_comic_editorial_releases_project", "comic_editorial_releases",
                    ["organization_id", "comic_project_id", "status"])

    op.create_table(
        "comic_editorial_release_targets",
        uuid_col("id"), uuid_col("organization_id"), uuid_col("release_id"),
        sa.Column("target_type", sa.String(32), nullable=False),
        uuid_col("target_id", nullable=True),
        sa.Column("availability_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("availability_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        uuid_col("created_by_user_id"), *timestamps(), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "release_id", "target_type", "target_id",
                            name="uq_comic_editorial_release_target"),
    )
    op.create_index("ix_comic_release_targets_availability", "comic_editorial_release_targets",
                    ["organization_id", "target_type", "availability_from"])


def downgrade() -> None:
    for table in [
        "comic_editorial_release_targets",
        "comic_editorial_releases",
        "comic_editorial_decisions",
        "comic_editorial_workflows",
        "comic_editorial_check_items",
        "comic_editorial_checklists",
        "comic_editorial_change_requests",
        "comic_editorial_comments",
        "comic_editorial_threads",
        "comic_editorial_assignments",
        "comic_editorial_review_sessions",
    ]:
        op.drop_table(table)
