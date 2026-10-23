import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(async_client: AsyncClient):
    response = await async_client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_request_id_generated_and_returned(async_client: AsyncClient):
    response = await async_client.get("/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    assert len(req_id) > 0


@pytest.mark.asyncio
async def test_custom_request_id_propagated(async_client: AsyncClient):
    custom_id = "test-request-id-99999"
    response = await async_client.get(
        "/v1/health", headers={"X-Request-ID": custom_id}
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_readiness_endpoint(async_client: AsyncClient):
    response = await async_client.get("/v1/ready")
    # Response code depends on live DB/Redis availability (200 if up, 503 if down)
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "redis" in data["dependencies"]
