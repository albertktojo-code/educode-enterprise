"""Laboratório Estatístico Avançado e revisão colaborativa.

Revision ID: 0019_statistical_lab_advanced
Revises: 0018_statistical_research_lab
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0019_statistical_lab_advanced"
down_revision = "0018_statistical_research_lab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "statistical_analyses",
        sa.Column("parent_analysis_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "statistical_analyses",
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "statistical_analyses",
        sa.Column("configuration_checksum", sa.String(64), server_default="", nullable=False),
    )
    op.add_column(
        "statistical_analyses",
        sa.Column("result_signature", sa.String(64), server_default="", nullable=False),
    )
    op.add_column(
        "statistical_analyses",
        sa.Column("review_status", sa.String(40), server_default="draft", nullable=False),
    )
    op.create_foreign_key(
        "fk_statistical_analyses_parent_analysis",
        "statistical_analyses",
        "statistical_analyses",
        ["parent_analysis_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_statistical_analyses_parent_analysis_id",
        "statistical_analyses",
        ["parent_analysis_id"],
    )

    op.create_table(
        "statistical_sensitivity_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("base_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("scenario_key", sa.String(80), nullable=False),
        sa.Column("scenario_parameters", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("analysis_type", sa.String(80), nullable=False),
        sa.Column("result", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("conclusion_changed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["base_analysis_id"], ["statistical_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["statistical_datasets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_statistical_sensitivity_runs_base_analysis_id", "statistical_sensitivity_runs", ["base_analysis_id"])
    op.create_index("ix_statistical_sensitivity_runs_dataset_id", "statistical_sensitivity_runs", ["dataset_id"])
    op.create_index("ix_statistical_sensitivity_runs_organization_id", "statistical_sensitivity_runs", ["organization_id"])
    op.create_index("ix_statistical_sensitivity_runs_scenario_key", "statistical_sensitivity_runs", ["scenario_key"])

    op.create_table(
        "statistical_method_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("base_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("dataset_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("methods", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("results", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("recommendation", sa.Text(), server_default="", nullable=False),
        sa.Column("conclusions_consistent", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["base_analysis_id"], ["statistical_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id"], ["statistical_datasets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_statistical_method_comparisons_base_analysis_id", "statistical_method_comparisons", ["base_analysis_id"])
    op.create_index("ix_statistical_method_comparisons_dataset_id", "statistical_method_comparisons", ["dataset_id"])
    op.create_index("ix_statistical_method_comparisons_organization_id", "statistical_method_comparisons", ["organization_id"])

    op.create_table(
        "statistical_review_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("section_key", sa.String(120), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_statistical_review_comments_organization_id", "statistical_review_comments", ["organization_id"])
    op.create_index("ix_statistical_review_comments_entity_type", "statistical_review_comments", ["entity_type"])
    op.create_index("ix_statistical_review_comments_entity_id", "statistical_review_comments", ["entity_id"])
    op.create_index("ix_statistical_review_comments_created_by_user_id", "statistical_review_comments", ["created_by_user_id"])

    op.create_table(
        "statistical_report_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("change_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "version_number", name="uq_statistical_report_revision_version"),
        sa.ForeignKeyConstraint(["report_id"], ["statistical_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_statistical_report_revisions_report_id", "statistical_report_revisions", ["report_id"])
    op.create_index("ix_statistical_report_revisions_organization_id", "statistical_report_revisions", ["organization_id"])
    op.create_index("ix_statistical_report_revisions_created_by_user_id", "statistical_report_revisions", ["created_by_user_id"])

    op.create_table(
        "statistical_sample_size_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("study_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("design", sa.String(60), nullable=False),
        sa.Column("significance_level", sa.Float(), server_default="0.05", nullable=False),
        sa.Column("power", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("expected_effect_size", sa.Float(), nullable=False),
        sa.Column("group_ratio", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("parameters", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("result", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["study_id"], ["statistical_studies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_statistical_sample_size_plans_organization_id", "statistical_sample_size_plans", ["organization_id"])
    op.create_index("ix_statistical_sample_size_plans_study_id", "statistical_sample_size_plans", ["study_id"])


def downgrade() -> None:
    op.drop_table("statistical_sample_size_plans")
    op.drop_table("statistical_report_revisions")
    op.drop_table("statistical_review_comments")
    op.drop_table("statistical_method_comparisons")
    op.drop_table("statistical_sensitivity_runs")
    op.drop_index("ix_statistical_analyses_parent_analysis_id", table_name="statistical_analyses")
    op.drop_constraint("fk_statistical_analyses_parent_analysis", "statistical_analyses", type_="foreignkey")
    op.drop_column("statistical_analyses", "review_status")
    op.drop_column("statistical_analyses", "result_signature")
    op.drop_column("statistical_analyses", "configuration_checksum")
    op.drop_column("statistical_analyses", "version_number")
    op.drop_column("statistical_analyses", "parent_analysis_id")
