from pathlib import Path

import pytest
from fastapi import HTTPException

from app.db import model_registry
from app.school_admissions.contracts import render_contract, validate_template
from app.school_admissions.schemas import EnrollmentContractAccept

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_contract_renderer_replaces_only_canonical_variables_and_hashes_snapshot() -> None:
    rendered, content_hash = render_contract(
        "Aluno {{nome_aluno}} no ano {{ano_letivo}}.",
        {"nome_aluno": "Ana", "ano_letivo": "2027"},
    )
    assert rendered == "Aluno Ana no ano 2027."
    assert len(content_hash) == 64
    with pytest.raises(HTTPException):
        validate_template("{{variavel_insegura}}")


def test_acceptance_requires_explicit_confirmation() -> None:
    assert EnrollmentContractAccept(confirmation="ACEITO", accepted_name="Maria").confirmation
    with pytest.raises(ValueError):
        EnrollmentContractAccept(confirmation="sim", accepted_name="Maria")


def test_contract_models_are_tenant_scoped_and_immutable() -> None:
    expected = {
        "enrollment_contract_templates",
        "enrollment_contracts",
        "enrollment_contract_versions",
        "enrollment_contract_acceptances",
    }
    assert expected <= set(model_registry.registered_table_names())
    for table_name in expected:
        assert "organization_id" in model_registry.Base.metadata.tables[table_name].columns
    versions = model_registry.Base.metadata.tables["enrollment_contract_versions"]
    assert "rendered_content" in versions.columns
    assert "content_sha256" in versions.columns


def test_contract_migration_is_reversible_and_based_on_0060() -> None:
    migration = (BACKEND / "alembic/versions/0061_enrollment_contracts.py").read_text(
        encoding="utf-8"
    )
    assert 'revision: str = "0061_enrollment_contracts"' in migration
    assert 'down_revision: str | None = "0060_enrollment_documents"' in migration
    assert migration.count("op.create_table(") == 4
    assert migration.count("op.drop_table(") == 4
    assert "content_sha256" in migration
    assert "postgresql_nulls_not_distinct=True" in migration


def test_contract_routes_scope_generate_accept_and_void() -> None:
    router = (BACKEND / "app/school_admissions/router.py").read_text(encoding="utf-8")
    contracts = (BACKEND / "app/school_admissions/contracts.py").read_text(encoding="utf-8")
    assert '"/applications/{application_id}/contract"' in router
    assert '"/contracts/{contract_id}/accept"' in router
    assert '"/contracts/{contract_id}/void"' in router
    assert 'action="enrollment_contract.accepted"' in router
    assert "GuardianProfile.user_id == actor.user_id" in router
    assert "EnrollmentContract.organization_id == organization_id" in contracts


def test_secretariat_exposes_a_separate_contract_module() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "pages/SchoolSecretariatLayout.tsx").read_text(encoding="utf-8")
    page = (FRONTEND / "pages/SchoolContractsPage.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "features/schoolAdmissions/api.ts").read_text(encoding="utf-8")
    assert 'path="contratos"' in app
    assert "/secretaria/contratos" in layout
    assert 'aria-live="polite"' in page
    assert "schoolAdmissionsApi.generateContract" in page
    assert "fetch(" not in api


def test_contract_increment_does_not_create_financial_or_signature_provider_domains() -> None:
    models = (BACKEND / "app/school_admissions/models.py").read_text(encoding="utf-8")
    migration = (BACKEND / "alembic/versions/0061_enrollment_contracts.py").read_text(
        encoding="utf-8"
    )
    assert "school_invoices" not in models + migration
    assert "platform_invoices" not in models + migration
    assert "PaymentProvider" not in models + migration
