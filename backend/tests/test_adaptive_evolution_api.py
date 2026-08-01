from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adaptive_evolution.compat import ActorContext, resolve_actor_context
from app.adaptive_evolution.router import router


app = FastAPI()


async def authenticated_actor() -> ActorContext:
    return ActorContext(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership_id=uuid.uuid4(),
        roles=frozenset({"TEACHER"}),
    )


app.dependency_overrides[resolve_actor_context] = authenticated_actor
app.include_router(router)
client = TestClient(app)


def test_health() -> None:
    response = client.get("/adaptive-evolution/health")
    assert response.status_code == 200
    assert response.json()["sprint"] == "14.1"


def test_review_calculator_endpoint() -> None:
    response = client.post(
        "/adaptive-evolution/reviews/calculate-next",
        json={
            "mastery_score": 0.55,
            "confidence_score": 0.65,
            "result_score": 0.70,
            "hint_level_used": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["interval_days"] >= 1


def test_feedback_endpoint() -> None:
    response = client.post(
        "/adaptive-evolution/feedback/adapt",
        json={
            "is_correct": False,
            "mastery_level": "ADEQUADO",
            "error_type": "INTERPRETATION",
            "attempt_number": 1,
            "hint_level_used": 0,
            "skill_name": "Interpretação do problema",
        },
    )
    assert response.status_code == 200
    assert "enunciado" in response.json()["content"].lower()


def test_accessibility_preview_endpoint() -> None:
    response = client.post(
        "/adaptive-evolution/accessibility/preview",
        json={
            "source_resource_type": "ACTIVITY",
            "source_resource_id": str(uuid.uuid4()),
            "title": "Atividade de algoritmo",
            "content": "Primeiro observe o problema; depois separe as etapas; por fim escreva a solução.",
            "adaptation_type": "STEP_BY_STEP",
            "learning_objective": "Organizar uma solução algorítmica.",
            "assessment_criteria": ["Sequência lógica"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NEEDS_REVIEW"
    assert "1." in body["content"]
