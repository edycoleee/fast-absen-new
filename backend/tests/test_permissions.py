"""
Tests untuk /api/v1/permissions endpoints.

Endpoint yang tersedia:
  GET    /permissions          → list_response (data.items, data.total)
  GET    /permissions/registry → success_response (data.items)
  POST   /permissions          → create (201)
  DELETE /permissions/{id}     → delete (200)
  (tidak ada PUT/UPDATE)

Fixtures dari conftest:
  - client_with_db     : AsyncClient + real DB + tst_admin / tst_user seeded
  - auth_headers_admin : Bearer token tst_admin (semua permission)
  - auth_headers_user  : Bearer token tst_user (hanya user.login)
"""
from httpx import AsyncClient

BASE = "/api/v1/permissions"

_PERM_NAME = "tst.permission.crud"


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _create_test_perm(
    client: AsyncClient,
    headers: dict,
    name: str = _PERM_NAME,
    description: str = "Permission untuk testing",
) -> int:
    """Membuat permission baru, pre-cleanup jika nama sudah ada."""
    # Pre-cleanup: hapus jika masih ada dari run sebelumnya
    list_resp = await client.get(BASE, headers=headers)
    if list_resp.status_code == 200:
        for p in list_resp.json()["data"]["items"]:
            if p["name"] == name:
                await client.delete(f"{BASE}/{p['id']}", headers=headers)
                break

    resp = await client.post(
        BASE,
        json={"name": name, "description": description},
        headers=headers,
    )
    assert resp.status_code == 201, f"Gagal membuat permission: {resp.text}"
    return resp.json()["data"]["id"]


async def _delete_test_perm(client: AsyncClient, headers: dict, perm_id: int) -> None:
    await client.delete(f"{BASE}/{perm_id}", headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# LIST  GET /api/v1/permissions
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_permissions_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin mendapatkan daftar permission (200)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # list_response: total ada di data
    assert "items" in body["data"]
    assert "total" in body["data"]
    assert isinstance(body["data"]["items"], list)
    assert body["data"]["total"] > 0


async def test_list_permissions_item_fields(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setiap item memiliki field id, name, description."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) > 0
    for item in items[:3]:  # cek 3 pertama sudah cukup
        assert "id" in item
        assert "name" in item
        assert "description" in item


async def test_list_permissions_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa (tanpa permissions.read) mendapat 403."""
    resp = await client_with_db.get(BASE, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_list_permissions_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.get(BASE)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY  GET /api/v1/permissions/registry
# ─────────────────────────────────────────────────────────────────────────────

async def test_get_registry_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Registry mengembalikan daftar semua permission yang terdaftar di kode (200)."""
    resp = await client_with_db.get(f"{BASE}/registry", headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert isinstance(body["data"]["items"], list)
    assert len(body["data"]["items"]) > 0


async def test_get_registry_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa akses registry → 403."""
    resp = await client_with_db.get(f"{BASE}/registry", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_get_registry_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(f"{BASE}/registry")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CREATE  POST /api/v1/permissions
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_permission_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa membuat permission baru (201)."""
    perm_id = await _create_test_perm(client_with_db, auth_headers_admin)
    try:
        # Verifikasi muncul di list
        list_resp = await client_with_db.get(BASE, headers=auth_headers_admin)
        names = [p["name"] for p in list_resp.json()["data"]["items"]]
        assert _PERM_NAME in names
    finally:
        await _delete_test_perm(client_with_db, auth_headers_admin, perm_id)


async def test_create_permission_response_fields(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Response create menyertakan id dan name."""
    name = f"{_PERM_NAME}.fields"
    # pre-cleanup
    lr = await client_with_db.get(BASE, headers=auth_headers_admin)
    for p in lr.json()["data"]["items"]:
        if p["name"] == name:
            await _delete_test_perm(client_with_db, auth_headers_admin, p["id"])
            break

    resp = await client_with_db.post(
        BASE, json={"name": name, "description": "Cek field"}, headers=auth_headers_admin
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "id" in data
    assert data["name"] == name
    await _delete_test_perm(client_with_db, auth_headers_admin, data["id"])


async def test_create_permission_missing_name(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """name wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE,
        json={"description": "Tanpa nama"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 422


async def test_create_permission_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa membuat permission → 403."""
    resp = await client_with_db.post(
        BASE,
        json={"name": "tst.forbidden.perm"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_create_permission_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.post(BASE, json={"name": "tst.noauth.perm"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  DELETE /api/v1/permissions/{perm_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_delete_permission_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa menghapus permission (200)."""
    perm_id = await _create_test_perm(
        client_with_db, auth_headers_admin, name=f"{_PERM_NAME}.del"
    )
    resp = await client_with_db.delete(f"{BASE}/{perm_id}", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verifikasi tidak muncul lagi di list
    list_resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    ids = [p["id"] for p in list_resp.json()["data"]["items"]]
    assert perm_id not in ids


async def test_delete_permission_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Hapus permission yang tidak ada → 404."""
    resp = await client_with_db.delete(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_delete_permission_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa menghapus permission → 403."""
    resp = await client_with_db.delete(f"{BASE}/1", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_delete_permission_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.delete(f"{BASE}/1")
    assert resp.status_code == 403


async def test_delete_permission_conflict_with_roles(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Menghapus permission yang masih digunakan role → 409 Conflict."""
    # Ambil permission yang dipakai oleh tst_superadmin
    roles_resp = await client_with_db.get("/api/v1/roles", headers=auth_headers_admin)
    superadmin = next(
        (r for r in roles_resp.json()["data"]["items"] if r["name"] == "tst_superadmin"), None
    )
    assert superadmin is not None and superadmin["permissions"], "tst_superadmin harus punya permission"
    perm_id = superadmin["permissions"][0]["id"]
    resp = await client_with_db.delete(f"{BASE}/{perm_id}", headers=auth_headers_admin)
    assert resp.status_code == 409
