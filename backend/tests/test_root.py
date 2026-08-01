from httpx import AsyncClient

from app.core.config import get_settings
from app.main import app


async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]


async def test_liveness_does_not_require_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.json()["version"] == get_settings().app_version


def test_openapi_schema_builds_with_hq_learning_analytics() -> None:
    schema = app.openapi()

    assert (
        "/api/v1/comic-page-editor/activity-deliveries/{delivery_id}/analytics/generate"
        in schema["paths"]
    )
