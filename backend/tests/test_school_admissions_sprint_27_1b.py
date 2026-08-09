from pathlib import Path

import pytest
from pydantic import ValidationError

from app.db import model_registry
from app.school_admissions.schemas import (
    EnrollmentDocumentRequirementCreate,
    EnrollmentDocumentReviewWrite,
)

BACKEND = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND.parent
FRONTEND = PROJECT_ROOT / "frontend/src"
if not FRONTEND.exists():
    FRONTEND = Path("/frontend/src")


def test_document_contracts_validate_mime_size_retention_and_review_notes() -> None:
    requirement = EnrollmentDocumentRequirementCreate(
        code="birth_certificate",
        name="Certidão de nascimento",
    )
    assert requirement.accepted_mime_types == [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]
    with pytest.raises(ValidationError):
        EnrollmentDocumentRequirementCreate(
            code="invalid code",
            name="Documento",
        )
    with pytest.raises(ValidationError):
        EnrollmentDocumentReviewWrite(decision="rejected", note="")


def test_document_models_are_tenant_scoped_and_versioned() -> None:
    expected = {
        "enrollment_document_requirements",
        "enrollment_documents",
        "enrollment_document_versions",
        "enrollment_document_reviews",
    }
    assert expected <= set(model_registry.registered_table_names())
    for table_name in expected:
        assert "organization_id" in model_registry.Base.metadata.tables[table_name].columns
    versions = model_registry.Base.metadata.tables["enrollment_document_versions"]
    assert "checksum_sha256" in versions.columns
    assert "storage_key" in versions.columns


def test_document_migration_is_single_reversible_and_based_on_current_head() -> None:
    migration = (BACKEND / "alembic/versions/0060_enrollment_documents.py").read_text(
        encoding="utf-8"
    )
    assert 'revision: str = "0060_enrollment_documents"' in migration
    assert 'down_revision: str | None = "0059_school_admissions"' in migration
    assert migration.count("op.create_table(") == 4
    assert 'op.drop_table("enrollment_document_requirements")' in migration
    assert 'op.drop_table("enrollment_document_versions")' in migration
    assert "checksum_sha256" in migration
    assert "postgresql_nulls_not_distinct=True" in migration


def test_private_storage_validates_signature_and_never_exposes_storage_key() -> None:
    storage = (BACKEND / "app/school_admissions/document_storage.py").read_text(encoding="utf-8")
    schemas = (BACKEND / "app/school_admissions/schemas.py").read_text(encoding="utf-8")
    assert "MIME_EXTENSIONS" in storage
    assert "_validate_signature" in storage
    assert "max_size_bytes" in storage
    assert "storage.put_bytes" in storage
    assert "storage_key" not in schemas
    assert "download_path" in schemas


def test_routes_scope_every_operation_and_audit_sensitive_access() -> None:
    router = (BACKEND / "app/school_admissions/router.py").read_text(encoding="utf-8")
    services = (BACKEND / "app/school_admissions/services.py").read_text(encoding="utf-8")
    assert '"/document-requirements"' in router
    assert '"/applications/{application_id}/documents"' in router
    assert '"/documents/{document_id}/review"' in router
    assert '"Cache-Control": "private, no-store"' in router
    assert 'action="enrollment_document.uploaded"' in router
    assert 'action="enrollment_document.accessed"' in router
    assert "EnrollmentDocument.organization_id == organization_id" in services
    assert "EnrollmentDocumentVersion.organization_id == document.organization_id" in services


def test_secretariat_frontend_is_split_into_clear_modules() -> None:
    app = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    layout = (FRONTEND / "pages/SchoolSecretariatLayout.tsx").read_text(encoding="utf-8")
    documents = (FRONTEND / "pages/SchoolDocumentsPage.tsx").read_text(encoding="utf-8")
    api = (FRONTEND / "features/schoolAdmissions/api.ts").read_text(encoding="utf-8")
    for route in ("matriculas", "documentos", "turmas-vagas"):
        assert f'path="{route}"' in app
    assert 'aria-label="Módulos da Secretaria"' in layout
    assert 'aria-live="polite"' in documents
    assert "schoolAdmissionsApi.uploadDocument" in documents
    assert "apiBlob" in api
    assert "fetch(" not in api


def test_financial_and_identity_fields_remain_outside_document_increment() -> None:
    models = (BACKEND / "app/school_admissions/models.py").read_text(encoding="utf-8")
    migration = (BACKEND / "alembic/versions/0060_enrollment_documents.py").read_text(
        encoding="utf-8"
    )
    assert "school_invoices" not in models + migration
    assert "platform_invoices" not in models + migration
    assert 'sa.Column("cpf"' not in migration
    assert 'sa.Column("rg"' not in migration
