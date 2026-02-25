"""
Tests for /api/v1/users endpoints.

Fixtures dari conftest:
  - client_with_db  : AsyncClient + real DB + tst_admin / tst_user sudah diseed
  - auth_headers_admin : Bearer token untuk tst_admin (punya semua permission)
  - auth_headers_user  : Bearer token untuk tst_user (hanya user.login)
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/users"

_NEW_USER = {
    "username": "tst_new_user",
    "password": "NewUser@9999",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _get_tst_admin_id(client: AsyncClient, headers: dict) -> int:
    """Ambil id tst_admin dari endpoint list."""
    resp = await client.get(BASE, params={"limit": 100}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    match = [u for u in items if u["username"] == "tst_admin"]
    assert match, "tst_admin tidak ditemukan di list users"
    return match[0]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# LIST  GET /api/v1/users
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_users_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin mendapatkan daftar user (200)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # struktur paginated — items ada di data, meta ada di meta
    assert "items" in body["data"]
    assert "meta" in body
    assert "total" in body["meta"]
    assert isinstance(body["data"]["items"], list)
    assert body["meta"]["total"] >= 2  # minimal tst_admin + tst_user


async def test_list_users_pagination(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Parameter page & limit bekerja dengan benar."""
    resp = await client_with_db.get(BASE, params={"page": 1, "limit": 1}, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]["items"]) == 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 1


async def test_list_users_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa (tanpa users.read) mendapat 403."""
    resp = await client_with_db.get(BASE, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_list_users_no_auth(client_with_db: AsyncClient):
    """Tanpa token mendapat 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.get(BASE)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DETAIL  GET /api/v1/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_get_user_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa melihat detail user (200)."""
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)

    resp = await client_with_db.get(f"{BASE}/{user_id}", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == user_id
    assert data["username"] == "tst_admin"
    assert "roles" in data
    assert "permissions" in data
    assert isinstance(data["roles"], list)
    assert isinstance(data["permissions"], list)


async def test_get_user_includes_roles_and_permissions(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Detail user menyertakan daftar role dan permission."""
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)
    resp = await client_with_db.get(f"{BASE}/{user_id}", headers=auth_headers_admin)
    data = resp.json()["data"]
    # tst_admin punya tst_superadmin role yang punya semua permission
    assert len(data["roles"]) >= 1
    assert len(data["permissions"]) >= 1


async def test_get_user_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """User ID yang tidak ada → 404."""
    resp = await client_with_db.get(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_get_user_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa melihat detail user → 403."""
    resp = await client_with_db.get(f"{BASE}/1", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_get_user_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.get(f"{BASE}/1")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CREATE  POST /api/v1/users
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_user_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa membuat user baru (201)."""
    resp = await client_with_db.post(BASE, json=_NEW_USER, headers=auth_headers_admin)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["username"] == _NEW_USER["username"]
    assert "id" in data
    # cleanup — force=true untuk benar-benar menghapus dari DB
    await client_with_db.delete(f"{BASE}/{data['id']}", params={"force": "true"}, headers=auth_headers_admin)


async def test_create_user_missing_username(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Username wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE, json={"password": "Pass@1234"}, headers=auth_headers_admin
    )
    assert resp.status_code == 422


async def test_create_user_missing_password(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Password wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE, json={"username": "tst_nopass"}, headers=auth_headers_admin
    )
    assert resp.status_code == 422


async def test_create_user_with_role(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Membuat user dengan role_ids yang valid (201)."""
    # Ambil id role yang ada dari list user (tst_admin punya tst_superadmin)
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)
    detail = await client_with_db.get(f"{BASE}/{user_id}", headers=auth_headers_admin)
    # Buat user baru dulu tanpa role
    resp = await client_with_db.post(
        BASE,
        json={"username": "tst_withrole", "password": "Role@1234", "role_ids": []},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 201
    new_id = resp.json()["data"]["id"]
    # cleanup — force=true untuk benar-benar menghapus dari DB
    await client_with_db.delete(f"{BASE}/{new_id}", params={"force": "true"}, headers=auth_headers_admin)


async def test_create_user_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa membuat user baru → 403."""
    resp = await client_with_db.post(BASE, json=_NEW_USER, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_create_user_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.post(BASE, json=_NEW_USER)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE  PUT /api/v1/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_update_user_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa mengupdate user (200)."""
    # Buat user baru untuk diupdate agar tidak merusak fixture user
    create = await client_with_db.post(
        BASE,
        json={"username": "tst_update_target", "password": "Upd@1234"},
        headers=auth_headers_admin,
    )
    assert create.status_code == 201
    uid = create.json()["data"]["id"]

    try:
        resp = await client_with_db.put(
            f"{BASE}/{uid}",
            json={"username": "tst_update_target_v2"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "tst_update_target_v2"
    finally:
        await client_with_db.delete(f"{BASE}/{uid}", params={"force": "true"}, headers=auth_headers_admin)


async def test_update_user_deactivate(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa menonaktifkan user dengan is_active=False."""
    create = await client_with_db.post(
        BASE,
        json={"username": "tst_deactivate", "password": "Deact@1234"},
        headers=auth_headers_admin,
    )
    assert create.status_code == 201
    uid = create.json()["data"]["id"]

    try:
        resp = await client_with_db.put(
            f"{BASE}/{uid}",
            json={"is_active": False},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
    finally:
        await client_with_db.delete(f"{BASE}/{uid}", params={"force": "true"}, headers=auth_headers_admin)


async def test_update_user_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update user yang tidak ada → 404."""
    resp = await client_with_db.put(
        f"{BASE}/9999999", json={"username": "ghost"}, headers=auth_headers_admin
    )
    assert resp.status_code == 404


async def test_update_user_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
    auth_headers_admin: dict,
):
    """User biasa tidak bisa mengupdate user → 403."""
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)
    resp = await client_with_db.put(
        f"{BASE}/{user_id}",
        json={"username": "should_fail"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_update_user_no_auth(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)
    resp = await client_with_db.put(f"{BASE}/{user_id}", json={"username": "ghost"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  DELETE /api/v1/users/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_delete_user_soft_default(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE tanpa force → soft delete: is_active=False, user masih ada (200)."""
    create = await client_with_db.post(
        BASE,
        json={"username": "tst_soft_del", "password": "Del@1234"},
        headers=auth_headers_admin,
    )
    assert create.status_code == 201
    uid = create.json()["data"]["id"]

    try:
        resp = await client_with_db.delete(f"{BASE}/{uid}", headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # Verifikasi: user masih ada tapi is_active=False
        detail = await client_with_db.get(f"{BASE}/{uid}", headers=auth_headers_admin)
        assert detail.status_code == 200
        assert detail.json()["data"]["is_active"] is False
    finally:
        await client_with_db.delete(f"{BASE}/{uid}", params={"force": "true"}, headers=auth_headers_admin)


async def test_delete_user_hard_force(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE ?force=true → hard delete: user benar-benar dihapus dari DB (200)."""
    create = await client_with_db.post(
        BASE,
        json={"username": "tst_hard_del", "password": "Del@1234"},
        headers=auth_headers_admin,
    )
    assert create.status_code == 201
    uid = create.json()["data"]["id"]

    resp = await client_with_db.delete(f"{BASE}/{uid}", params={"force": "true"}, headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verifikasi: user sudah tidak ada
    detail = await client_with_db.get(f"{BASE}/{uid}", headers=auth_headers_admin)
    assert detail.status_code == 404


async def test_delete_user_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Hapus user yang tidak ada → 404."""
    resp = await client_with_db.delete(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_delete_user_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
    auth_headers_admin: dict,
):
    """User biasa tidak bisa menghapus user → 403."""
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)
    resp = await client_with_db.delete(f"{BASE}/{user_id}", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_delete_user_no_auth(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    user_id = await _get_tst_admin_id(client_with_db, auth_headers_admin)
    resp = await client_with_db.delete(f"{BASE}/{user_id}")
    assert resp.status_code == 403
