"""Comic review, controlled regeneration and visual preparation.

Revision ID: 0011_comic_review_control
Revises: 0010_comic_generation_editor
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_comic_review_control"
down_revision: str | None = "0010_comic_generation_editor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

review_specialty = postgresql.ENUM(
    "NARRATIVE", "PEDAGOGICAL", "VISUAL", "ACCESSIBILITY",
    name="comic_review_specialty", create_type=False,
)
review_decision = postgresql.ENUM(
    "PENDING", "APPROVED", "CHANGES_REQUESTED",
    name="comic_review_decision", create_type=False,
)
comment_status = postgresql.ENUM(
    "OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED",
    name="comic_review_comment_status", create_type=False,
)
proposal_status = postgresql.ENUM(
    "PROPOSED", "ACCEPTED", "REJECTED", "SUPERSEDED",
    name="comic_proposal_status", create_type=False,
)
operation_status = postgresql.ENUM(
    "APPLIED", "UNDONE", "REDONE",
    name="comic_edit_operation_status", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        review_specialty, review_decision, comment_status, proposal_status, operation_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.add_column("generated_comics", sa.Column("review_state", postgresql.JSONB(), server_default="{}", nullable=False))
    op.add_column("generated_comics", sa.Column("autosave_revision", sa.Integer(), server_default="0", nullable=False))
    op.add_column("generated_comics", sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("comic_panels", sa.Column("locked_elements", postgresql.JSONB(), server_default="[]", nullable=False))
    op.add_column("comic_panels", sa.Column("visual_prompt", postgresql.JSONB(), server_default="{}", nullable=False))
    op.add_column("comic_panels", sa.Column("frozen_assets", postgresql.JSONB(), server_default="{}", nullable=False))
    op.add_column("comic_panels", sa.Column("pacing", sa.String(length=40), server_default="moderate", nullable=False))
    op.add_column("comic_panels", sa.Column("image_asset_path", sa.String(length=500), nullable=True))
    op.add_column("comic_panels", sa.Column("alt_text", sa.Text(), nullable=True))
    op.add_column("comic_panels", sa.Column("audio_description", sa.Text(), nullable=True))
    op.add_column("comic_panels", sa.Column("text_word_limit", sa.Integer(), server_default="80", nullable=False))

    op.add_column("comic_balloons", sa.Column("is_locked", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("comic_balloons", sa.Column("layer_config", postgresql.JSONB(), server_default="{}", nullable=False))

    op.create_table(
        "comic_review_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Uuid(), nullable=True),
        sa.Column("panel_id", sa.Uuid(), nullable=True),
        sa.Column("balloon_id", sa.Uuid(), nullable=True),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("author_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("specialty", review_specialty, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", comment_status, server_default="OPEN", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["comic_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["panel_id"], ["comic_panels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["balloon_id"], ["comic_balloons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "comic_id", "page_id", "panel_id", "balloon_id", "author_user_id"):
        op.create_index(f"ix_comic_review_comments_{column}", "comic_review_comments", [column])

    op.create_table(
        "comic_review_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("specialty", review_specialty, nullable=False),
        sa.Column("decision", review_decision, server_default="PENDING", nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comic_id", "specialty", name="uq_comic_review_specialty"),
    )
    op.create_index("ix_comic_review_approvals_comic_id", "comic_review_approvals", ["comic_id"])
    op.create_index("ix_comic_review_approvals_reviewer_user_id", "comic_review_approvals", ["reviewer_user_id"])

    op.create_table(
        "comic_regeneration_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", postgresql.ENUM(name="comic_generation_scope", create_type=False), nullable=False),
        sa.Column("target_page_id", sa.Uuid(), nullable=True),
        sa.Column("target_panel_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("tone", sa.String(length=80), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("proposal_payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", proposal_status, server_default="PROPOSED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_regeneration_proposals_comic_id", "comic_regeneration_proposals", ["comic_id"])
    op.create_index("ix_comic_regeneration_proposals_requested_by_user_id", "comic_regeneration_proposals", ["requested_by_user_id"])

    op.create_table(
        "comic_edit_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comic_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(length=120), nullable=False),
        sa.Column("target_page_id", sa.Uuid(), nullable=True),
        sa.Column("target_panel_id", sa.Uuid(), nullable=True),
        sa.Column("target_balloon_id", sa.Uuid(), nullable=True),
        sa.Column("before_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("after_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", operation_status, server_default="APPLIED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comic_edit_operations_comic_id", "comic_edit_operations", ["comic_id"])
    op.create_index("ix_comic_edit_operations_actor_user_id", "comic_edit_operations", ["actor_user_id"])


def downgrade() -> None:
    op.drop_table("comic_edit_operations")
    op.drop_table("comic_regeneration_proposals")
    op.drop_table("comic_review_approvals")
    op.drop_table("comic_review_comments")
    op.drop_column("comic_balloons", "layer_config")
    op.drop_column("comic_balloons", "is_locked")
    for column in (
        "text_word_limit", "audio_description", "alt_text", "image_asset_path", "pacing",
        "frozen_assets", "visual_prompt", "locked_elements",
    ):
        op.drop_column("comic_panels", column)
    op.drop_column("generated_comics", "last_saved_at")
    op.drop_column("generated_comics", "autosave_revision")
    op.drop_column("generated_comics", "review_state")
    bind = op.get_bind()
    for enum_type in (operation_status, proposal_status, comment_status, review_decision, review_specialty):
        enum_type.drop(bind, checkfirst=True)
