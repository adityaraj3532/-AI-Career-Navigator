import pytest
from httpx import AsyncClient
from app.main import app
from app.core.exceptions import AppException


# Add dynamic test endpoints to verify error handlers
@app.get("/test/custom-app-error", include_in_schema=False)
async def raise_custom_error():
    raise AppException(
        message="Resource not found or unauthorized",
        status_code=403,
        code="FORBIDDEN_RESOURCE",
        details={"resource_id": 42},
    )


@app.get("/test/unhandled-error", include_in_schema=False)
async def raise_unhandled_error():
    raise RuntimeError("Unexpected server crash")


@pytest.mark.asyncio
async def test_404_error_standard_format(async_client: AsyncClient):
    response = await async_client.get("/v1/non-existent-route")
    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["code"] == "HTTP_404"
    assert "Not Found" in error["message"]
    assert "request_id" in error
    assert response.headers.get("X-Request-ID") == error["request_id"]


@pytest.mark.asyncio
async def test_custom_app_exception_standard_format(async_client: AsyncClient):
    response = await async_client.get("/test/custom-app-error")
    assert response.status_code == 403
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["code"] == "FORBIDDEN_RESOURCE"
    assert error["message"] == "Resource not found or unauthorized"
    assert error["details"] == {"resource_id": 42}
    assert "request_id" in error
    assert response.headers.get("X-Request-ID") == error["request_id"]


@pytest.mark.asyncio
async def test_unhandled_exception_standard_format(async_client: AsyncClient):
    response = await async_client.get("/test/unhandled-error")
    assert response.status_code == 500
    data = response.json()

    assert "error" in data
    error = data["error"]
    assert error["code"] == "INTERNAL_SERVER_ERROR"
    assert error["message"] == "An unexpected internal server error occurred."
    assert "request_id" in error
    assert response.headers.get("X-Request-ID") == error["request_id"]
