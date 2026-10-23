import base64
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_signup_success(async_client: AsyncClient):
    payload = {
        "email": "Student.One@Example.com",
        "password": "SecurePassword123!",
        "education_level": "class_11_12",
    }
    response = await async_client.post("/v1/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student.one@example.com"
    assert data["role"] == "student"  # Strictly defaulted to student
    assert data["education_level"] == "class_11_12"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_signup_role_in_body_rejected(async_client: AsyncClient):
    payload = {
        "email": "hacker@example.com",
        "password": "SecurePassword123!",
        "education_level": "college",
        "role": "admin",  # Must be rejected by extra="forbid"
    }
    response = await async_client.post("/v1/auth/signup", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_signup_short_password_rejected(async_client: AsyncClient):
    payload = {
        "email": "short@example.com",
        "password": "short",  # < 10 chars
        "education_level": "college",
    }
    response = await async_client.post("/v1/auth/signup", json=payload)
    assert response.status_code == 422
    assert "at least 10 characters" in response.text


@pytest.mark.asyncio
async def test_signup_too_long_password_rejected(async_client: AsyncClient):
    payload = {
        "email": "long@example.com",
        "password": "A" * 75,  # > 72 bytes
        "education_level": "college",
    }
    response = await async_client.post("/v1/auth/signup", json=payload)
    assert response.status_code == 422
    assert "72 bytes" in response.text


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(async_client: AsyncClient):
    payload = {
        "email": "dupe@example.com",
        "password": "ValidPassword123!",
        "education_level": "college",
    }
    # First registration
    res1 = await async_client.post("/v1/auth/signup", json=payload)
    assert res1.status_code == 201

    # Second registration with same email (case-insensitive)
    payload["email"] = "DUPE@example.com"
    res2 = await async_client.post("/v1/auth/signup", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    # Register
    signup_payload = {
        "email": "login_user@example.com",
        "password": "LoginPassword123!",
        "education_level": "college",
    }
    await async_client.post("/v1/auth/signup", json=signup_payload)

    # Login
    login_payload = {
        "email": "LOGIN_USER@example.com",
        "password": "LoginPassword123!",
    }
    response = await async_client.post("/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900  # 15 mins


@pytest.mark.asyncio
async def test_login_unknown_email_and_wrong_password_return_identical_error(async_client: AsyncClient):
    # 1. Non-existent email
    res1 = await async_client.post(
        "/v1/auth/login",
        json={"email": "non_existent@example.com", "password": "Password12345!"},
    )
    assert res1.status_code == 401
    err1 = res1.json()["error"]
    assert err1["code"] == "INVALID_CREDENTIALS"
    assert err1["message"] == "Invalid email or password."

    # 2. Existing user with wrong password
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "real_user@example.com", "password": "CorrectPassword123!", "education_level": "college"},
    )
    res2 = await async_client.post(
        "/v1/auth/login",
        json={"email": "real_user@example.com", "password": "WrongPassword999!"},
    )
    assert res2.status_code == 401
    err2 = res2.json()["error"]
    assert err2["code"] == "INVALID_CREDENTIALS"
    assert err2["message"] == "Invalid email or password."
    # Both errors must be completely identical
    assert err1["message"] == err2["message"]


@pytest.mark.asyncio
async def test_refresh_token_rotation_success(async_client: AsyncClient):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "refresh_user@example.com", "password": "RefreshPass123!", "education_level": "class_11_12"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "refresh_user@example.com", "password": "RefreshPass123!"},
    )
    t1_refresh = login_res.json()["refresh_token"]

    # First rotation
    rotate_res1 = await async_client.post("/v1/auth/refresh", json={"refresh_token": t1_refresh})
    assert rotate_res1.status_code == 200
    t2_refresh = rotate_res1.json()["refresh_token"]
    assert t2_refresh != t1_refresh  # Must be rotated

    # Second rotation with the new token
    rotate_res2 = await async_client.post("/v1/auth/refresh", json={"refresh_token": t2_refresh})
    assert rotate_res2.status_code == 200
    t3_refresh = rotate_res2.json()["refresh_token"]
    assert t3_refresh != t2_refresh


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection_revokes_family(async_client: AsyncClient):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "reuse_user@example.com", "password": "ReusePass123!", "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "reuse_user@example.com", "password": "ReusePass123!"},
    )
    t1_refresh = login_res.json()["refresh_token"]

    # Legitimate rotation -> consumes t1, produces t2
    rotate_res = await async_client.post("/v1/auth/refresh", json={"refresh_token": t1_refresh})
    assert rotate_res.status_code == 200
    t2_refresh = rotate_res.json()["refresh_token"]

    # MALICIOUS REUSE ATTEMPT: Attacker presents already-used t1_refresh
    malicious_res = await async_client.post("/v1/auth/refresh", json={"refresh_token": t1_refresh})
    assert malicious_res.status_code == 401
    assert malicious_res.json()["error"]["code"] == "REFRESH_TOKEN_REUSE_DETECTED"

    # Consequence: Entire family is revoked. Even legitimate t2_refresh is now rejected
    legit_aftermath = await async_client.post("/v1/auth/refresh", json={"refresh_token": t2_refresh})
    assert legit_aftermath.status_code == 401
    assert legit_aftermath.json()["error"]["code"] == "REFRESH_TOKEN_REUSE_DETECTED"


@pytest.mark.asyncio
async def test_expired_refresh_token_rejected(async_client: AsyncClient, test_storage):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "expired_user@example.com", "password": "ExpiredPass123!", "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "expired_user@example.com", "password": "ExpiredPass123!"},
    )
    t_refresh = login_res.json()["refresh_token"]

    # Artificially expire the token in test storage
    for token in test_storage["tokens"].values():
        token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    res = await async_client.post("/v1/auth/refresh", json={"refresh_token": t_refresh})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "REFRESH_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_refresh_token_used_as_access_token_rejected(async_client: AsyncClient):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "bearer_check@example.com", "password": "Password12345!", "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "bearer_check@example.com", "password": "Password12345!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Attempt to access protected endpoint using refresh token
    res = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_tampered_access_token_rejected(async_client: AsyncClient):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "tamper@example.com", "password": "Password12345!", "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "tamper@example.com", "password": "Password12345!"},
    )
    valid_token = login_res.json()["access_token"]

    # Tamper with the token payload/signature
    tampered = valid_token[:-4] + "WXYZ"
    res = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_algorithm_none_rejected(async_client: AsyncClient):
    # Construct an unsigned token with alg="none"
    header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
    now = int(datetime.now(timezone.utc).timestamp())
    payload = base64.urlsafe_b64encode(
        json.dumps({
            "sub": str(uuid4()),
            "email": "hacker@none.com",
            "role": "admin",
            "type": "access",
            "iat": now,
            "exp": now + 900,
        }).encode()
    ).decode().rstrip("=")

    alg_none_token = f"{header}.{payload}."

    res = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {alg_none_token}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


@pytest.mark.asyncio
async def test_password_change_revokes_sessions(async_client: AsyncClient):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "pw_change@example.com", "password": "OldPassword123!", "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "pw_change@example.com", "password": "OldPassword123!"},
    )
    access_token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    # Change password
    change_res = await async_client.post(
        "/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "OldPassword123!", "new_password": "NewPassword123!"},
    )
    assert change_res.status_code == 200

    # Old refresh token is now revoked
    refresh_after = await async_client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after.status_code == 401

    # Login with old password fails
    login_old = await async_client.post(
        "/v1/auth/login",
        json={"email": "pw_change@example.com", "password": "OldPassword123!"},
    )
    assert login_old.status_code == 401

    # Login with new password succeeds
    login_new = await async_client.post(
        "/v1/auth/login",
        json={"email": "pw_change@example.com", "password": "NewPassword123!"},
    )
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_get_current_user_me_endpoint(async_client: AsyncClient):
    # Signup & Login
    await async_client.post(
        "/v1/auth/signup",
        json={"email": "me_user@example.com", "password": "MePassword123!", "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": "me_user@example.com", "password": "MePassword123!"},
    )
    token = login_res.json()["access_token"]

    res = await async_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me_user@example.com"
    assert data["role"] == "student"
    assert data["education_level"] == "college"


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(async_client: AsyncClient, test_storage):
    # 1. Signup user
    email = "reset_test@example.com"
    old_pw = "OriginalPass123!"
    await async_client.post(
        "/v1/auth/signup",
        json={"email": email, "password": old_pw, "education_level": "college"},
    )
    login_res = await async_client.post(
        "/v1/auth/login",
        json={"email": email, "password": old_pw},
    )
    old_refresh = login_res.json()["refresh_token"]

    # 2. Forgot password request (returns identical message for any email)
    res_unknown = await async_client.post(
        "/v1/auth/forgot-password",
        json={"email": "nonexistent_email@example.com"},
    )
    assert res_unknown.status_code == 200
    assert "instructions have been sent" in res_unknown.json()["message"]

    res_known = await async_client.post(
        "/v1/auth/forgot-password",
        json={"email": email},
    )
    assert res_known.status_code == 200
    assert "instructions have been sent" in res_known.json()["message"]

    from app.core.security import hash_token
    from app.services.auth_service import AuthService

    # First test invalid token:
    invalid_res = await async_client.post(
        "/v1/auth/reset-password",
        json={"token": "invalid_token_1234567890", "new_password": "NewSecretPass123!"},
    )
    assert invalid_res.status_code == 400

    # Test extra='forbid' on reset-password
    extra_res = await async_client.post(
        "/v1/auth/reset-password",
        json={"token": "invalid_token_1234567890", "new_password": "NewSecretPass123!", "hacked": True},
    )
    assert extra_res.status_code == 422

    # 5. Successfully reset with valid token
    valid_raw_token = "valid_reset_token_secret_12345"
    token_hash = hash_token(valid_raw_token)
    user_rec = next(u for u in test_storage["users"].values() if u.email == email)
    
    # Store token in test_storage / mock token repo
    auth_srv = AuthService(None)
    await auth_srv.token_repo.create_password_reset_token(
        user_id=user_rec.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )

    reset_res = await async_client.post(
        "/v1/auth/reset-password",
        json={"token": valid_raw_token, "new_password": "NewSecretPass123!"},
    )
    assert reset_res.status_code == 200
    assert "successfully reset" in reset_res.json()["message"]

    # Reusing the same reset token is rejected
    reuse_res = await async_client.post(
        "/v1/auth/reset-password",
        json={"token": valid_raw_token, "new_password": "AnotherSecret123!"},
    )
    assert reuse_res.status_code == 400

    # Old refresh token is revoked
    refresh_after = await async_client.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_after.status_code == 401

    # Old password no longer works
    login_old = await async_client.post(
        "/v1/auth/login",
        json={"email": email, "password": old_pw},
    )
    assert login_old.status_code == 401

    # New password works
    login_new = await async_client.post(
        "/v1/auth/login",
        json={"email": email, "password": "NewSecretPass123!"},
    )
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_auth_rate_limiting(async_client: AsyncClient):
    """Verify progressive rate limiting on forgot password endpoint."""
    from app.core.rate_limit import reset_rate_limits
    reset_rate_limits()

    rate_limit_email = "ratelimit_target@example.com"
    for _ in range(5):
        resp = await async_client.post(
            "/v1/auth/forgot-password",
            json={"email": rate_limit_email},
        )
        assert resp.status_code == 200

    # 6th request must exceed rate limit
    exceeded = await async_client.post(
        "/v1/auth/forgot-password",
        json={"email": rate_limit_email},
    )
    assert exceeded.status_code == 429
    assert exceeded.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


