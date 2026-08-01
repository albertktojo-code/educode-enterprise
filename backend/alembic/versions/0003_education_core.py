"""Education core.

Revision ID: 0003_education_core
Revises: 0002_auth_rbac
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_education_core"
down_revision: str | None = "0002_auth_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

project_status = postgresql.ENUM(
    "DRAFT",
    "ACTIVE",
    "ARCHIVED",
    name="project_status",
    create_type=False,
)
content_type = postgresql.ENUM(
    "LESSON",
    "COMIC",
    "QUIZ",
    "ACTIVITY",
    "REFERENCE",
    name="content_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    project_status.create(bind, checkfirst=True)
    content_type.create(bind, checkfirst=True)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_subject_org_code"),
    )
    op.create_index(
        "ix_subjects_organization_id",
        "subjects",
        ["organization_id"],
        unique=False,
    )

    op.create_table(
        "classrooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("school_year", sa.Integer(), nullable=True),
        sa.Column("grade", sa.String(length=60), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_classrooms_organization_id",
        "classrooms",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_classrooms_subject_id",
        "classrooms",
        ["subject_id"],
        unique=False,
    )

    op.create_table(
        "classroom_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=30), server_default="student", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["classroom_id"],
            ["classrooms.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classroom_id", "user_id", name="uq_classroom_user"),
    )
    op.create_index(
        "ix_classroom_enrollments_classroom_id",
        "classroom_enrollments",
        ["classroom_id"],
        unique=False,
    )
    op.create_index(
        "ix_classroom_enrollments_user_id",
        "classroom_enrollments",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("classroom_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", project_status, server_default="DRAFT", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["classroom_id"],
            ["classrooms.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_projects_organization_id",
        "projects",
        ["organization_id"],
        unique=False,
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"], unique=False)
    op.create_index(
        "ix_projects_classroom_id",
        "projects",
        ["classroom_id"],
        unique=False,
    )
    op.create_index("ix_projects_subject_id", "projects", ["subject_id"], unique=False)

    op.create_table(
        "content_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("content_type", content_type, nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_items_project_id",
        "content_items",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_content_items_project_id", table_name="content_items")
    op.drop_table("content_items")
    op.drop_index("ix_projects_subject_id", table_name="projects")
    op.drop_index("ix_projects_classroom_id", table_name="projects")
    op.drop_index("ix_projects_owner_id", table_name="projects")
    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_classroom_enrollments_user_id", table_name="classroom_enrollments")
    op.drop_index(
        "ix_classroom_enrollments_classroom_id",
        table_name="classroom_enrollments",
    )
    op.drop_table("classroom_enrollments")
    op.drop_index("ix_classrooms_subject_id", table_name="classrooms")
    op.drop_index("ix_classrooms_organization_id", table_name="classrooms")
    op.drop_table("classrooms")
    op.drop_index("ix_subjects_organization_id", table_name="subjects")
    op.drop_table("subjects")
    content_type.drop(op.get_bind(), checkfirst=True)
    project_status.drop(op.get_bind(), checkfirst=True)
