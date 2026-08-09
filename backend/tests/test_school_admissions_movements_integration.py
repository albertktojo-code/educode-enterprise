import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SCHOOL_ADMISSIONS_MOVEMENTS_INTEGRATION") != "1",
    reason="executado apenas em banco temporário dedicado",
)


async def test_renewal_and_external_transfer_preserve_enrollment_history() -> None:
    email = os.getenv("INITIAL_ADMIN_EMAIL", "movements-test@example.com")
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "Movements-Test-2027!")
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
            json={"name": "Unidade Movimentos", "code": "MOV", "address": {}},
        )
        assert unit.status_code == 201, unit.text

        async def classroom(name: str, year: int) -> str:
            response = await client.post(
                "/api/v1/classrooms",
                headers=headers,
                json={
                    "name": name,
                    "school_unit_id": unit.json()["id"],
                    "school_year": year,
                    "grade": "7º ano",
                    "shift": "morning",
                },
            )
            assert response.status_code == 201, response.text
            capacity = await client.put(
                f"/api/v1/school-admissions/classrooms/{response.json()['id']}/capacity",
                headers=headers,
                json={
                    "maximum_seats": 10,
                    "reservation_duration_minutes": 60,
                    "waitlist_enabled": True,
                },
            )
            assert capacity.status_code == 200, capacity.text
            return response.json()["id"]

        source_id = await classroom("Turma 2027", 2027)
        target_id = await classroom("Turma 2028", 2028)
        application = await client.post(
            "/api/v1/school-admissions/applications",
            headers=headers,
            json={
                "school_unit_id": unit.json()["id"],
                "classroom_id": source_id,
                "academic_year": 2027,
                "intended_grade": "6º ano",
                "intended_shift": "morning",
                "student": {"legal_name": "Estudante Movimento", "birth_date": "2015-04-10"},
                "guardians": [
                    {
                        "full_name": "Responsável Movimento",
                        "email": "guardian-movements@example.com",
                        "phone": "11999999999",
                        "relationship": "responsável legal",
                        "roles": ["legal"],
                    }
                ],
            },
        )
        assert application.status_code == 201, application.text
        approved = await client.post(
            f"/api/v1/school-admissions/applications/{application.json()['id']}/approve",
            headers=headers,
        )
        assert approved.status_code == 200, approved.text
        source_enrollment_id = approved.json()["enrollment_id"]

        renewal = await client.post(
            f"/api/v1/school-admissions/enrollments/{source_enrollment_id}/renewals",
            headers=headers,
            json={
                "target_classroom_id": target_id,
                "target_academic_year": 2028,
                "reason": "Continuidade",
            },
        )
        assert renewal.status_code == 201, renewal.text
        reviewed = await client.post(
            f"/api/v1/school-admissions/renewals/{renewal.json()['id']}/review",
            headers=headers,
            json={"decision": "approved", "note": "Documentação conferida"},
        )
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "approved"
        assert reviewed.json()["result_application_id"]

        dashboard = await client.get("/api/v1/school-admissions/movements", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        assert len(dashboard.json()["enrollments"]) == 2
        renewed = next(
            item for item in dashboard.json()["enrollments"] if item["classroom_id"] == target_id
        )
        transfer = await client.post(
            f"/api/v1/school-admissions/enrollments/{renewed['id']}/transfers",
            headers=headers,
            json={
                "transfer_type": "external",
                "destination_name": "Escola Destino",
                "reason": "Mudança",
            },
        )
        assert transfer.status_code == 201, transfer.text
        transfer_review = await client.post(
            f"/api/v1/school-admissions/transfers/{transfer.json()['id']}/review",
            headers=headers,
            json={"decision": "approved", "note": "Histórico emitido"},
        )
        assert transfer_review.status_code == 200, transfer_review.text
        assert transfer_review.json()["status"] == "approved"
        dashboard = await client.get("/api/v1/school-admissions/movements", headers=headers)
        assert [item["id"] for item in dashboard.json()["enrollments"]] == [source_enrollment_id]
