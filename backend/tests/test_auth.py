"""
Integration tests for /api/v1/auth endpoints.
Fixtures `client_with_db` seeds test users (tst_admin / tst_user)
and hard-deletes them in teardown — real PostgreSQL, no mocking.
"""
import pytest
from httpx import AsyncClient


LOGIN_URL  = "/api/v1/auth/login"
ME_URL     = "/api/v1/auth/me"
LOGOUT_URL = "/api/v1/auth/logout"

ADMIN_CREDS = {"username": "tst_admin", "password": "Test@1234"}
USER_CREDS  = {"username": "tst_user",  "password": "Test@1234"}


# ============================================================
# Login — success paths
# ============================================================

@pytest.mark.asyncio
async def test_login_admin_success(client_with_db: AsyncClient):
    resp = await client_with_db.post(LOGIN_URL, json=ADMIN_CREDS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"
    assert data["data"]["username"] == "tst_admin"
    assert isinstance(data["data"]["permissions"], list)
    assert len(data["data"]["permissions"]) > 0
    assert "menu_guard" in data["data"]


@pytest.mark.asyncio
async def test_login_user_success(client_with_db: AsyncClient):
    resp = await client_with_db.post(LOGIN_URL, json=USER_CREDS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["username"] == "tst_user"
    assert isinstance(data["data"]["roles"], list)


@pytest.mark.asyncio
async def test_login_returns_expires_in(client_with_db: AsyncClient):
    resp = await client_with_db.post(LOGIN_URL, json=ADMIN_CREDS)
    assert resp.status_code == 200
    assert "expires_in" in resp.json()["data"]
    assert isinstance(resp.json()["data"]["expires_in"], int)


# ============================================================
# Login — failure paths
# ============================================================

@pytest.mark.asyncio
async def test_login_wrong_password(client_with_db: AsyncClient):
    resp = await client_with_db.post(
        LOGIN_URL, json={"username": "tst_admin", "password": "WrongPass!"}
    )
    assert resp.status_code == 401
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_login_nonexistent_user(client_with_db: AsyncClient):
    resp = await client_with_db.post(
        LOGIN_URL, json={"username": "ghost_xyz", "password": "Test@1234"}
    )
    assert resp.status_code == 401
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_login_missing_username(client: AsyncClient):
    resp = await client.post(LOGIN_URL, json={"password": "Test@1234"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_password(client: AsyncClient):
    resp = await client.post(LOGIN_URL, json={"username": "tst_admin"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_empty_body(client: AsyncClient):
    resp = await client.post(LOGIN_URL, json={})
    assert resp.status_code == 422


# ============================================================
# /auth/me — protected endpoint
# ============================================================

@pytest.mark.asyncio
async def test_me_with_valid_token(client_with_db: AsyncClient):
    login = await client_with_db.post(LOGIN_URL, json=ADMIN_CREDS)
    token = login.json()["data"]["access_token"]

    resp = await client_with_db.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["username"] == "tst_admin"
    assert "roles" in data["data"]
    assert "permissions" in data["data"]


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    resp = await client.get(ME_URL)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    resp = await client.get(
        ME_URL, headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code in (401, 403)


# ============================================================
# /auth/logout
# ============================================================

@pytest.mark.asyncio
async def test_logout_success(client_with_db: AsyncClient):
    login = await client_with_db.post(LOGIN_URL, json=ADMIN_CREDS)
    token = login.json()["data"]["access_token"]

    resp = await client_with_db.post(
        LOGOUT_URL, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_logout_without_token(client: AsyncClient):
    resp = await client.post(LOGOUT_URL)
    assert resp.status_code in (401, 403)

