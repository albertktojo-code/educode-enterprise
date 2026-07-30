from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0043_intervention_orchestration"
down_revision: str | None = "0042_auth_session_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "adaptive_recommendations",
        sa.Column("source_alert_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "adaptive_recommendations",
        sa.Column("source_comic_release_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "adaptive_recommendations",
        sa.Column("source_ai_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "adaptive_recommendations",
        sa.Column(
            "source_kind",
            sa.String(40),
            nullable=False,
            server_default="generic_alert",
        ),
    )
    op.create_foreign_key(
        "fk_adaptive_recommendations_source_alert",
        "adaptive_recommendations",
        "learning_alerts",
        ["source_alert_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_adaptive_recommendations_source_release",
        "adaptive_recommendations",
        "comic_editorial_releases",
        ["source_comic_release_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_adaptive_recommendations_source_ai",
        "adaptive_recommendations",
        "ai_generation_requests",
        ["source_ai_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_adaptive_recommendations_source_alert_id",
        "adaptive_recommendations",
        ["source_alert_id"],
    )
    op.create_index(
        "ix_adaptive_recommendations_source_comic_release_id",
        "adaptive_recommendations",
        ["source_comic_release_id"],
    )
    op.create_index(
        "ix_adaptive_recommendations_source_ai_request_id",
        "adaptive_recommendations",
        ["source_ai_request_id"],
    )
    op.create_index(
        "ix_adaptive_recommendations_source_kind",
        "adaptive_recommendations",
        ["source_kind"],
    )

    intervention_columns = (
        ("source_recommendation_id", "adaptive_recommendations", "id"),
        ("comic_release_id", "comic_editorial_releases", "id"),
        ("adaptive_path_id", "adaptive_learning_paths", "id"),
        ("accessible_resource_version_id", "accessible_resource_versions", "id"),
        ("ai_request_id", "ai_generation_requests", "id"),
        ("approved_by_user_id", "users", "id"),
    )
    for column_name, target_table, target_column in intervention_columns:
        op.add_column(
            "learning_interventions",
            sa.Column(column_name, postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            f"fk_learning_interventions_{column_name}",
            "learning_interventions",
            target_table,
            [column_name],
            [target_column],
            ondelete="SET NULL",
        )
        op.create_index(
            f"ix_learning_interventions_{column_name}",
            "learning_interventions",
            [column_name],
        )

    op.add_column(
        "learning_interventions",
        sa.Column(
            "plan_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "learning_interventions",
        sa.Column(
            "baseline_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "learning_interventions",
        sa.Column(
            "target_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "learning_interventions",
        sa.Column(
            "human_review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    for column_name in (
        "approved_at",
        "started_at",
        "due_at",
        "evaluation_due_at",
    ):
        op.add_column(
            "learning_interventions",
            sa.Column(column_name, sa.DateTime(timezone=True), nullable=True),
        )

    op.create_table(
        "learning_intervention_events",
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
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=False, server_default=""),
        sa.Column("to_status", sa.String(30), nullable=False, server_default=""),
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
    op.create_index(
        "ix_learning_intervention_events_timeline",
        "learning_intervention_events",
        ["organization_id", "intervention_id", "created_at"],
    )
    op.create_index(
        "ix_learning_intervention_events_intervention_id",
        "learning_intervention_events",
        ["intervention_id"],
    )
    op.create_index(
        "ix_learning_intervention_events_actor_user_id",
        "learning_intervention_events",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_learning_intervention_events_event_type",
        "learning_intervention_events",
        ["event_type"],
    )

    op.add_column(
        "intervention_outcomes",
        sa.Column(
            "learning_intervention_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "intervention_outcomes",
        sa.Column(
            "comic_release_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_intervention_outcomes_learning_intervention",
        "intervention_outcomes",
        "learning_interventions",
        ["learning_intervention_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_intervention_outcomes_comic_release",
        "intervention_outcomes",
        "comic_editorial_releases",
        ["comic_release_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_intervention_outcomes_learning_intervention_id",
        "intervention_outcomes",
        ["learning_intervention_id"],
    )
    op.create_index(
        "ix_intervention_outcomes_comic_release_id",
        "intervention_outcomes",
        ["comic_release_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_intervention_outcomes_comic_release_id",
        table_name="intervention_outcomes",
    )
    op.drop_index(
        "ix_intervention_outcomes_learning_intervention_id",
        table_name="intervention_outcomes",
    )
    op.drop_constraint(
        "fk_intervention_outcomes_comic_release",
        "intervention_outcomes",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_intervention_outcomes_learning_intervention",
        "intervention_outcomes",
        type_="foreignkey",
    )
    op.drop_column("intervention_outcomes", "comic_release_id")
    op.drop_column("intervention_outcomes", "learning_intervention_id")

    op.drop_table("learning_intervention_events")

    for column_name in (
        "evaluation_due_at",
        "due_at",
        "started_at",
        "approved_at",
        "human_review_required",
        "target_snapshot",
        "baseline_snapshot",
        "plan_snapshot",
    ):
        op.drop_column("learning_interventions", column_name)

    for column_name, _, _ in reversed(
        (
            ("source_recommendation_id", "adaptive_recommendations", "id"),
            ("comic_release_id", "comic_editorial_releases", "id"),
            ("adaptive_path_id", "adaptive_learning_paths", "id"),
            ("accessible_resource_version_id", "accessible_resource_versions", "id"),
            ("ai_request_id", "ai_generation_requests", "id"),
            ("approved_by_user_id", "users", "id"),
        )
    ):
        op.drop_index(
            f"ix_learning_interventions_{column_name}",
            table_name="learning_interventions",
        )
        op.drop_constraint(
            f"fk_learning_interventions_{column_name}",
            "learning_interventions",
            type_="foreignkey",
        )
        op.drop_column("learning_interventions", column_name)

    op.drop_index(
        "ix_adaptive_recommendations_source_kind",
        table_name="adaptive_recommendations",
    )
    op.drop_index(
        "ix_adaptive_recommendations_source_ai_request_id",
        table_name="adaptive_recommendations",
    )
    op.drop_index(
        "ix_adaptive_recommendations_source_comic_release_id",
        table_name="adaptive_recommendations",
    )
    op.drop_index(
        "ix_adaptive_recommendations_source_alert_id",
        table_name="adaptive_recommendations",
    )
    op.drop_constraint(
        "fk_adaptive_recommendations_source_ai",
        "adaptive_recommendations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_adaptive_recommendations_source_release",
        "adaptive_recommendations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_adaptive_recommendations_source_alert",
        "adaptive_recommendations",
        type_="foreignkey",
    )
    op.drop_column("adaptive_recommendations", "source_kind")
    op.drop_column("adaptive_recommendations", "source_ai_request_id")
    op.drop_column("adaptive_recommendations", "source_comic_release_id")
    op.drop_column("adaptive_recommendations", "source_alert_id")
