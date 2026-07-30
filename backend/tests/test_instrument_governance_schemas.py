import uuid

import pytest
from pydantic import ValidationError

from app.instrument_governance.schemas import ImportBatchCreate, LicenseCreate, NormEntryCreate, NormGroupCreate


def test_license_rejects_invalid_period():
    with pytest.raises(ValidationError):
        LicenseCreate(
            instrument_id=uuid.uuid4(),
            license_holder="Instituicao",
            permission_reference="DOC-1",
            valid_from="2026-12-31",
            valid_until="2026-01-01",
        )


def test_norm_entry_rejects_inverted_range():
    with pytest.raises(ValidationError):
        NormEntryCreate(raw_min=10, raw_max=2, classification="X")


def test_norm_group_accepts_entries():
    payload = NormGroupCreate(
        instrument_id=uuid.uuid4(),
        code="BR-12",
        version="1",
        name="Norma brasileira 12 anos",
        source_reference="Documento autorizado",
        entries=[{"dimension_code": "TOTAL", "raw_min": 0, "raw_max": 10, "classification": "Inicial"}],
    )
    assert len(payload.entries) == 1


def test_import_checksum_must_be_sha256():
    with pytest.raises(ValidationError):
        ImportBatchCreate(
            instrument_id=uuid.uuid4(),
            filename="instrumento.json",
            file_format="json",
            checksum_sha256="abc",
            manifest={
                "instrument_code": "CT",
                "instrument_version": "1",
                "dimensions": [{"code": "TOTAL"}],
                "items_count": 1,
            },
        )
