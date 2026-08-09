from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.student_portfolio.schemas import CertificateIssue, CertificateRevoke

BACKEND = Path(__file__).resolve().parents[1]


def test_certificate_requires_evidence_and_reason() -> None:
    with pytest.raises(ValidationError):
        CertificateIssue(student_user_id=uuid4(), title="Certificado", evidence_entry_ids=[])
    with pytest.raises(ValidationError):
        CertificateRevoke(reason="x")


def test_certificate_contract_has_tenant_ownership_audit_and_rollback() -> None:
    router = (BACKEND / "app/student_portfolio/router.py").read_text(encoding="utf-8")
    migration = (BACKEND / "alembic/versions/0058_student_certificates.py").read_text(
        encoding="utf-8"
    )
    assert "StudentPortfolioEntry.organization_id == actor.organization_id" in router
    assert "StudentPortfolioEntry.student_user_id == data.student_user_id" in router
    assert 'action="certificate.issued"' in router and 'action="certificate.revoked"' in router
    assert 'down_revision: str | None = "0057_student_portfolio"' in migration
    assert 'op.drop_table("student_certificates")' in migration
    smoke = (BACKEND.parent / "scripts/smoke_test.py").read_text(encoding="utf-8")
    assert 'version.get("migration_revision") == "0059_school_admissions"' in smoke
