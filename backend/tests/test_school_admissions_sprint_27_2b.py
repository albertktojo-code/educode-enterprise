from pathlib import Path

BACKEND = Path(__file__).parents[1]
ROOT = BACKEND.parent
FRONTEND = ROOT / "frontend/src"


def test_movement_models_are_tenant_scoped_and_auditable() -> None:
    models = (BACKEND / "app/school_admissions/models.py").read_text(encoding="utf-8")
    assert "class EnrollmentRenewalRequest" in models
    assert "class EnrollmentTransferRequest" in models
    assert models.count('ForeignKey("organizations.id", ondelete="CASCADE")') >= 2
    assert "requested_by_user_id" in models
    assert "reviewed_by_user_id" in models
    assert "result_application_id" in models


def test_movement_api_reuses_canonical_enrollment_and_capacity_flow() -> None:
    movement = (BACKEND / "app/school_admissions/movements.py").read_text(encoding="utf-8")
    assert "approve_application(session, actor, application, commit=False)" in movement
    assert "EnrollmentStatus.TRANSFERRED" in movement
    assert '"enrollment.renewal.requested"' in movement
    assert '"enrollment.transfer.requested"' in movement
    assert "ensure_admissions_staff" in movement


def test_migration_is_reversible_and_follows_contracts() -> None:
    migration = (BACKEND / "alembic/versions/0062_enrollment_movements.py").read_text(
        encoding="utf-8"
    )
    assert 'revision: str = "0062_enrollment_movements"' in migration
    assert 'down_revision: str | None = "0061_enrollment_contracts"' in migration
    assert '"enrollment_renewal_requests"' in migration
    assert '"enrollment_transfer_requests"' in migration
    assert 'op.drop_table("enrollment_transfer_requests")' in migration
    assert 'op.drop_table("enrollment_renewal_requests")' in migration


def test_frontend_exposes_separate_movement_module() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "pages/SchoolSecretariatLayout.tsx").read_text(encoding="utf-8")
    page = (FRONTEND / "pages/SchoolMovementsPage.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "features/schoolAdmissions/api.ts").read_text(encoding="utf-8")
    assert 'path="movimentacoes"' in app
    assert "/secretaria/movimentacoes" in layout
    assert "Nova rematrícula" in page
    assert "Nova transferência" in page
    assert "createRenewal" in api and "createTransfer" in api


def test_registry_tracks_new_incremental_tables() -> None:
    registry = (BACKEND / "app/db/model_registry.py").read_text(encoding="utf-8")
    assert '"enrollment_renewal_"' in registry
    assert '"enrollment_transfer_"' in registry
