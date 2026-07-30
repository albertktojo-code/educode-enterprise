"""Pedagogical planning, learning units and generation sources.

Revision ID: 0006_pedagogical_planning
Revises: 0005_document_structure
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_pedagogical_planning"
down_revision: str | None = "0005_document_structure"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

source_mode = postgresql.ENUM(
    "DOCUMENT",
    "AI",
    "TEACHER_TEXT",
    "HYBRID",
    name="source_mode",
    create_type=False,
)
source_type = postgresql.ENUM(
    "DOCUMENT",
    "TEACHER_TEXT",
    "AI_KNOWLEDGE",
    "MANUAL_INSTRUCTION",
    name="generation_source_type",
    create_type=False,
)
fidelity_level = postgresql.ENUM(
    "STRICT",
    "BALANCED",
    "CREATIVE",
    name="fidelity_level",
    create_type=False,
)
integration_mode = postgresql.ENUM(
    "SUBJECT_FOCUS",
    "COMPUTATIONAL_THINKING_FOCUS",
    "BALANCED",
    name="integration_mode",
    create_type=False,
)
difficulty_level = postgresql.ENUM(
    "INTRODUCTORY",
    "BASIC",
    "INTERMEDIATE",
    "ADVANCED",
    name="difficulty_level",
    create_type=False,
)
generation_difficulty_level = postgresql.ENUM(
    "INTRODUCTORY",
    "BASIC",
    "INTERMEDIATE",
    "ADVANCED",
    name="generation_difficulty_level",
    create_type=False,
)
privacy_level = postgresql.ENUM(
    "PRIVATE",
    "TEAM",
    "CLASSROOM",
    "ORGANIZATION",
    name="privacy_level",
    create_type=False,
)
generation_status = postgresql.ENUM(
    "DRAFT",
    "IN_REVIEW",
    "CONFIRMED",
    "ARCHIVED",
    name="generation_status",
    create_type=False,
)
pillar_relevance = postgresql.ENUM(
    "HIGH",
    "MEDIUM",
    "COMPLEMENTARY",
    name="pillar_relevance",
    create_type=False,
)
assessment_design = postgresql.ENUM(
    "NONE",
    "DIAGNOSTIC",
    "PRE_POST",
    "EXPERIMENTAL_CONTROL",
    "FORMATIVE",
    "SUMMATIVE",
    "TAM",
    name="assessment_design",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        source_mode,
        source_type,
        fidelity_level,
        integration_mode,
        difficulty_level,
        generation_difficulty_level,
        privacy_level,
        generation_status,
        pillar_relevance,
        assessment_design,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "learning_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_page", sa.Integer(), nullable=True),
        sa.Column("end_page", sa.Integer(), nullable=True),
        sa.Column("school_year", sa.String(length=80), nullable=True),
        sa.Column(
            "difficulty_level",
            difficulty_level,
            server_default="INTERMEDIATE",
            nullable=False,
        ),
        sa.Column("disciplinary_objective", sa.Text(), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["document_chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_units_organization_id", "learning_units", ["organization_id"])
    op.create_index("ix_learning_units_chapter_id", "learning_units", ["chapter_id"])
    op.create_index("ix_learning_units_subject_id", "learning_units", ["subject_id"])

    op.create_table(
        "computational_thinking_pillars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("pedagogical_examples", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_computational_thinking_pillars_code",
        "computational_thinking_pillars",
        ["code"],
        unique=True,
    )

    op.create_table(
        "generation_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("source_mode", source_mode, nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("custom_subject_name", sa.String(length=160), nullable=True),
        sa.Column("school_year", sa.String(length=80), nullable=True),
        sa.Column("topic", sa.String(length=240), nullable=False),
        sa.Column("disciplinary_objective", sa.Text(), nullable=True),
        sa.Column("computational_thinking_objective", sa.Text(), nullable=True),
        sa.Column("teacher_text", sa.Text(), nullable=True),
        sa.Column("teacher_instructions", sa.Text(), nullable=True),
        sa.Column("allow_ai_expansion", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "fidelity_level",
            fidelity_level,
            server_default="BALANCED",
            nullable=False,
        ),
        sa.Column(
            "integration_mode",
            integration_mode,
            server_default="BALANCED",
            nullable=False,
        ),
        sa.Column(
            "difficulty_level",
            generation_difficulty_level,
            server_default="INTERMEDIATE",
            nullable=False,
        ),
        sa.Column(
            "privacy_level",
            privacy_level,
            server_default="PRIVATE",
            nullable=False,
        ),
        sa.Column("credit_name", sa.String(length=180), nullable=False),
        sa.Column("rights_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "bncc_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "desired_materials",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "accessibility_options",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "source_priority",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "assessment_design",
            assessment_design,
            server_default="NONE",
            nullable=False,
        ),
        sa.Column("assessment_notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            generation_status,
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column(
            "mock_proposal",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_projects_organization_id", "generation_projects", ["organization_id"]
    )
    op.create_index("ix_generation_projects_project_id", "generation_projects", ["project_id"])
    op.create_index(
        "ix_generation_projects_created_by_user_id", "generation_projects", ["created_by_user_id"]
    )
    op.create_index("ix_generation_projects_subject_id", "generation_projects", ["subject_id"])

    op.create_table(
        "generation_project_pillars",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=False),
        sa.Column("pillar_id", sa.Uuid(), nullable=False),
        sa.Column(
            "relevance",
            pillar_relevance,
            server_default="HIGH",
            nullable=False,
        ),
        sa.Column("application_description", sa.Text(), nullable=True),
        sa.Column("selected_by", sa.String(length=30), server_default="teacher", nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_project_id"], ["generation_projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["pillar_id"], ["computational_thinking_pillars.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_project_id",
            "pillar_id",
            name="uq_generation_project_pillar",
        ),
    )
    op.create_index(
        "ix_generation_project_pillars_generation_project_id",
        "generation_project_pillars",
        ["generation_project_id"],
    )
    op.create_index(
        "ix_generation_project_pillars_pillar_id",
        "generation_project_pillars",
        ["pillar_id"],
    )

    op.create_table(
        "generation_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("chapter_id", sa.Uuid(), nullable=True),
        sa.Column("learning_unit_id", sa.Uuid(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("weight", sa.Float(), server_default="1", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("allow_ai_expansion", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_project_id"], ["generation_projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chapter_id"], ["document_chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["learning_unit_id"], ["learning_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_generation_sources_generation_project_id",
        "generation_sources",
        ["generation_project_id"],
    )
    op.create_index("ix_generation_sources_document_id", "generation_sources", ["document_id"])
    op.create_index("ix_generation_sources_chapter_id", "generation_sources", ["chapter_id"])
    op.create_index(
        "ix_generation_sources_learning_unit_id", "generation_sources", ["learning_unit_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_generation_sources_learning_unit_id", table_name="generation_sources")
    op.drop_index("ix_generation_sources_chapter_id", table_name="generation_sources")
    op.drop_index("ix_generation_sources_document_id", table_name="generation_sources")
    op.drop_index("ix_generation_sources_generation_project_id", table_name="generation_sources")
    op.drop_table("generation_sources")

    op.drop_index(
        "ix_generation_project_pillars_pillar_id", table_name="generation_project_pillars"
    )
    op.drop_index(
        "ix_generation_project_pillars_generation_project_id",
        table_name="generation_project_pillars",
    )
    op.drop_table("generation_project_pillars")

    op.drop_index("ix_generation_projects_subject_id", table_name="generation_projects")
    op.drop_index("ix_generation_projects_created_by_user_id", table_name="generation_projects")
    op.drop_index("ix_generation_projects_project_id", table_name="generation_projects")
    op.drop_index("ix_generation_projects_organization_id", table_name="generation_projects")
    op.drop_table("generation_projects")

    op.drop_index(
        "ix_computational_thinking_pillars_code", table_name="computational_thinking_pillars"
    )
    op.drop_table("computational_thinking_pillars")

    op.drop_index("ix_learning_units_subject_id", table_name="learning_units")
    op.drop_index("ix_learning_units_chapter_id", table_name="learning_units")
    op.drop_index("ix_learning_units_organization_id", table_name="learning_units")
    op.drop_table("learning_units")

    for enum_type in reversed(
        (
            source_mode,
            source_type,
            fidelity_level,
            integration_mode,
            difficulty_level,
            generation_difficulty_level,
            privacy_level,
            generation_status,
            pillar_relevance,
            assessment_design,
        )
    ):
        enum_type.drop(op.get_bind(), checkfirst=True)
