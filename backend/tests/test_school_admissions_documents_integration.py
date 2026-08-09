import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SCHOOL_ADMISSIONS_DOCUMENTS_INTEGRATION") != "1",
    reason="executado apenas em banco e armazenamento temporários dedicados",
)


async def test_document_checklist_upload_review_version_and_private_download() -> None:
    email = os.getenv("INITIAL_ADMIN_EMAIL", "documents-test@example.com")
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "Documents-Test-2027!")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password, "remember_me": False},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        unit = await client.post(
            "/api/v1/school-admissions/units",
            headers=headers,
            json={"name": "Unidade Documentos", "code": "DOCS", "address": {}},
        )
        assert unit.status_code == 201, unit.text
        unit_id = unit.json()["id"]
        classroom = await client.post(
            "/api/v1/classrooms",
            headers=headers,
            json={
                "name": "Turma Documentos",
                "school_unit_id": unit_id,
                "school_year": 2027,
                "grade": "7º ano",
                "shift": "morning",
            },
        )
        assert classroom.status_code == 201, classroom.text
        classroom_id = classroom.json()["id"]

        application = await client.post(
            "/api/v1/school-admissions/applications",
            headers=headers,
            json={
                "school_unit_id": unit_id,
                "classroom_id": classroom_id,
                "academic_year": 2027,
                "intended_grade": "7º ano",
                "intended_shift": "morning",
                "student": {"legal_name": "Estudante Documentos", "birth_date": "2015-05-10"},
                "guardians": [
                    {
                        "full_name": "Responsável Documentos",
                        "email": "guardian-documents@example.com",
                        "phone": "11999999999",
                        "relationship": "responsável legal",
                        "roles": ["legal"],
                    }
                ],
            },
        )
        assert application.status_code == 201, application.text
        application_id = application.json()["id"]

        requirement = await client.post(
            "/api/v1/school-admissions/document-requirements",
            headers=headers,
            json={
                "school_unit_id": unit_id,
                "code": "birth_certificate",
                "name": "Certidão de nascimento",
                "description": "Documento completo e legível",
                "is_required": True,
                "accepted_mime_types": ["application/pdf"],
                "max_size_bytes": 1048576,
                "retention_days": 1825,
            },
        )
        assert requirement.status_code == 201, requirement.text
        requirement_id = requirement.json()["id"]

        first_upload = await client.post(
            f"/api/v1/school-admissions/applications/{application_id}/documents",
            headers=headers,
            data={"requirement_id": requirement_id},
            files={"file": ("certidao.pdf", b"%PDF-1.4\nfirst-version", "application/pdf")},
        )
        assert first_upload.status_code == 201, first_upload.text
        document = first_upload.json()
        document_id = document["id"]
        assert document["current_version_number"] == 1
        assert "storage_key" not in document["versions"][0]

        approved = await client.post(
            f"/api/v1/school-admissions/documents/{document_id}/review",
            headers=headers,
            json={"decision": "approved", "note": "Documento conferido"},
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "approved"

        version = approved.json()["versions"][0]
        download = await client.get(f"/api/v1{version['download_path']}", headers=headers)
        assert download.status_code == 200, download.text
        assert download.content.startswith(b"%PDF-1.4")
        assert download.headers["cache-control"] == "private, no-store"

        second_upload = await client.post(
            f"/api/v1/school-admissions/applications/{application_id}/documents",
            headers=headers,
            data={"requirement_id": requirement_id},
            files={"file": ("certidao-v2.pdf", b"%PDF-1.4\nsecond-version", "application/pdf")},
        )
        assert second_upload.status_code == 201, second_upload.text
        assert second_upload.json()["current_version_number"] == 2
        assert len(second_upload.json()["versions"]) == 2

        checklist = await client.get(
            f"/api/v1/school-admissions/applications/{application_id}/documents",
            headers=headers,
        )
        assert checklist.status_code == 200, checklist.text
        assert checklist.json()[0]["document"]["status"] == "submitted"

        foreign = await client.get(
            f"/api/v1/school-admissions/documents/{uuid4()}/versions/{uuid4()}/download",
            headers=headers,
        )
        assert foreign.status_code == 404
