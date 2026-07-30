from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0051_hq_activity_delivery"
down_revision: str | None = "0050_hq_activity_feedback"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "hq_activity_delivery_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("publication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_mode", sa.String(24), nullable=False, server_default="HQ_FLOW"),
        sa.Column("reader_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("release_answer_key", sa.String(24), nullable=False, server_default="AFTER_SUBMISSION"),
        sa.Column("monitoring_settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("delivery_mode IN ('HQ_FLOW','ACTIVITY_ONLY','TEACHER_PREVIEW')", name="ck_hq_activity_delivery_mode"),
        sa.CheckConstraint("release_answer_key IN ('NEVER','AFTER_SUBMISSION','AFTER_WINDOW','IMMEDIATE')", name="ck_hq_answer_key_release"),
        sa.CheckConstraint("status IN ('DRAFT','SCHEDULED','PUBLISHED','CLOSED','ARCHIVED')", name="ck_hq_activity_delivery_status"),
        sa.UniqueConstraint("organization_id","comic_project_id","publication_id",name="uq_hq_activity_delivery_publication"),
    )
    op.create_index("ix_hq_activity_delivery_status","hq_activity_delivery_links",["organization_id","status","published_at"])

def downgrade() -> None:
    op.drop_index("ix_hq_activity_delivery_status",table_name="hq_activity_delivery_links")
    op.drop_table("hq_activity_delivery_links")
