"""Creative library, creative bible and teaching sequences.

Revision ID: 0007_creative_library
Revises: 0006_pedagogical_planning
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_creative_library"
down_revision: str | None = "0006_pedagogical_planning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

creative_item_kind = postgresql.ENUM(
    "CHARACTER", "SCENE", "STYLE", name="creative_item_kind", create_type=False
)
creative_visibility = postgresql.ENUM(
    "PRIVATE", "TEAM", "ORGANIZATION", name="creative_visibility", create_type=False
)
creative_status = postgresql.ENUM(
    "DRAFT", "ACTIVE", "ARCHIVED", name="creative_status", create_type=False
)
sequence_status = postgresql.ENUM(
    "DRAFT", "IN_REVIEW", "APPROVED", "ARCHIVED", name="sequence_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        creative_item_kind,
        creative_visibility,
        creative_status,
        sequence_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.add_column(
        "generation_projects",
        sa.Column("cognitive_levels", postgresql.JSONB(), server_default="[]", nullable=False),
    )
    op.add_column(
        "generation_projects",
        sa.Column("measurable_objectives", postgresql.JSONB(), server_default="[]", nullable=False),
    )
    op.add_column(
        "generation_projects",
        sa.Column("evaluation_plan", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.add_column(
        "generation_projects",
        sa.Column(
            "author_credit_settings", postgresql.JSONB(), server_default="{}", nullable=False
        ),
    )

    op.create_table(
        "creative_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("kind", creative_item_kind, nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("canonical_prompt", sa.Text(), nullable=True),
        sa.Column("negative_prompt", sa.Text(), nullable=True),
        sa.Column("profile_data", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("visibility", creative_visibility, server_default="PRIVATE", nullable=False),
        sa.Column("status", creative_status, server_default="DRAFT", nullable=False),
        sa.Column("rights_confirmed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("original_author", sa.String(length=180), nullable=True),
        sa.Column("license_notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "kind", "name", name="uq_creative_item_org_kind_name"
        ),
    )
    op.create_index("ix_creative_items_organization_id", "creative_items", ["organization_id"])
    op.create_index(
        "ix_creative_items_created_by_user_id", "creative_items", ["created_by_user_id"]
    )
    op.create_index("ix_creative_items_kind", "creative_items", ["kind"])

    op.create_table(
        "creative_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("creative_item_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("asset_role", sa.String(length=80), server_default="reference", nullable=False),
        sa.Column("pdf_page_number", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creative_item_id"], ["creative_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_creative_assets_creative_item_id", "creative_assets", ["creative_item_id"])
    op.create_index("ix_creative_assets_checksum_sha256", "creative_assets", ["checksum_sha256"])

    op.create_table(
        "creative_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("creative_item_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("profile_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("change_description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creative_item_id"], ["creative_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "creative_item_id", "version_number", name="uq_creative_version_number"
        ),
    )
    op.create_index(
        "ix_creative_versions_creative_item_id", "creative_versions", ["creative_item_id"]
    )
    op.create_index(
        "ix_creative_versions_created_by_user_id", "creative_versions", ["created_by_user_id"]
    )

    op.create_table(
        "generation_project_creative_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=False),
        sa.Column("creative_item_id", sa.Uuid(), nullable=False),
        sa.Column("creative_version_id", sa.Uuid(), nullable=True),
        sa.Column("narrative_role", sa.String(length=100), nullable=True),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(
            ["generation_project_id"], ["generation_projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["creative_item_id"], ["creative_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["creative_version_id"], ["creative_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "generation_project_id",
            "creative_item_id",
            name="uq_generation_project_creative_item",
        ),
    )
    op.create_index(
        "ix_generation_project_creative_items_generation_project_id",
        "generation_project_creative_items",
        ["generation_project_id"],
    )
    op.create_index(
        "ix_generation_project_creative_items_creative_item_id",
        "generation_project_creative_items",
        ["creative_item_id"],
    )

    op.create_table(
        "creative_bibles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("age_group", sa.String(length=80), nullable=True),
        sa.Column("visual_language", sa.Text(), nullable=True),
        sa.Column("narrative_tone", sa.Text(), nullable=True),
        sa.Column("pedagogical_tone", sa.Text(), nullable=True),
        sa.Column("color_palette", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("mandatory_rules", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("prohibited_elements", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("institution_identity", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
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
            ["generation_project_id"], ["generation_projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_project_id"),
    )
    op.create_index(
        "ix_creative_bibles_generation_project_id",
        "creative_bibles",
        ["generation_project_id"],
        unique=True,
    )
    op.create_index(
        "ix_creative_bibles_updated_by_user_id", "creative_bibles", ["updated_by_user_id"]
    )

    op.create_table(
        "teaching_sequences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sequence_status, server_default="DRAFT", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_name_snapshot", sa.String(length=160), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["generation_project_id"], ["generation_projects.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_teaching_sequences_organization_id", "teaching_sequences", ["organization_id"]
    )
    op.create_index(
        "ix_teaching_sequences_generation_project_id",
        "teaching_sequences",
        ["generation_project_id"],
    )
    op.create_index(
        "ix_teaching_sequences_created_by_user_id", "teaching_sequences", ["created_by_user_id"]
    )

    op.create_table(
        "teaching_sequence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("material_type", sa.String(length=80), nullable=False),
        sa.Column("learning_objective", sa.Text(), nullable=True),
        sa.Column("pillar_codes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("evaluation_role", sa.String(length=60), server_default="none", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["sequence_id"], ["teaching_sequences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_teaching_sequence_items_sequence_id", "teaching_sequence_items", ["sequence_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_teaching_sequence_items_sequence_id", table_name="teaching_sequence_items")
    op.drop_table("teaching_sequence_items")

    op.drop_index("ix_teaching_sequences_created_by_user_id", table_name="teaching_sequences")
    op.drop_index("ix_teaching_sequences_generation_project_id", table_name="teaching_sequences")
    op.drop_index("ix_teaching_sequences_organization_id", table_name="teaching_sequences")
    op.drop_table("teaching_sequences")

    op.drop_index("ix_creative_bibles_updated_by_user_id", table_name="creative_bibles")
    op.drop_index("ix_creative_bibles_generation_project_id", table_name="creative_bibles")
    op.drop_table("creative_bibles")

    op.drop_index(
        "ix_generation_project_creative_items_creative_item_id",
        table_name="generation_project_creative_items",
    )
    op.drop_index(
        "ix_generation_project_creative_items_generation_project_id",
        table_name="generation_project_creative_items",
    )
    op.drop_table("generation_project_creative_items")

    op.drop_index("ix_creative_versions_created_by_user_id", table_name="creative_versions")
    op.drop_index("ix_creative_versions_creative_item_id", table_name="creative_versions")
    op.drop_table("creative_versions")

    op.drop_index("ix_creative_assets_checksum_sha256", table_name="creative_assets")
    op.drop_index("ix_creative_assets_creative_item_id", table_name="creative_assets")
    op.drop_table("creative_assets")

    op.drop_index("ix_creative_items_kind", table_name="creative_items")
    op.drop_index("ix_creative_items_created_by_user_id", table_name="creative_items")
    op.drop_index("ix_creative_items_organization_id", table_name="creative_items")
    op.drop_table("creative_items")

    op.drop_column("generation_projects", "author_credit_settings")
    op.drop_column("generation_projects", "evaluation_plan")
    op.drop_column("generation_projects", "measurable_objectives")
    op.drop_column("generation_projects", "cognitive_levels")

    bind = op.get_bind()
    for enum_type in (
        sequence_status,
        creative_status,
        creative_visibility,
        creative_item_kind,
    ):
        enum_type.drop(bind, checkfirst=True)
