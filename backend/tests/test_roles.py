"""
Tests untuk /api/v1/roles endpoints.

list_response → { "data": { "items": [...], "total": N } }
(bukan paginated, jadi total ada di data bukan meta)

Fixtures dari conftest:
  - client_with_db     : AsyncClient + real DB + tst_admin / tst_user seeded
  - auth_headers_admin : Bearer token tst_admin (semua permission)
  - auth_headers_user  : Bearer token tst_user (hanya user.login)
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/roles"

# Nama role yang dipakai khusus di test ini — diawali tst_ agar mudah diidentifikasi
_ROLE_NAME = "tst_role_crud"


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _create_test_role(
    client: AsyncClient,
    headers: dict,
    name: str = _ROLE_NAME,
    description: str = "Role untuk keperluan testing",
    permission_ids: list[int] | None = None,
) -> int:
    """Membuat role baru dan mengembalikan id-nya.
    Jika sudah ada role dengan nama yang sama (sisa run gagal sebelumnya),
    hapus dulu lalu buat ulang.
    """
    # Pre-cleanup: cari role dengan nama ini, hapus jika masih ada
    list_resp = await client.get(BASE, headers=headers)
    if list_resp.status_code == 200:
        for r in list_resp.json()["data"]["items"]:
            if r["name"] == name:
                await client.delete(f"{BASE}/{r['id']}", headers=headers)
                break

    payload: dict = {"name": name, "description": description}
    if permission_ids is not None:
        payload["permission_ids"] = permission_ids
    resp = await client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, f"Gagal membuat role: {resp.text}"
    return resp.json()["data"]["id"]


async def _delete_test_role(client: AsyncClient, headers: dict, role_id: int) -> None:
    """Menghapus role setelah test selesai."""
    await client.delete(f"{BASE}/{role_id}", headers=headers)


# ─────────────────────────────────────────────────────────────────────────────
# LIST  GET /api/v1/roles
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_roles_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin mendapatkan daftar role (200)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # list_response menaruh total di data, bukan meta
    assert "items" in body["data"]
    assert "total" in body["data"]
    assert isinstance(body["data"]["items"], list)
    assert body["data"]["total"] >= 2  # minimal tst_superadmin + tst_user_role


async def test_list_roles_includes_permissions(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setiap role dalam list menyertakan field permissions (list)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    for role in items:
        assert "permissions" in role
        assert isinstance(role["permissions"], list)


async def test_list_roles_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa (tanpa roles.read) mendapat 403."""
    resp = await client_with_db.get(BASE, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_list_roles_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.get(BASE)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CREATE  POST /api/v1/roles
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_role_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa membuat role baru tanpa permission (201)."""
    # Pre-cleanup jika ada sisa run sebelumnya
    lr = await client_with_db.get(BASE, headers=auth_headers_admin)
    for r in lr.json()["data"]["items"]:
        if r["name"] == _ROLE_NAME:
            await _delete_test_role(client_with_db, auth_headers_admin, r["id"])
            break

    resp = await client_with_db.post(
        BASE,
        json={"name": _ROLE_NAME, "description": "Deskripsi test"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == _ROLE_NAME
    assert "id" in data
    assert isinstance(data["permissions"], list)
    await _delete_test_role(client_with_db, auth_headers_admin, data["id"])


async def test_create_role_with_permissions(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Role dengan permission_ids yang valid tercatat di DB (verifikasi via list)."""
    # Ambil permission ids dari role tst_superadmin yang sudah seeded
    list_resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    all_roles = list_resp.json()["data"]["items"]
    superadmin = next((r for r in all_roles if r["name"] == "tst_superadmin"), None)
    perm_ids = [p["id"] for p in superadmin["permissions"][:2]] if superadmin else []

    # Buat role lewat helper — otomatis pre-cleanup jika nama sudah ada
    role_name = f"{_ROLE_NAME}_perm"
    new_id = await _create_test_role(
        client_with_db, auth_headers_admin,
        name=role_name, permission_ids=perm_ids,
    )

    try:
        # Verifikasi permission via list (eager-loaded)
        if perm_ids:
            list2 = await client_with_db.get(BASE, headers=auth_headers_admin)
            created = next(
                (r for r in list2.json()["data"]["items"] if r["id"] == new_id), None
            )
            assert created is not None
            assert len(created["permissions"]) == len(perm_ids)
    finally:
        await _delete_test_role(client_with_db, auth_headers_admin, new_id)


async def test_create_role_missing_name(
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


async def test_create_role_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa membuat role → 403."""
    resp = await client_with_db.post(
        BASE,
        json={"name": "tst_forbidden_role"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_create_role_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.post(BASE, json={"name": "tst_noauth_role"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE  PUT /api/v1/roles/{role_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_update_role_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa mengubah nama & deskripsi role (200)."""
    role_id = await _create_test_role(client_with_db, auth_headers_admin, name=f"{_ROLE_NAME}_upd")
    try:
        resp = await client_with_db.put(
            f"{BASE}/{role_id}",
            json={"name": f"{_ROLE_NAME}_upd_v2", "description": "Updated"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == f"{_ROLE_NAME}_upd_v2"
        assert data["description"] == "Updated"
    finally:
        await _delete_test_role(client_with_db, auth_headers_admin, role_id)


async def test_update_role_assign_permissions(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update role dengan permission_ids baru — verifikasi via list setelah update."""
    role_id = await _create_test_role(
        client_with_db, auth_headers_admin, name=f"{_ROLE_NAME}_perm_upd"
    )
    try:
        # Ambil satu permission id dari sistem
        list_resp = await client_with_db.get(BASE, headers=auth_headers_admin)
        superadmin = next(
            (r for r in list_resp.json()["data"]["items"] if r["name"] == "tst_superadmin"),
            None,
        )
        perm_ids = [superadmin["permissions"][0]["id"]] if superadmin and superadmin["permissions"] else []

        resp = await client_with_db.put(
            f"{BASE}/{role_id}",
            json={"permission_ids": perm_ids},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200

        if perm_ids:
            # Verifikasi via list (eager-loaded)
            list2 = await client_with_db.get(BASE, headers=auth_headers_admin)
            updated = next(
                (r for r in list2.json()["data"]["items"] if r["id"] == role_id), None
            )
            assert updated is not None
            assert any(p["id"] == perm_ids[0] for p in updated["permissions"])
    finally:
        await _delete_test_role(client_with_db, auth_headers_admin, role_id)


async def test_update_role_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update role yang tidak ada → 404."""
    resp = await client_with_db.put(
        f"{BASE}/9999999",
        json={"name": "ghost"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 404


async def test_update_role_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa mengupdate role → 403."""
    resp = await client_with_db.put(
        f"{BASE}/1",
        json={"name": "hijack"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_update_role_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.put(f"{BASE}/1", json={"name": "ghost"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  DELETE /api/v1/roles/{role_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_delete_role_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa menghapus role (200)."""
    role_id = await _create_test_role(
        client_with_db, auth_headers_admin, name=f"{_ROLE_NAME}_del"
    )
    resp = await client_with_db.delete(f"{BASE}/{role_id}", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_delete_role_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Hapus role yang tidak ada → 404."""
    resp = await client_with_db.delete(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_delete_role_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa menghapus role → 403."""
    resp = await client_with_db.delete(f"{BASE}/1", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_delete_role_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.delete(f"{BASE}/1")
    assert resp.status_code == 403


async def test_delete_role_conflict_with_users(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Menghapus role yang masih dipakai user → 409 Conflict."""
    # tst_superadmin role sudah di-assign ke tst_admin oleh conftest
    roles = await client_with_db.get(BASE, headers=auth_headers_admin)
    superadmin = next(
        (r for r in roles.json()["data"]["items"] if r["name"] == "tst_superadmin"), None
    )
    assert superadmin is not None, "Role tst_superadmin tidak ditemukan"
    resp = await client_with_db.delete(f"{BASE}/{superadmin['id']}", headers=auth_headers_admin)
    assert resp.status_code == 409
