from __future__ import annotations

import json
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0046_comic_editor_story"
down_revision: str | None = "0045_institutional_governance"
branch_labels = None
depends_on = None

SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000"

LAYOUTS = [
    {
        "id": "16100000-0000-4000-8000-000000000001",
        "code": "GRID_FEATURE_THREE",
        "name": "Destaque e três cenas",
        "description": "Um quadro principal e três cenas de apoio.",
        "panel_count": 4,
        "category": "TRADITIONAL",
        "grid_definition": {
            "gutter": 0.02,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 0.66, "height": 0.50, "shape": "RECTANGLE"},
                {"x": 0.68, "y": 0.00, "width": 0.32, "height": 0.50, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.52, "width": 0.32, "height": 0.48, "shape": "RECTANGLE"},
                {"x": 0.34, "y": 0.52, "width": 0.66, "height": 0.48, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "balanced", "recommended_beats": ["opening", "development"]},
    },
    {
        "id": "16100000-0000-4000-8000-000000000002",
        "code": "GRID_EQUAL_FOUR",
        "name": "Quatro quadros iguais",
        "description": "Quatro cenas com o mesmo peso visual.",
        "panel_count": 4,
        "category": "TRADITIONAL",
        "grid_definition": {
            "gutter": 0.02,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"},
                {"x": 0.51, "y": 0.00, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.51, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"},
                {"x": 0.51, "y": 0.51, "width": 0.49, "height": 0.49, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "steady", "recommended_beats": ["development"]},
    },
    {
        "id": "16100000-0000-4000-8000-000000000003",
        "code": "GRID_OPENING_SCENE",
        "name": "Cena de abertura",
        "description": "Uma grande abertura e três quadros de progressão.",
        "panel_count": 4,
        "category": "CINEMATIC",
        "grid_definition": {
            "gutter": 0.02,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 1.00, "height": 0.58, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.60, "width": 0.32, "height": 0.40, "shape": "RECTANGLE"},
                {"x": 0.34, "y": 0.60, "width": 0.32, "height": 0.40, "shape": "RECTANGLE"},
                {"x": 0.68, "y": 0.60, "width": 0.32, "height": 0.40, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "opening", "recommended_beats": ["opening", "context"]},
    },
    {
        "id": "16100000-0000-4000-8000-000000000004",
        "code": "GRID_DYNAMIC_COLUMNS",
        "name": "Duas colunas dinâmicas",
        "description": "Colunas com proporções variadas para ação e reação.",
        "panel_count": 5,
        "category": "DYNAMIC",
        "grid_definition": {
            "gutter": 0.02,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 0.56, "height": 1.00, "shape": "RECTANGLE"},
                {"x": 0.58, "y": 0.00, "width": 0.42, "height": 0.24, "shape": "RECTANGLE"},
                {"x": 0.58, "y": 0.26, "width": 0.42, "height": 0.24, "shape": "RECTANGLE"},
                {"x": 0.58, "y": 0.52, "width": 0.42, "height": 0.22, "shape": "RECTANGLE"},
                {"x": 0.58, "y": 0.76, "width": 0.42, "height": 0.24, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "accelerating", "recommended_beats": ["investigation", "reaction"]},
    },
    {
        "id": "16100000-0000-4000-8000-000000000005",
        "code": "GRID_CINEMATIC_STRIPS",
        "name": "Faixa cinematográfica",
        "description": "Três quadros horizontais para cenas panorâmicas.",
        "panel_count": 3,
        "category": "CINEMATIC",
        "grid_definition": {
            "gutter": 0.02,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 1.00, "height": 0.32, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.34, "width": 1.00, "height": 0.32, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.68, "width": 1.00, "height": 0.32, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "cinematic", "recommended_beats": ["transition", "climax"]},
    },
    {
        "id": "16100000-0000-4000-8000-000000000006",
        "code": "GRID_NARRATIVE_MOSAIC",
        "name": "Mosaico narrativo",
        "description": "Seis quadros variados para histórias densas.",
        "panel_count": 6,
        "category": "MOSAIC",
        "grid_definition": {
            "gutter": 0.02,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 0.48, "height": 0.36, "shape": "RECTANGLE"},
                {"x": 0.50, "y": 0.00, "width": 0.50, "height": 0.24, "shape": "RECTANGLE"},
                {"x": 0.50, "y": 0.26, "width": 0.24, "height": 0.34, "shape": "RECTANGLE"},
                {"x": 0.76, "y": 0.26, "width": 0.24, "height": 0.34, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.38, "width": 0.48, "height": 0.62, "shape": "RECTANGLE"},
                {"x": 0.50, "y": 0.62, "width": 0.50, "height": 0.38, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "dense", "recommended_beats": ["development", "explanation"]},
    },
    {
        "id": "16100000-0000-4000-8000-000000000007",
        "code": "GRID_ACTION_PAGE",
        "name": "Página de ação",
        "description": "Cinco quadros com contraste de tamanhos para o clímax.",
        "panel_count": 5,
        "category": "ACTION",
        "grid_definition": {
            "gutter": 0.018,
            "page_margin": 0.02,
            "panels": [
                {"x": 0.00, "y": 0.00, "width": 0.62, "height": 0.46, "shape": "RECTANGLE"},
                {"x": 0.64, "y": 0.00, "width": 0.36, "height": 0.30, "shape": "RECTANGLE"},
                {"x": 0.64, "y": 0.32, "width": 0.36, "height": 0.34, "shape": "RECTANGLE"},
                {"x": 0.00, "y": 0.48, "width": 0.36, "height": 0.52, "shape": "RECTANGLE"},
                {"x": 0.38, "y": 0.68, "width": 0.62, "height": 0.32, "shape": "RECTANGLE"},
            ],
        },
        "preview_metadata": {"rhythm": "climax", "recommended_beats": ["climax", "resolution"]},
    },
]


def upgrade() -> None:
    op.create_table(
        "hq_story_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comic_project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_mode", sa.String(24), nullable=False, server_default="MANUAL"),
        sa.Column("total_pages", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("narrative_pacing", sa.String(24), nullable=False, server_default="BALANCED"),
        sa.Column("distribution_mode", sa.String(24), nullable=False, server_default="AUTOMATIC"),
        sa.Column("short_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("full_script", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "page_plan",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "continuity_constraints",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "generation_instructions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("generation_status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column(
            "ai_generation_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_generation_requests.id", ondelete="SET NULL"),
        ),
        sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            "comic_project_id",
            name="uq_hq_story_plan_project",
        ),
    )
    op.create_index(
        "ix_hq_story_plan_project",
        "hq_story_plans",
        ["organization_id", "comic_project_id"],
    )
    op.create_index(
        "ix_hq_story_plan_ai_request",
        "hq_story_plans",
        ["organization_id", "ai_generation_request_id"],
    )

    layout_table = sa.table(
        "hq_layout_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("organization_id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("version", sa.String()),
        sa.column("panel_count", sa.Integer()),
        sa.column("orientation", sa.String()),
        sa.column("category", sa.String()),
        sa.column("status", sa.String()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_favorite", sa.Boolean()),
        sa.column("grid_definition", postgresql.JSONB()),
        sa.column("preview_metadata", postgresql.JSONB()),
        sa.column("created_by_user_id", postgresql.UUID(as_uuid=True)),
    )
    connection = op.get_bind()
    system_user = uuid.UUID(SYSTEM_USER_ID)
    for layout in LAYOUTS:
        exists = connection.execute(
            sa.select(sa.literal(1))
            .select_from(layout_table)
            .where(
                layout_table.c.code == layout["code"],
                layout_table.c.is_system.is_(True),
                layout_table.c.status != "ARCHIVED",
            )
            .limit(1)
        ).scalar_one_or_none()
        if exists is not None:
            continue
        op.bulk_insert(
            layout_table,
            [
                {
                    "id": uuid.UUID(layout["id"]),
                    "organization_id": None,
                    "code": layout["code"],
                    "name": layout["name"],
                    "description": layout["description"],
                    "version": "2.0.0",
                    "panel_count": layout["panel_count"],
                    "orientation": "PORTRAIT",
                    "category": layout["category"],
                    "status": "PUBLISHED",
                    "is_system": True,
                    "is_favorite": False,
                    "grid_definition": layout["grid_definition"],
                    "preview_metadata": layout["preview_metadata"],
                    "created_by_user_id": system_user,
                }
            ],
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM hq_layout_templates
            WHERE id IN ('16100000-0000-4000-8000-000000000001'::uuid, '16100000-0000-4000-8000-000000000002'::uuid, '16100000-0000-4000-8000-000000000003'::uuid, '16100000-0000-4000-8000-000000000004'::uuid, '16100000-0000-4000-8000-000000000005'::uuid, '16100000-0000-4000-8000-000000000006'::uuid, '16100000-0000-4000-8000-000000000007'::uuid)
            """
        )
    )
    op.drop_table("hq_story_plans")
