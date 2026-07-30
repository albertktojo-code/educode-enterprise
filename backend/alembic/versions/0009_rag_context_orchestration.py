"""RAG context orchestration, citations and pedagogical-narrative contracts.

Revision ID: 0009_rag_context_orchestration
Revises: 0008_vector_retrieval
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_rag_context_orchestration"
down_revision: str | None = "0008_vector_retrieval"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

context_status = postgresql.ENUM(
    "DRAFT", "IN_REVIEW", "READY_WITH_WARNINGS", "INSUFFICIENT", "CONFLICTED",
    "APPROVED", "ARCHIVED", name="rag_context_status", create_type=False
)
fact_type = postgresql.ENUM(
    "DEFINITION", "PROCEDURE", "EXAMPLE", "MISCONCEPTION", "CONSTRAINT", "OTHER",
    name="rag_fact_type", create_type=False
)
review_status = postgresql.ENUM(
    "PENDING", "APPROVED", "REJECTED", name="rag_review_status", create_type=False
)
rule_category = postgresql.ENUM(
    "PEDAGOGICAL", "NARRATIVE", "CONTINUITY", "CREATIVE", "VISUAL", "SAFETY",
    "ACCESSIBILITY", name="rag_rule_category", create_type=False
)
rule_priority = postgresql.ENUM(
    "REQUIRED", "HIGH", "NORMAL", name="rag_rule_priority", create_type=False
)
conflict_status = postgresql.ENUM(
    "OPEN", "RESOLVED", "DISMISSED", name="rag_conflict_status", create_type=False
)
source_safety = postgresql.ENUM(
    "SAFE", "SUSPICIOUS", "BLOCKED", "MANUALLY_APPROVED",
    name="rag_source_safety", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        context_status, fact_type, review_status, rule_category, rule_priority,
        conflict_status, source_safety,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "rag_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("generation_project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("search_mode", sa.String(length=30), server_default="hybrid", nullable=False),
        sa.Column("status", context_status, server_default="DRAFT", nullable=False),
        sa.Column("context_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("retrieval_configuration", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("structured_context", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("assembled_context_text", sa.Text(), server_default="", nullable=False),
        sa.Column("quality_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("token_estimate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("readiness_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generation_project_id"], ["generation_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("organization_id", "generation_project_id", "created_by_user_id", "approved_by_user_id"):
        op.create_index(f"ix_rag_contexts_{column}", "rag_contexts", [column])

    op.create_table(
        "rag_context_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rag_context_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("citation_code", sa.String(length=30), nullable=False),
        sa.Column("citation_label", sa.String(length=220), nullable=False),
        sa.Column("ranking_position", sa.Integer(), nullable=False),
        sa.Column("source_order", sa.Integer(), nullable=False),
        sa.Column("inclusion_reason", sa.Text(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_included", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("safety_status", source_safety, server_default="SAFE", nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rag_context_id", "chunk_id", name="uq_rag_context_chunk"),
        sa.UniqueConstraint("rag_context_id", "citation_code", name="uq_rag_context_citation"),
    )
    op.create_index("ix_rag_context_sources_rag_context_id", "rag_context_sources", ["rag_context_id"])
    op.create_index("ix_rag_context_sources_chunk_id", "rag_context_sources", ["chunk_id"])

    op.create_table(
        "rag_context_facts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rag_context_id", sa.Uuid(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("fact_type", fact_type, server_default="OTHER", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.75", nullable=False),
        sa.Column("citation_codes", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("review_status", review_status, server_default="PENDING", nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_context_facts_rag_context_id", "rag_context_facts", ["rag_context_id"])

    op.create_table(
        "rag_context_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rag_context_id", sa.Uuid(), nullable=False),
        sa.Column("category", rule_category, nullable=False),
        sa.Column("rule_text", sa.Text(), nullable=False),
        sa.Column("priority", rule_priority, server_default="NORMAL", nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_context_rules_rag_context_id", "rag_context_rules", ["rag_context_id"])

    op.create_table(
        "rag_context_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rag_context_id", sa.Uuid(), nullable=False),
        sa.Column("statement_a", sa.Text(), nullable=False),
        sa.Column("statement_b", sa.Text(), nullable=False),
        sa.Column("citation_codes_a", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("citation_codes_b", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", conflict_status, server_default="OPEN", nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_context_conflicts_rag_context_id", "rag_context_conflicts", ["rag_context_id"])

    op.create_table(
        "rag_context_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rag_context_id", sa.Uuid(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False),
        sa.Column("diversity_score", sa.Float(), nullable=False),
        sa.Column("traceability_score", sa.Float(), nullable=False),
        sa.Column("consistency_score", sa.Float(), nullable=False),
        sa.Column("safety_score", sa.Float(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rag_context_evaluations_rag_context_id", "rag_context_evaluations", ["rag_context_id"])


def downgrade() -> None:
    for table in (
        "rag_context_evaluations", "rag_context_conflicts", "rag_context_rules",
        "rag_context_facts", "rag_context_sources", "rag_contexts",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum_type in (
        source_safety, conflict_status, rule_priority, rule_category,
        review_status, fact_type, context_status,
    ):
        enum_type.drop(bind, checkfirst=True)
