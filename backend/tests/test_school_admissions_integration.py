import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SCHOOL_ADMISSIONS_INTEGRATION") != "1",
    reason="executado apenas em banco temporário dedicado",
)


async def test_admissions_capacity_reservation_waitlist_and_approval() -> None:
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admissions-test@example.com")
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "Admissions-Test-2027!")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": admin_email,
                "password": admin_password,
                "remember_me": False,
            },
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        unit_response = await client.post(
            "/api/v1/school-admissions/units",
            headers=headers,
            json={"name": "Unidade Teste", "code": "TESTE", "address": {}},
        )
        assert unit_response.status_code == 201, unit_response.text
        unit_id = unit_response.json()["id"]

        classroom_response = await client.post(
            "/api/v1/classrooms",
            headers=headers,
            json={
                "name": "Turma Teste",
                "school_unit_id": unit_id,
                "school_year": 2027,
                "grade": "6º ano",
                "shift": "morning",
            },
        )
        assert classroom_response.status_code == 201, classroom_response.text
        classroom_id = classroom_response.json()["id"]

        capacity = await client.put(
            f"/api/v1/school-admissions/classrooms/{classroom_id}/capacity",
            headers=headers,
            json={
                "maximum_seats": 1,
                "reservation_duration_minutes": 60,
                "waitlist_enabled": True,
            },
        )
        assert capacity.status_code == 200, capacity.text
        assert capacity.json()["available_seats"] == 1

        async def application(student_name: str, guardian_email: str) -> str:
            response = await client.post(
                "/api/v1/school-admissions/applications",
                headers=headers,
                json={
                    "school_unit_id": unit_id,
                    "classroom_id": classroom_id,
                    "academic_year": 2027,
                    "intended_grade": "6º ano",
                    "intended_shift": "morning",
                    "student": {
                        "legal_name": student_name,
                        "birth_date": "2016-04-10",
                    },
                    "guardians": [
                        {
                            "full_name": f"Responsável {student_name}",
                            "email": guardian_email,
                            "phone": "11999999999",
                            "relationship": "responsável legal",
                            "roles": ["legal"],
                        }
                    ],
                },
            )
            assert response.status_code == 201, response.text
            return response.json()["id"]

        first_application = await application("Estudante Um", "guardian-one@example.com")
        reservation = await client.post(
            f"/api/v1/school-admissions/applications/{first_application}/reserve",
            headers=headers,
        )
        assert reservation.status_code == 200, reservation.text
        assert reservation.json()["outcome"] == "reserved"

        same_reservation = await client.post(
            f"/api/v1/school-admissions/applications/{first_application}/reserve",
            headers=headers,
        )
        assert same_reservation.json()["outcome"] == "already_reserved"

        approval = await client.post(
            f"/api/v1/school-admissions/applications/{first_application}/approve",
            headers=headers,
        )
        assert approval.status_code == 200, approval.text
        assert approval.json()["status"] == "pending_identity"
        enrollment_id = approval.json()["enrollment_id"]

        same_approval = await client.post(
            f"/api/v1/school-admissions/applications/{first_application}/approve",
            headers=headers,
        )
        assert same_approval.status_code == 200, same_approval.text
        assert same_approval.json()["enrollment_id"] == enrollment_id

        second_application = await application("Estudante Dois", "guardian-two@example.com")
        waitlist = await client.post(
            f"/api/v1/school-admissions/applications/{second_application}/reserve",
            headers=headers,
        )
        assert waitlist.status_code == 200, waitlist.text
        assert waitlist.json()["outcome"] == "waitlisted"
        assert waitlist.json()["waitlist_position"] == 1

        dashboard = await client.get("/api/v1/school-admissions/dashboard", headers=headers)
        assert dashboard.status_code == 200, dashboard.text
        summary = dashboard.json()
        assert summary["approved"] == 1
        assert summary["waitlisted"] == 1
        assert summary["capacities"][0]["occupied_seats"] == 1
        assert summary["capacities"][0]["available_seats"] == 0

        foreign_classroom = uuid4()
        denied = await client.get(
            f"/api/v1/school-admissions/classrooms/{foreign_classroom}/capacity",
            headers=headers,
        )
        assert denied.status_code == 404
