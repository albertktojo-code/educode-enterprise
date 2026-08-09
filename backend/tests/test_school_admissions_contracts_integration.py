import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SCHOOL_ADMISSIONS_CONTRACTS_INTEGRATION") != "1",
    reason="executado apenas em banco temporário dedicado",
)


async def test_contract_template_generation_versions_and_void() -> None:
    email = os.getenv("INITIAL_ADMIN_EMAIL", "contracts-test@example.com")
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "Contracts-Test-2027!")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password, "remember_me": False},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        unit = await client.post(
            "/api/v1/school-admissions/units",
            headers=headers,
            json={"name": "Unidade Contratos", "code": "CONTRACTS", "address": {}},
        )
        classroom = await client.post(
            "/api/v1/classrooms",
            headers=headers,
            json={
                "name": "Turma Contratos",
                "school_unit_id": unit.json()["id"],
                "school_year": 2027,
                "grade": "8º ano",
                "shift": "morning",
            },
        )
        application = await client.post(
            "/api/v1/school-admissions/applications",
            headers=headers,
            json={
                "school_unit_id": unit.json()["id"],
                "classroom_id": classroom.json()["id"],
                "academic_year": 2027,
                "intended_grade": "8º ano",
                "intended_shift": "morning",
                "student": {"legal_name": "Estudante Contrato", "birth_date": "2014-05-10"},
                "guardians": [
                    {
                        "full_name": "Responsável Contrato",
                        "email": "guardian-contract@example.com",
                        "phone": "11999999999",
                        "relationship": "responsável legal",
                        "roles": ["legal"],
                    }
                ],
            },
        )
        guardians = await client.get(
            f"/api/v1/school-admissions/applications/{application.json()['id']}/guardians",
            headers=headers,
        )
        assert guardians.status_code == 200 and len(guardians.json()) == 1
        contract_body = "Contrato de {student} com {guardian} para {year}.".format(
            student="{{nome_aluno}}",
            guardian="{{nome_responsavel}}",
            year="{{ano_letivo}}",
        )
        template = await client.post(
            "/api/v1/school-admissions/contract-templates",
            headers=headers,
            json={
                "school_unit_id": unit.json()["id"],
                "code": "standard",
                "name": "Contrato padrão",
                "body_template": contract_body,
            },
        )
        assert template.status_code == 201, template.text
        payload = {
            "template_id": template.json()["id"],
            "guardian_profile_id": guardians.json()[0]["id"],
        }
        first = await client.post(
            f"/api/v1/school-admissions/applications/{application.json()['id']}/contract",
            headers=headers,
            json=payload,
        )
        assert first.status_code == 200, first.text
        assert first.json()["current_version_number"] == 1
        assert "Estudante Contrato" in first.json()["versions"][0]["rendered_content"]
        second = await client.post(
            f"/api/v1/school-admissions/applications/{application.json()['id']}/contract",
            headers=headers,
            json=payload,
        )
        assert second.status_code == 200, second.text
        assert second.json()["current_version_number"] == 2
        assert len(second.json()["versions"]) == 2
        admin_accept = await client.post(
            f"/api/v1/school-admissions/contracts/{second.json()['id']}/accept",
            headers=headers,
            json={"confirmation": "ACEITO", "accepted_name": "Responsável Contrato"},
        )
        assert admin_accept.status_code == 403
        voided = await client.post(
            f"/api/v1/school-admissions/contracts/{second.json()['id']}/void",
            headers=headers,
            json={"reason": "Nova versão será emitida"},
        )
        assert voided.status_code == 200 and voided.json()["status"] == "voided"
