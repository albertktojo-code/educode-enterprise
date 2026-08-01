from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adaptive_insights.router import router


def test_health_endpoint() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    response = TestClient(app).get("/api/v1/adaptive-insights/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "module": "adaptive-insights",
        "sprint": "14.2",
    }
