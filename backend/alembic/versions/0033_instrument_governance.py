"""Sprint 15.3 - instrument governance

Revision ID: 0033_instrument_governance
Revises: 0032_assessment_delivery
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0033_instrument_governance"
down_revision: str | None = "0032_assessment_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "assessment_instrument_licenses",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("instrument_id", UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("license_holder", sa.String(240), nullable=False),
        sa.Column("rights_owner", sa.String(240)),
        sa.Column("permission_reference", sa.Text(), nullable=False),
        sa.Column("rights_scope", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("permitted_populations", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("permitted_territories", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("item_exposure_policy", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("storage_policy", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_until", sa.Date()),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("approved_by_user_id", UUID),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "instrument_id", "version", name="uq_instrument_license_version"),
    )
    op.create_index("ix_instrument_licenses_status", "assessment_instrument_licenses", ["organization_id", "status", "valid_until"])

    op.create_table(
        "assessment_instrument_protocols",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("instrument_id", UUID, nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("instructions", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("duration_minutes", sa.Integer()),
        sa.Column("target_population", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("administration_conditions", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("accessibility_rules", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scoring_reference", sa.Text()),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("published_by_user_id", UUID),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "instrument_id", "code", "version", name="uq_instrument_protocol_version"),
    )
    op.create_index("ix_instrument_protocols_status", "assessment_instrument_protocols", ["organization_id", "status", "instrument_id"])

    op.create_table(
        "assessment_instrument_norm_groups",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("instrument_id", UUID, nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("locale", sa.String(20), nullable=False, server_default="pt-BR"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("age_min", sa.Float()),
        sa.Column("age_max", sa.Float()),
        sa.Column("school_year_min", sa.Integer()),
        sa.Column("school_year_max", sa.Integer()),
        sa.Column("population_filters", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sample_size", sa.Integer()),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("methodology", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("published_by_user_id", UUID),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "instrument_id", "code", "version", name="uq_instrument_norm_group"),
    )
    op.create_index("ix_instrument_norm_groups_lookup", "assessment_instrument_norm_groups", ["organization_id", "instrument_id", "locale", "status"])

    op.create_table(
        "assessment_instrument_norm_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("norm_group_id", UUID, nullable=False),
        sa.Column("dimension_code", sa.String(80), nullable=False, server_default="TOTAL"),
        sa.Column("raw_min", sa.Float(), nullable=False),
        sa.Column("raw_max", sa.Float(), nullable=False),
        sa.Column("standardized_score", sa.Float()),
        sa.Column("percentile", sa.Float()),
        sa.Column("classification", sa.String(120), nullable=False),
        sa.Column("interpretation", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "norm_group_id", "dimension_code", "raw_min", "raw_max", name="uq_instrument_norm_entry_range"),
    )
    op.create_index("ix_instrument_norm_entries_lookup", "assessment_instrument_norm_entries", ["organization_id", "norm_group_id", "dimension_code"])

    op.create_table(
        "assessment_instrument_mappings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("instrument_id", UUID, nullable=False),
        sa.Column("dimension_id", UUID, nullable=False),
        sa.Column("framework_type", sa.String(40), nullable=False),
        sa.Column("framework_code", sa.String(100), nullable=False),
        sa.Column("relation_type", sa.String(40), nullable=False, server_default="RELATED"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "instrument_id", "dimension_id", "framework_type", "framework_code", name="uq_instrument_dimension_mapping"),
    )
    op.create_index("ix_instrument_mappings_framework", "assessment_instrument_mappings", ["organization_id", "framework_type", "framework_code"])

    op.create_table(
        "assessment_instrument_imports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("instrument_id", UUID, nullable=False),
        sa.Column("filename", sa.String(260), nullable=False),
        sa.Column("file_format", sa.String(40), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECEIVED"),
        sa.Column("declared_license_id", UUID),
        sa.Column("contains_protected_items", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("manifest", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_errors", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("imported_counts", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", UUID, nullable=False),
        sa.Column("validated_by_user_id", UUID),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "checksum_sha256", name="uq_instrument_import_checksum"),
    )
    op.create_index("ix_instrument_imports_status", "assessment_instrument_imports", ["organization_id", "status", "created_at"])

    op.create_table(
        "assessment_instrument_interpretations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("instrument_id", UUID, nullable=False),
        sa.Column("attempt_id", UUID, nullable=False),
        sa.Column("norm_group_id", UUID),
        sa.Column("scoring_version", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="CALCULATED"),
        sa.Column("raw_scores", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("standardized_scores", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("classifications", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("descriptive_interpretation", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("calculated_by_user_id", UUID, nullable=False),
        sa.Column("validated_by_user_id", UUID),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "attempt_id", "scoring_version", name="uq_instrument_interpretation"),
    )
    op.create_index("ix_instrument_interpretations_review", "assessment_instrument_interpretations", ["organization_id", "status", "requires_human_review"])


def downgrade() -> None:
    op.drop_index("ix_instrument_interpretations_review", table_name="assessment_instrument_interpretations")
    op.drop_table("assessment_instrument_interpretations")
    op.drop_index("ix_instrument_imports_status", table_name="assessment_instrument_imports")
    op.drop_table("assessment_instrument_imports")
    op.drop_index("ix_instrument_mappings_framework", table_name="assessment_instrument_mappings")
    op.drop_table("assessment_instrument_mappings")
    op.drop_index("ix_instrument_norm_entries_lookup", table_name="assessment_instrument_norm_entries")
    op.drop_table("assessment_instrument_norm_entries")
    op.drop_index("ix_instrument_norm_groups_lookup", table_name="assessment_instrument_norm_groups")
    op.drop_table("assessment_instrument_norm_groups")
    op.drop_index("ix_instrument_protocols_status", table_name="assessment_instrument_protocols")
    op.drop_table("assessment_instrument_protocols")
    op.drop_index("ix_instrument_licenses_status", table_name="assessment_instrument_licenses")
    op.drop_table("assessment_instrument_licenses")
