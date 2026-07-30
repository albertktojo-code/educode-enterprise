from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0053_hq_learning_analytics"
down_revision: str | None = "0052_hq_student_experience"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "hq_learning_analytics_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(24), nullable=False, server_default="PUBLICATION"),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("skill_metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("page_metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("activity_metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("correlations", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("alerts", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scope_type IN ('PUBLICATION','CLASS','STUDENT','ACTIVITY')",name="ck_hq_learning_analytics_scope"),
        sa.UniqueConstraint("organization_id","publication_id","scope_type","scope_id","period_start","period_end",name="uq_hq_learning_analytics_snapshot"),
    )
    op.create_index("ix_hq_learning_analytics_lookup","hq_learning_analytics_snapshots",["organization_id","publication_id","scope_type","generated_at"])

def downgrade() -> None:
    op.drop_index("ix_hq_learning_analytics_lookup",table_name="hq_learning_analytics_snapshots")
    op.drop_table("hq_learning_analytics_snapshots")
