"""Teacher studio, art direction and pedagogical packages.

Revision ID: 0013_teacher_studio_canvas
Revises: 0012_comic_stabilization
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013_teacher_studio_canvas"
down_revision: str | None = "0012_comic_stabilization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


creation_mode = postgresql.ENUM(
    "QUICK", "ADVANCED", name="studio_creation_mode", create_type=False
)
material_type = postgresql.ENUM(
    "COMIC", "QUIZ", "EXERCISE", "ACTIVITY", "GAME", "LESSON_PLAN",
    "TEACHING_SEQUENCE", "ANSWER_KEY", "TEACHER_GUIDE",
    name="studio_material_type", create_type=False,
)
draft_status = postgresql.ENUM(
    "DRAFT", "CONFIGURED", "GENERATING", "READY", "ARCHIVED",
    name="studio_draft_status", create_type=False,
)
package_status = postgresql.ENUM(
    "DRAFT", "PREPARING", "READY", "NEEDS_REVIEW", "ARCHIVED",
    name="pedagogical_package_status", create_type=False,
)
material_status = postgresql.ENUM(
    "DRAFT", "READY", "NEEDS_REVIEW",
    name="package_material_status", create_type=False,
)
readiness = postgresql.ENUM(
    "NOT_READY", "READY_WITH_WARNINGS", "READY",
    name="publication_readiness", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        creation_mode, material_type, draft_status, package_status,
        material_status, readiness,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "teacher_studio_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=True),
        sa.Column("rag_context_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("creation_mode", creation_mode, nullable=False),
        sa.Column("primary_material", material_type, nullable=False),
        sa.Column("subject_name", sa.String(length=160), nullable=False),
        sa.Column("school_year", sa.String(length=80), nullable=False),
        sa.Column("topic", sa.String(length=240), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False),
        sa.Column("wizard_data", sa.JSON(), nullable=False),
        sa.Column("selected_outputs", sa.JSON(), nullable=False),
        sa.Column("page_plan", sa.JSON(), nullable=False),
        sa.Column("art_direction", sa.JSON(), nullable=False),
        sa.Column("accessibility_options", sa.JSON(), nullable=False),
        sa.Column("status", draft_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["generation_project_id"], ["generation_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in (
        "organization_id",
        "created_by_user_id",
        "generation_project_id",
        "rag_context_id",
    ):
        op.create_index(f"ix_teacher_studio_drafts_{col}", "teacher_studio_drafts", [col])

    op.create_table(
        "art_direction_presets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("preview_config", sa.JSON(), nullable=False),
        sa.Column("visual_rules", sa.JSON(), nullable=False),
        sa.Column("age_groups", sa.JSON(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_art_direction_presets_code", "art_direction_presets", ["code"], unique=True)
    op.create_index("ix_art_direction_presets_organization_id", "art_direction_presets", ["organization_id"])

    op.create_table(
        "pedagogical_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=True),
        sa.Column("comic_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("shared_context", sa.JSON(), nullable=False),
        sa.Column("art_direction_snapshot", sa.JSON(), nullable=False),
        sa.Column("status", package_status, nullable=False),
        sa.Column("preparation_report", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["comic_id"], ["generated_comics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["draft_id"], ["teacher_studio_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generation_project_id"], ["generation_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("organization_id", "draft_id", "generation_project_id", "comic_id", "created_by_user_id"):
        op.create_index(f"ix_pedagogical_packages_{col}", "pedagogical_packages", [col])

    op.create_table(
        "package_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("material_type", material_type, nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("status", material_status, nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["package_id"], ["pedagogical_packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_package_materials_package_id", "package_materials", ["package_id"])

    op.create_table(
        "publication_preparations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("readiness", readiness, nullable=False),
        sa.Column("checklist", sa.JSON(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("prepared_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["pedagogical_packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ("organization_id", "package_id", "requested_by_user_id"):
        op.create_index(f"ix_publication_preparations_{col}", "publication_preparations", [col])

    op.add_column("generated_comics", sa.Column("art_direction", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("generated_comics", sa.Column("canvas_config", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("generated_comics", sa.Column("publication_status", sa.String(length=40), server_default="draft", nullable=False))
    op.add_column("comic_pages", sa.Column("page_role", sa.String(length=40), server_default="story", nullable=False))
    op.add_column("comic_pages", sa.Column("background_config", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("comic_pages", sa.Column("guides_config", sa.JSON(), server_default="{}", nullable=False))

def downgrade() -> None:
    for column in ("guides_config", "background_config", "page_role"):
        op.drop_column("comic_pages", column)
    for column in ("publication_status", "canvas_config", "art_direction"):
        op.drop_column("generated_comics", column)
    op.drop_table("publication_preparations")
    op.drop_table("package_materials")
    op.drop_table("pedagogical_packages")
    op.drop_table("art_direction_presets")
    op.drop_table("teacher_studio_drafts")

    bind = op.get_bind()
    for enum_type in (
        readiness, material_status, package_status, draft_status,
        material_type, creation_mode,
    ):
        enum_type.drop(bind, checkfirst=True)
