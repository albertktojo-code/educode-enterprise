from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0044_intervention_effectiveness"
down_revision: str | None = "0043_intervention_orchestration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intervention_evaluation_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "intervention_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_interventions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "outcome_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("intervention_outcomes.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "classroom_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("classrooms.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "comic_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "assignment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material_assignments.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "accessible_resource_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accessible_resource_versions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "adaptive_path_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adaptive_learning_paths.id", ondelete="SET NULL"),
        ),
        sa.Column("window_code", sa.String(24), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column(
            "scheduled_for",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "metric_name",
            sa.String(80),
            nullable=False,
            server_default="insufficient_evidence",
        ),
        sa.Column("baseline_value", sa.Float()),
        sa.Column("observed_value", sa.Float()),
        sa.Column("delta_value", sa.Float()),
        sa.Column("target_value", sa.Float()),
        sa.Column(
            "target_met",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "improved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "retained",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "alert_recurred",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "comparable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "evidence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "evidence_snapshot",
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
        sa.Column("evaluated_at", sa.DateTime(timezone=True)),
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
            "intervention_id",
            "window_code",
            name="uq_intervention_evaluation_window",
        ),
    )
    checkpoint_indexes = {
        "organization_id": "ix_int_eval_org",
        "intervention_id": "ix_int_eval_intervention",
        "outcome_id": "ix_int_eval_outcome",
        "student_id": "ix_int_eval_student",
        "classroom_id": "ix_int_eval_classroom",
        "comic_release_id": "ix_int_eval_release",
        "assignment_id": "ix_int_eval_assignment",
        "accessible_resource_version_id": "ix_int_eval_accessible",
        "adaptive_path_id": "ix_int_eval_path",
        "window_code": "ix_int_eval_window",
        "status": "ix_int_eval_status",
    }
    for column, index_name in checkpoint_indexes.items():
        op.create_index(
            index_name,
            "intervention_evaluation_checkpoints",
            [column],
        )
    op.create_index(
        "ix_intervention_evaluation_due",
        "intervention_evaluation_checkpoints",
        ["organization_id", "status", "scheduled_for"],
    )
    op.create_index(
        "ix_intervention_evaluation_student",
        "intervention_evaluation_checkpoints",
        ["organization_id", "student_id", "evaluated_at"],
    )

    op.create_table(
        "intervention_effectiveness_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_key", sa.String(100), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True)),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("window_code", sa.String(24), nullable=False),
        sa.Column("dimension_type", sa.String(40), nullable=False),
        sa.Column("dimension_key", sa.String(180), nullable=False),
        sa.Column("intervention_type", sa.String(80)),
        sa.Column(
            "comic_release_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comic_editorial_releases.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "assignment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("material_assignments.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "accessible_resource_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accessible_resource_versions.id", ondelete="SET NULL"),
        ),
        sa.Column("adaptive_path_used", sa.Boolean()),
        sa.Column(
            "sample_size",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "completed_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "improved_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "target_met_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "retained_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "recurrence_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "insufficient_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("completion_rate", sa.Float()),
        sa.Column("improved_rate", sa.Float()),
        sa.Column("target_met_rate", sa.Float()),
        sa.Column("retention_rate", sa.Float()),
        sa.Column("recurrence_rate", sa.Float()),
        sa.Column("average_gain", sa.Float()),
        sa.Column("median_days_to_improvement", sa.Float()),
        sa.Column(
            "privacy_suppressed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "calculated_at",
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
            "scope_key",
            "period_start",
            "period_end",
            "window_code",
            "dimension_key",
            name="uq_intervention_effectiveness_metric",
        ),
    )
    metric_indexes = {
        "organization_id": "ix_int_effect_org",
        "comic_release_id": "ix_int_effect_release",
        "assignment_id": "ix_int_effect_assignment",
        "accessible_resource_version_id": "ix_int_effect_accessible",
    }
    for column, index_name in metric_indexes.items():
        op.create_index(
            index_name,
            "intervention_effectiveness_metrics",
            [column],
        )
    op.create_index(
        "ix_intervention_effectiveness_period",
        "intervention_effectiveness_metrics",
        ["organization_id", "period_start", "period_end"],
    )
    op.create_index(
        "ix_intervention_effectiveness_dimension",
        "intervention_effectiveness_metrics",
        ["organization_id", "dimension_type", "dimension_key"],
    )


def downgrade() -> None:
    op.drop_table("intervention_effectiveness_metrics")
    op.drop_table("intervention_evaluation_checkpoints")
