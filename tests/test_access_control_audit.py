import json
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient

from app.api.deps import get_current_user
from app.main import app
from app.models.portfolio import UserPortfolio
from app.models.user import User


EXPLICIT_UNAUTHENTICATED_ALLOWLIST = {
    ("GET", "/health"),
    ("GET", "/v1/health"),
    ("GET", "/v1/ready"),
    ("POST", "/v1/auth/signup"),
    ("POST", "/v1/auth/login"),
    ("POST", "/v1/auth/refresh"),
    ("POST", "/v1/auth/forgot-password"),
    ("POST", "/v1/auth/reset-password"),
    ("POST", "/v1/auth/logout"),
    ("GET", "/v1/careers"),
    ("GET", "/v1/careers/search"),
    ("GET", "/v1/careers/{career_id}"),
    ("POST", "/v1/compare"),
    ("GET", "/v1/portfolio/p/{slug}"),
}

FORBIDDEN_PUBLIC_KEYS = [
    "user_id",
    "email",
    "internal_id",
    "id",
    "test_results",
    "diagnostic_tests",
    "budget",
    "hours_available",
    "hours_available_per_week",
    "target_career",
    "scores",
    "dimension_weights",
    "raw_score",
    "hashed_password",
]


def test_all_endpoints_require_auth_or_are_explicitly_allowlisted():
    """Security Invariant: Walks app.routes and fails if any route neither requires get_current_user
    nor is on the explicit public allowlist.
    """
    unprotected_routes = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        # Ignore synthetic test routes registered strictly by test harness
        if route.path.startswith("/test/"):
            continue

        # Collect all dependencies in the dependency tree
        all_calls = set()

        def _traverse(dep):
            for d in dep.dependencies:
                all_calls.add(d.call)
                _traverse(d)

        _traverse(route.dependant)

        for method in route.methods:
            if method in ("OPTIONS", "HEAD"):
                continue

            route_pair = (method, route.path)
            if get_current_user not in all_calls:
                if route_pair not in EXPLICIT_UNAUTHENTICATED_ALLOWLIST:
                    unprotected_routes.append(route_pair)

    assert not unprotected_routes, (
        f"Broken Access Control! The following routes are missing authentication and are not allowlisted:\n"
        f"{unprotected_routes}"
    )


def test_openapi_snapshot_match():
    """OpenAPI Snapshot Test: Fails with a diff if any new or modified endpoint is introduced."""
    snapshot_path = Path(__file__).parent / "snapshots" / "openapi_snapshot.json"
    assert snapshot_path.is_file(), f"Snapshot file missing at {snapshot_path}"

    expected_spec = json.loads(snapshot_path.read_text(encoding="utf-8"))
    actual_spec = app.openapi()

    assert actual_spec == expected_spec, "OpenAPI specification drifted! Review routes or update snapshot."


@pytest.mark.asyncio
async def test_public_slug_response_contains_no_forbidden_keys(async_client: AsyncClient, test_storage):
    """Data Minimization Invariant: Public slug portfolio view contains NONE of the forbidden keys."""
    user = User(
        id=uuid4(),
        email="student_secure@example.com",
        hashed_password="hashed_pw",
        education_level="College Junior",
        role="student",
        is_active=True,
    )
    test_storage["users"][user.id] = user

    portfolio = UserPortfolio(
        id=uuid4(),
        user_id=user.id,
        slug="safe-student-slug",
        is_public=True,
        headline="Full Stack Systems Engineer",
        about="Passionate software engineer building resilient distributed systems.",
        visibility={"about": True, "skills": True, "projects": True, "certificates": True},
        custom_projects=[{"title": "Distributed Cache", "description": "Raft-based key-value store"}],
    )
    test_storage["user_portfolios"][portfolio.id] = portfolio

    resp = await async_client.get("/v1/portfolio/p/safe-student-slug")
    assert resp.status_code == 200
    data = resp.json()

    # Recursively check for forbidden keys in JSON response
    found_forbidden = []

    def _check_keys(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                cur_path = f"{path}.{k}" if path else k
                if k.lower() in FORBIDDEN_PUBLIC_KEYS:
                    found_forbidden.append((cur_path, k, v))
                _check_keys(v, cur_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _check_keys(item, f"{path}[{i}]")

    _check_keys(data)

    assert not found_forbidden, f"Data Exposure! Found forbidden keys in public portfolio: {found_forbidden}"


@pytest.mark.asyncio
async def test_deleted_public_user_id_portfolio_returns_404_or_405(async_client: AsyncClient):
    """Verifies that GET /v1/portfolio/public/{user_id} was deleted and returns 404/405."""
    random_uuid = str(uuid4())
    resp = await async_client.get(f"/v1/portfolio/public/{random_uuid}")
    # Endpoint should not exist
    assert resp.status_code in (404, 405)
