import pytest


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_halo(client):
    resp = await client.get("/api/v1/halo")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_login_invalid(client):
    resp = await client.post("/api/v1/auth/login", json={"username": "wrong", "password": "wrong"})
    assert resp.status_code == 401
