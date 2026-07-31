from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_sprint_reuses_existing_tables_without_parallel_domain_migration():
    migrations = BACKEND / "alembic" / "versions"
    for migration in migrations.glob("0055*"):
        migration_source = migration.read_text(encoding="utf-8")
        assert "op.create_table(" not in migration_source
        assert '"adaptive_' not in migration_source
        assert '"intervention_' not in migration_source
        assert '"hq_' not in migration_source

    analytics = (
        BACKEND / "app/comic_page_editor/learning_analytics.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "HQLearningAnalyticsSnapshot",
        "LearningAlert",
        "AssessmentSession",
        "AssessmentResponse",
        "QuestionSkillLink",
        "ComicReaderEvent",
    ):
        assert marker in analytics


def test_post_hq_alerts_are_traceable_and_human_reviewed():
    analytics = (
        BACKEND / "app/comic_page_editor/learning_analytics.py"
    ).read_text(encoding="utf-8")
    for marker in (
        '"source_snapshot_id"',
        '"publication_id"',
        '"release_id"',
        '"human_approval_required": True',
        '"hq_post_learning"',
    ):
        assert marker in analytics

    orchestration = (
        BACKEND / "app/intervention_orchestration/services.py"
    ).read_text(encoding="utf-8")
    assert '"hq_learning_analytics"' in orchestration
    assert 'status="pending_review"' in orchestration
    assert "created_by_ai=False" in orchestration


def test_recommendations_use_existing_orchestration_routes_and_audit():
    router = (
        BACKEND / "app/intervention_orchestration/router.py"
    ).read_text(encoding="utf-8")
    for marker in (
        '"/proposals/from-alert/{alert_id}"',
        '"/proposals/{recommendation_id}"',
        "require_teacher(actor)",
        "append_domain_audit",
        "HQ_RECOMMENDATION_SOURCE_KINDS",
    ):
        assert marker in router


def test_group_privacy_and_latest_snapshot_scope_are_enforced():
    analytics = (
        BACKEND / "app/comic_page_editor/learning_analytics.py"
    ).read_text(encoding="utf-8")
    assert 'group_scope = normalized_scope != "STUDENT"' in analytics
    assert (
        "models.HQLearningAnalyticsSnapshot.scope_type == normalized_scope"
        in analytics
    )
    assert "scope_filter" in analytics


def test_student_experience_exposes_accessible_release():
    backend_source = (
        BACKEND / "app/comic_page_editor/student_experience.py"
    ).read_text(encoding="utf-8")
    assert "accessible_published_release_id" in backend_source
    assert '"release_id"' in backend_source


def test_adaptive_taxonomy_does_not_publish_automatically():
    policies = (
        BACKEND / "app/intervention_orchestration/policies.py"
    ).read_text(encoding="utf-8")
    for recommendation_type in (
        "guided_reread",
        "simplified_activity",
        "equivalent_activity",
        "reinforcement",
        "consolidation",
        "deepening",
        "advanced_challenge",
    ):
        assert recommendation_type in policies
    assert '"requires_teacher_selection": True' in policies


def test_version_is_16_11_5():
    config = (BACKEND / "app/core/config.py").read_text(encoding="utf-8")
    assert 'app_version: str = "0.16.11.' in config
    assert "sprint-16.11." in config


def test_release_ledger_reads_current_alembic_revision():
    seed = (BACKEND / "app/db/seed.py").read_text(encoding="utf-8")
    assert "SELECT version_num FROM alembic_version LIMIT 1" in seed
    assert 'migration_revision="0025_ops_observability"' not in seed
