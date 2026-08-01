from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0045_institutional_governance"
down_revision: str | None = "0044_intervention_effectiveness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institutional_governance_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(120), nullable=False),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "risk_tier",
            sa.String(20),
            nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "adaptive_model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adaptive_model_versions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "ai_model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_models.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "prompt_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_prompt_templates.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "module_policy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_module_policies.id", ondelete="SET NULL"),
        ),
        sa.Column("intervention_type", sa.String(80)),
        sa.Column("evidence_rule_code", sa.String(120)),
        sa.Column("purpose", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "intended_users",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "limitations",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "prohibited_uses",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "documentation",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "approval_policy",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "monitoring_policy",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "lineage_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "content_hash",
            sa.String(64),
            nullable=False,
            server_default="",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("suspended_at", sa.DateTime(timezone=True)),
        sa.Column("retired_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            "version",
            name="uq_governance_asset_org_code_version",
        ),
        sa.CheckConstraint(
            """
            num_nonnulls(
                adaptive_model_version_id,
                ai_model_id,
                prompt_template_id,
                module_policy_id,
                intervention_type,
                evidence_rule_code
            ) = 1
            """,
            name="ck_governance_asset_reference",
        ),
    )
    asset_indexes = {
        "organization_id": "ix_gov_asset_org",
        "code": "ix_gov_asset_code",
        "asset_type": "ix_gov_asset_type",
        "status": "ix_gov_asset_status_single",
        "risk_tier": "ix_gov_asset_risk",
        "owner_user_id": "ix_gov_asset_owner",
        "adaptive_model_version_id": "ix_gov_asset_adaptive",
        "ai_model_id": "ix_gov_asset_ai_model",
        "prompt_template_id": "ix_gov_asset_prompt",
        "module_policy_id": "ix_gov_asset_policy",
        "intervention_type": "ix_gov_asset_intervention",
        "evidence_rule_code": "ix_gov_asset_rule",
    }
    for column, index_name in asset_indexes.items():
        op.create_index(
            index_name,
            "institutional_governance_assets",
            [column],
        )
    op.create_index(
        "ix_governance_asset_status",
        "institutional_governance_assets",
        ["organization_id", "status", "risk_tier"],
    )
    op.create_index(
        "ix_governance_asset_reference",
        "institutional_governance_assets",
        ["organization_id", "asset_type", "code"],
    )

    op.create_table(
        "institutional_governance_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "institutional_governance_assets.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "reviewer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("review_stage", sa.String(40), nullable=False),
        sa.Column(
            "decision",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "scorecard",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "findings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "required_actions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("comments", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "asset_id",
            "reviewer_user_id",
            "review_stage",
            name="uq_governance_review_asset_user_stage",
        ),
    )
    for column, index_name in {
        "organization_id": "ix_gov_review_org",
        "asset_id": "ix_gov_review_asset",
        "reviewer_user_id": "ix_gov_review_user",
        "review_stage": "ix_gov_review_stage",
        "decision": "ix_gov_review_decision",
    }.items():
        op.create_index(
            index_name,
            "institutional_governance_reviews",
            [column],
        )
    op.create_index(
        "ix_governance_review_queue",
        "institutional_governance_reviews",
        ["organization_id", "decision", "review_stage"],
    )

    op.create_table(
        "institutional_governance_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "institutional_governance_assets.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "background_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("background_jobs.id", ondelete="SET NULL"),
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "sample_size",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("quality_score", sa.Float()),
        sa.Column("safety_score", sa.Float()),
        sa.Column("effectiveness_score", sa.Float()),
        sa.Column("fairness_score", sa.Float()),
        sa.Column("drift_score", sa.Float()),
        sa.Column("error_rate", sa.Float()),
        sa.Column("recurrence_rate", sa.Float()),
        sa.Column(
            "complaint_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "threshold_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "threshold_breaches",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "cohort_metrics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "privacy_suppressed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "asset_id",
            "period_start",
            "period_end",
            name="uq_governance_snapshot_asset_period",
        ),
    )
    for column, index_name in {
        "organization_id": "ix_gov_snapshot_org",
        "asset_id": "ix_gov_snapshot_asset",
        "background_job_id": "ix_gov_snapshot_job",
        "threshold_breached": "ix_gov_snapshot_breach",
    }.items():
        op.create_index(
            index_name,
            "institutional_governance_snapshots",
            [column],
        )
    op.create_index(
        "ix_governance_snapshot_period",
        "institutional_governance_snapshots",
        ["organization_id", "period_start", "period_end"],
    )
    op.create_index(
        "ix_governance_snapshot_risk",
        "institutional_governance_snapshots",
        ["organization_id", "threshold_breached", "calculated_at"],
    )

    op.create_table(
        "institutional_governance_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "institutional_governance_assets.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "institutional_governance_snapshots.id",
                ondelete="SET NULL",
            ),
        ),
        sa.Column(
            "opened_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "resolved_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default="moderate",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="open",
        ),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "remediation_plan",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "resolution_summary",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    for column, index_name in {
        "organization_id": "ix_gov_incident_org",
        "asset_id": "ix_gov_incident_asset",
        "snapshot_id": "ix_gov_incident_snapshot",
        "opened_by_user_id": "ix_gov_incident_opened_by",
        "resolved_by_user_id": "ix_gov_incident_resolved_by",
        "category": "ix_gov_incident_category",
        "severity": "ix_gov_incident_severity",
        "status": "ix_gov_incident_status",
    }.items():
        op.create_index(
            index_name,
            "institutional_governance_incidents",
            [column],
        )
    op.create_index(
        "ix_governance_incident_open",
        "institutional_governance_incidents",
        ["organization_id", "status", "severity"],
    )

    op.create_table(
        "institutional_governance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "institutional_governance_assets.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column(
            "from_status",
            sa.String(30),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "to_status",
            sa.String(30),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "event_data",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    for column, index_name in {
        "organization_id": "ix_gov_event_org",
        "asset_id": "ix_gov_event_asset",
        "actor_user_id": "ix_gov_event_actor",
        "event_type": "ix_gov_event_type",
    }.items():
        op.create_index(
            index_name,
            "institutional_governance_events",
            [column],
        )
    op.create_index(
        "ix_governance_event_timeline",
        "institutional_governance_events",
        ["organization_id", "asset_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("institutional_governance_events")
    op.drop_table("institutional_governance_incidents")
    op.drop_table("institutional_governance_snapshots")
    op.drop_table("institutional_governance_reviews")
    op.drop_table("institutional_governance_assets")
