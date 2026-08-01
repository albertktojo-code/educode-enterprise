"""EduCode AI Fabric: orquestração transversal de IA.

Revision ID: 0021_ai_orchestration_runtime
Revises: 0020_integrated_assessment_core
Create Date: 2026-07-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0021_ai_orchestration_runtime"
down_revision = "0020_integrated_assessment_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_EMPTY = sa.text("'{}'::json")
JSON_LIST = sa.text("'[]'::json")
NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "ai_providers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("provider_type", sa.String(40), server_default="mock", nullable=False),
        sa.Column("status", sa.String(30), server_default="active", nullable=False),
        sa.Column("public_configuration", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("secret_env_var", sa.String(160)),
        sa.Column("base_url", sa.String(500)),
        sa.Column("timeout_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", name="uq_ai_provider_org_name"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_ai_providers_organization_id", "ai_providers", ["organization_id"])

    op.create_table(
        "ai_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("model_identifier", sa.String(200), nullable=False),
        sa.Column("capabilities", sa.JSON(), server_default=JSON_LIST, nullable=False),
        sa.Column("configuration", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("input_unit_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("output_unit_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("image_unit_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "model_identifier", name="uq_ai_model_provider_identifier"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_providers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_models_organization_id", "ai_models", ["organization_id"])
    op.create_index("ix_ai_models_provider_id", "ai_models", ["provider_id"])

    op.create_table(
        "ai_prompt_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(100), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("system_instructions", sa.Text(), server_default="", nullable=False),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("required_variables", sa.JSON(), server_default=JSON_LIST, nullable=False),
        sa.Column("output_schema", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("recommended_model_id", sa.Uuid()),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "purpose", "version", name="uq_ai_prompt_org_purpose_version"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommended_model_id"], ["ai_models.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ai_prompt_templates_organization_id", "ai_prompt_templates", ["organization_id"])
    op.create_index("ix_ai_prompt_templates_purpose", "ai_prompt_templates", ["purpose"])

    op.create_table(
        "ai_module_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("module_name", sa.String(80), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("allowed_actions", sa.JSON(), server_default=JSON_LIST, nullable=False),
        sa.Column("allowed_model_ids", sa.JSON(), server_default=JSON_LIST, nullable=False),
        sa.Column("human_approval_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("daily_request_limit", sa.Integer(), server_default="100", nullable=False),
        sa.Column("monthly_cost_limit", sa.Float(), server_default="100", nullable=False),
        sa.Column("allow_student_data", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("allow_real_person_images", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("fallback_mode", sa.String(30), server_default="mock", nullable=False),
        sa.Column("policy_configuration", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "module_name", name="uq_ai_policy_org_module"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_ai_module_policies_organization_id", "ai_module_policies", ["organization_id"])

    op.create_table(
        "ai_generation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flow_id", sa.String(64), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("module_name", sa.String(80), nullable=False),
        sa.Column("action_name", sa.String(100), nullable=False),
        sa.Column("request_type", sa.String(60), server_default="structured_text", nullable=False),
        sa.Column("target_type", sa.String(80)),
        sa.Column("target_id", sa.Uuid()),
        sa.Column("provider_id", sa.Uuid()),
        sa.Column("model_id", sa.Uuid()),
        sa.Column("prompt_template_id", sa.Uuid()),
        sa.Column("rag_context_id", sa.Uuid()),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("input_snapshot", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("parameters", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("source_snapshot", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("validation_summary", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("safety_summary", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("estimated_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), server_default="", nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["ai_providers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_id"], ["ai_models.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prompt_template_id"], ["ai_prompt_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rag_context_id"], ["rag_contexts.id"], ondelete="SET NULL"),
    )
    for col in ("flow_id", "organization_id", "requested_by_user_id", "module_name", "status"):
        op.create_index(f"ix_ai_generation_requests_{col}", "ai_generation_requests", [col])

    op.create_table(
        "ai_generation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("result_type", sa.String(60), nullable=False),
        sa.Column("structured_content", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("text_content", sa.Text(), server_default="", nullable=False),
        sa.Column("storage_reference", sa.String(500)),
        sa.Column("validation_results", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("safety_results", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("review_status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("applied_to_module", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("application_snapshot", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["request_id"], ["ai_generation_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_generation_results_request_id", "ai_generation_results", ["request_id"])
    op.create_index("ix_ai_generation_results_organization_id", "ai_generation_results", ["organization_id"])

    op.create_table(
        "ai_usage_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("provider_name", sa.String(160), nullable=False),
        sa.Column("model_identifier", sa.String(200), nullable=False),
        sa.Column("input_units", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_units", sa.Integer(), server_default="0", nullable=False),
        sa.Column("image_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("estimated_cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("processing_time_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["ai_generation_requests.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_usage_records_organization_id", "ai_usage_records", ["organization_id"])
    op.create_index("ix_ai_usage_records_request_id", "ai_usage_records", ["request_id"])

    op.create_table(
        "ai_generation_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("correctness_rating", sa.Integer()),
        sa.Column("pedagogical_rating", sa.Integer()),
        sa.Column("creativity_rating", sa.Integer()),
        sa.Column("safety_rating", sa.Integer()),
        sa.Column("comments", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_id", "reviewed_by_user_id", name="uq_ai_review_result_user"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_id"], ["ai_generation_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_ai_generation_reviews_organization_id", "ai_generation_reviews", ["organization_id"])
    op.create_index("ix_ai_generation_reviews_result_id", "ai_generation_reviews", ["result_id"])

    op.create_table(
        "ai_module_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("result_id", sa.Uuid()),
        sa.Column("module_name", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(60), server_default="generated_output", nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("link_metadata", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["ai_generation_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_id"], ["ai_generation_results.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for col in ("organization_id", "request_id", "result_id", "module_name", "target_type", "target_id"):
        op.create_index(f"ix_ai_module_links_{col}", "ai_module_links", [col])

    op.create_table(
        "ai_activity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("flow_id", sa.String(64), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid()),
        sa.Column("module_name", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_data", sa.JSON(), server_default=JSON_EMPTY, nullable=False),
        sa.Column("created_by_user_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["ai_generation_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    for col in ("flow_id", "organization_id", "request_id", "module_name"):
        op.create_index(f"ix_ai_activity_events_{col}", "ai_activity_events", [col])


def downgrade() -> None:
    for table in (
        "ai_activity_events",
        "ai_module_links",
        "ai_generation_reviews",
        "ai_usage_records",
        "ai_generation_results",
        "ai_generation_requests",
        "ai_module_policies",
        "ai_prompt_templates",
        "ai_models",
        "ai_providers",
    ):
        op.drop_table(table)
