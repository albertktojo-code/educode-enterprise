from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


def test_migration_chain_and_single_table():
    migration = (
        BACKEND
        / "alembic/versions/0052_hq_student_experience.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "0052_hq_student_experience"' in migration
    assert (
        'down_revision: str | None = "0051_hq_activity_delivery"'
        in migration
    )
    assert migration.count("op.create_table(") == 1
    assert '"hq_student_experience_states"' in migration


def test_canonical_reader_and_delivery_are_reused():
    service = (
        BACKEND / "app/comic_page_editor/student_experience.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "AssessmentPublication",
        "HQActivityDeliveryLink",
        "HQActivityBinding",
        "HQEditorPage",
    ):
        assert marker in service
    assert "StudentAttempt" not in service
    manifest_source = service.split(
        "async def save_experience_state", maxsplit=1
    )[0]
    assert "AssessmentSession" in manifest_source
    assert "AssessmentAutosave" in manifest_source
    assert "session.add(" not in manifest_source


def test_student_routes_exist():
    router = (
        BACKEND / "app/comic_page_editor/router.py"
    ).read_text(encoding="utf-8")
    assert "/student-experience/publications/{publication_id}" in router
    assert "/state" in router
    assert "append_domain_audit" in router
    assert "require_role(actor, STUDENT_ROLES)" in router


def test_student_frontend_uses_canonical_delivery_flow():
    frontend = BACKEND.parent / "frontend"
    if not frontend.exists():
        pytest.skip("Frontend não é montado no container do backend.")
    api = (frontend / "src/features/hqStudentExperience/api.ts").read_text(
        encoding="utf-8"
    )
    page = (
        frontend
        / "src/features/hqStudentExperience/HQStudentExperiencePage.tsx"
    ).read_text(encoding="utf-8")
    assert "/assessment-delivery" in api
    assert "autosaveResponse" in api
    assert "submitSession" in api
    assert "simulateCorrection" not in api
    assert "simulateCorrection" not in page


def test_version_keeps_16_11_compatibility():
    config = (
        BACKEND / "app/core/config.py"
    ).read_text(encoding="utf-8")
    assert 'app_version: str = "0.16.11.' in config
