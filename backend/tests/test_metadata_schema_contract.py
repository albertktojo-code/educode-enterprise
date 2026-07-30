from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
from app.db.model_registry import registered_table_names

EXPECTED_UNIQUE_CONSTRAINTS = {
    "art_direction_presets": {"art_direction_presets_code_key"},
    "assignment_item_metrics": {
        "assignment_item_metrics_assignment_question_id_key"
    },
    "auth_sessions": {
        "auth_sessions_legacy_refresh_token_hash_key",
        "auth_sessions_previous_refresh_token_hash_key",
        "auth_sessions_refresh_token_hash_key",
    },
    "computational_thinking_pillars": {
        "computational_thinking_pillars_code_key"
    },
    "creative_bibles": {"creative_bibles_generation_project_id_key"},
    "organizations": {"uq_organizations_slug"},
    "password_reset_tokens": {"password_reset_tokens_token_hash_key"},
    "users": {"uq_users_email"},
}

EXPECTED_PRESERVED_INDEXES = {
    "adaptive_skill_states": {"ix_adaptive_skill_dimension"},
    "assignment_item_metrics": {
        "ix_assignment_item_metrics_assignment_question_id"
    },
    "document_chunks": {
        "ix_document_chunks_embedding_hnsw",
        "ix_document_chunks_search_vector",
    },
    "hq_editor_pages": {
        "ix_hq_editor_page_type",
        "uq_hq_editor_single_back_cover",
        "uq_hq_editor_single_cover",
    },
    "material_assignments": {"ix_material_assignments_status_due"},
    "operational_alert_events": {"ix_alert_events_org_status"},
    "operational_metric_snapshots": {"ix_metric_snapshots_name_time"},
    "skill_prerequisites": {"ix_skill_prereq_dimension"},
    "student_attempts": {"ix_student_attempts_student_status"},
    "user_notifications": {"ix_user_notifications_user_status"},
}


def test_critical_unique_constraints_are_registered() -> None:
    assert registered_table_names()
    for table_name, expected_names in EXPECTED_UNIQUE_CONSTRAINTS.items():
        table = Base.metadata.tables[table_name]
        registered_names = {
            constraint.name
            for constraint in table.constraints
            if constraint.name is not None
        }
        assert expected_names <= registered_names


def test_specialized_and_composite_indexes_are_registered() -> None:
    for table_name, expected_names in EXPECTED_PRESERVED_INDEXES.items():
        table = Base.metadata.tables[table_name]
        registered_names = {index.name for index in table.indexes}
        assert expected_names <= registered_names

    chunks = Base.metadata.tables["document_chunks"]
    hnsw = next(
        index
        for index in chunks.indexes
        if index.name == "ix_document_chunks_embedding_hnsw"
    )
    search = next(
        index
        for index in chunks.indexes
        if index.name == "ix_document_chunks_search_vector"
    )
    assert hnsw.dialect_options["postgresql"]["using"] == "hnsw"
    assert hnsw.dialect_options["postgresql"]["ops"] == {
        "embedding": "vector_cosine_ops"
    }
    assert search.dialect_options["postgresql"]["using"] == "gin"

    pages = Base.metadata.tables["hq_editor_pages"]
    partial_indexes = {
        index.name: index for index in pages.indexes if index.name.startswith("uq_hq_")
    }
    assert all(index.unique for index in partial_indexes.values())
    assert {
        str(index.dialect_options["postgresql"]["where"])
        for index in partial_indexes.values()
    } == {"page_type = 'BACK_COVER'", "page_type = 'COVER'"}


def test_postgresql_jsonb_contract_preserves_intentional_json_columns() -> None:
    jsonb_columns = (
        ("adaptive_audit_events", "details"),
        ("comic_panels", "visual_prompt"),
        ("creative_bibles", "color_palette"),
        ("generation_projects", "bncc_skills"),
        ("infrastructure_clusters", "capabilities"),
        ("operational_alert_events", "evidence"),
        ("rag_contexts", "structured_context"),
        ("release_validation_runs", "checks"),
        ("document_chunks", "metadata"),
    )
    for table_name, column_name in jsonb_columns:
        assert isinstance(
            Base.metadata.tables[table_name].c[column_name].type,
            JSONB,
        )

    intentional_json_columns = (
        ("generated_comics", "art_direction"),
        ("generated_comics", "canvas_config"),
        ("comic_pages", "background_config"),
        ("comic_pages", "guides_config"),
    )
    for table_name, column_name in intentional_json_columns:
        column_type = Base.metadata.tables[table_name].c[column_name].type
        assert isinstance(column_type, JSON)
        assert not isinstance(column_type, JSONB)
