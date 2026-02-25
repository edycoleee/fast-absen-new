"""
Tests untuk /api/v1/unit endpoints.

Endpoint yang tersedia:
  GET    /unit                     → paginated (meta.page, meta.limit, meta.total)
  POST   /unit                     → create (201), id_unit wajib (integer manual)
  PUT    /unit/{id_unit}           → update (200)
  DELETE /unit/{id_unit}           → soft delete default (status = 'INACTIVE')
  DELETE /unit/{id_unit}?force=true → hard delete permanen (hanya jika tidak ada pegawai)

Catatan: id_unit bukan auto-increment, harus disuplai saat create.
Gunakan id range 99000-an untuk test agar tidak bentrok dengan data produksi.

Fade dari list setelah soft delete: GET /unit hanya menampilkan status 'ACTIVE'.

Fixtures dari conftest:
  - client_with_db     : AsyncClient + real DB + tst_admin / tst_user seeded
  - auth_headers_admin : Bearer token tst_admin (semua permission)
  - auth_headers_user  : Bearer token tst_user (hanya user.login)
"""
from httpx import AsyncClient

BASE = "/api/v1/unit"

# Gunakan id & nama yang unik, jauh dari range data nyata
_TEST_UNIT = {"id_unit": 99001, "nama_unit": "TST_Unit_CRUD"}
_TEST_UNIT_2 = {"id_unit": 99002, "nama_unit": "TST_Unit_Extra"}


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_deleted(client: AsyncClient, headers: dict, id_unit: int) -> None:
    """Hard-delete unit agar test cleanup benar-benar bersih.
    Pakai ?force=true sehingga record benar-benar hilang dari DB.
    Abaikan semua error (404 = sudah bersih).
    """
    await client.delete(f"{BASE}/{id_unit}?force=true", headers=headers)


async def _create_test_unit(
    client: AsyncClient,
    headers: dict,
    payload: dict = None,
) -> dict:
    """Buat unit test, pre-cleanup dulu. Kembalikan data response."""
    if payload is None:
        payload = _TEST_UNIT
    await _ensure_deleted(client, headers, payload["id_unit"])
    resp = await client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, f"Gagal membuat unit: {resp.text}"
    return resp.json()["data"]


# ─────────────────────────────────────────────────────────────────────────────
# LIST  GET /api/v1/unit
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_units_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin mendapatkan daftar unit (200)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # paginated_response → items di data, page/limit/total di meta
    assert "items" in body["data"]
    assert "meta" in body
    assert "total" in body["meta"]
    assert isinstance(body["data"]["items"], list)


async def test_list_units_pagination(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Parameter page & limit bekerja dengan benar."""
    resp = await client_with_db.get(BASE, params={"page": 1, "limit": 1}, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]["items"]) <= 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 1


async def test_list_units_item_fields(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setiap item memiliki field id_unit, nama_unit, status."""
    # Pastikan minimal ada satu unit
    await _create_test_unit(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.get(BASE, params={"limit": 50}, headers=auth_headers_admin)
        items = resp.json()["data"]["items"]
        assert len(items) > 0
        for item in items[:3]:
            assert "id_unit" in item
            assert "nama_unit" in item
            assert "is_active" in item
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_UNIT["id_unit"])


async def test_list_units_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa (tanpa unit.read) mendapat 403."""
    resp = await client_with_db.get(BASE, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_list_units_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403 (HTTPBearer auto_error)."""
    resp = await client_with_db.get(BASE)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CREATE  POST /api/v1/unit
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_unit_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa membuat unit baru (201)."""
    data = await _create_test_unit(client_with_db, auth_headers_admin)
    try:
        assert data["id_unit"] == _TEST_UNIT["id_unit"]
        assert data["nama_unit"] == _TEST_UNIT["nama_unit"]
        assert data["is_active"] == True
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_UNIT["id_unit"])


async def test_create_unit_default_status(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Status default 'ACTIVE' jika tidak disuplai."""
    payload = {"id_unit": 99003, "nama_unit": "TST_Unit_DefStatus"}
    await _ensure_deleted(client_with_db, auth_headers_admin, 99003)
    try:
        resp = await client_with_db.post(BASE, json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["data"]["is_active"] == True
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, 99003)


async def test_create_unit_missing_id_unit(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """id_unit wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE,
        json={"nama_unit": "TST_No_Id"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 422


async def test_create_unit_missing_nama(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """nama_unit wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE,
        json={"id_unit": 99004},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 422


async def test_create_unit_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa membuat unit → 403."""
    resp = await client_with_db.post(BASE, json=_TEST_UNIT, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_create_unit_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.post(BASE, json=_TEST_UNIT)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE  PUT /api/v1/unit/{id_unit}
# ─────────────────────────────────────────────────────────────────────────────

async def test_update_unit_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa mengubah nama dan status unit (200)."""
    await _create_test_unit(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.put(
            f"{BASE}/{_TEST_UNIT['id_unit']}",
            json={"nama_unit": "TST_Unit_CRUD_Updated", "is_active": False},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["nama_unit"] == "TST_Unit_CRUD_Updated"
        assert data["is_active"] == False
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_UNIT["id_unit"])


async def test_update_unit_partial(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update hanya satu field (status) tanpa menyertakan nama_unit."""
    await _create_test_unit(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.put(
            f"{BASE}/{_TEST_UNIT['id_unit']}",
            json={"is_active": False},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] == False
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_UNIT["id_unit"])


async def test_update_unit_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update unit yang tidak ada → 404."""
    resp = await client_with_db.put(
        f"{BASE}/9999999",
        json={"nama_unit": "Ghost"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 404


async def test_update_unit_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa mengupdate unit → 403."""
    resp = await client_with_db.put(
        f"{BASE}/1",
        json={"nama_unit": "Hijack"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_update_unit_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.put(f"{BASE}/1", json={"nama_unit": "Ghost"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  DELETE /api/v1/unit/{id_unit}  &  DELETE /api/v1/unit/{id_unit}?force=true
# ─────────────────────────────────────────────────────────────────────────────

async def test_delete_unit_soft_default(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE tanpa ?force → soft delete: unit tidak muncul di list (200)."""
    await _create_test_unit(client_with_db, auth_headers_admin, payload=_TEST_UNIT_2)
    try:
        resp = await client_with_db.delete(
            f"{BASE}/{_TEST_UNIT_2['id_unit']}", headers=auth_headers_admin
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # Pesan menyebut 'nonaktifkan', bukan 'dihapus'
        assert "nonaktif" in resp.json()["message"].lower()

        # Unit tidak lagi muncul di list (filter 'ACTIVE')
        list_resp = await client_with_db.get(BASE, params={"limit": 100}, headers=auth_headers_admin)
        ids = [u["id_unit"] for u in list_resp.json()["data"]["items"]]
        assert _TEST_UNIT_2["id_unit"] not in ids
    finally:
        # Cleanup: hard delete agar tidak meninggalkan data 'INACTIVE'
        await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_UNIT_2["id_unit"])


async def test_delete_unit_hard_force(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE ?force=true → hard delete: unit benar-benar hilang dari DB (200)."""
    await _create_test_unit(client_with_db, auth_headers_admin, payload=_TEST_UNIT_2)

    resp = await client_with_db.delete(
        f"{BASE}/{_TEST_UNIT_2['id_unit']}?force=true", headers=auth_headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Unit benar-benar hilang: hard delete lagi → 404
    verify = await client_with_db.delete(
        f"{BASE}/{_TEST_UNIT_2['id_unit']}?force=true", headers=auth_headers_admin
    )
    assert verify.status_code == 404


async def test_delete_unit_hard_conflict_with_pegawai(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """
    Hard delete ditolak (409) jika masih ada pegawai terhubung.
    Skenario: buat unit, tautkan ke pegawai fixture, coba force delete.

    Cleanup: pindahkan pegawai ke unit spare → force-delete unit utama,
    lalu soft-delete unit spare (hard delete-nya dilakukan _ensure_deleted
    di awal test run berikutnya, setelah conftest sudah bersihkan pegawai).
    """
    _UNIT_LINKED = {"id_unit": 99010, "nama_unit": "TST_Unit_Linked"}
    _UNIT_SPARE  = {"id_unit": 99011, "nama_unit": "TST_Unit_Spare"}

    # Pre-cleanup: hapus sisa run sebelumnya (conftest sudah hapus pegawai
    # sehingga count_pegawai=0 dan force=true aman)
    await _ensure_deleted(client_with_db, auth_headers_admin, _UNIT_LINKED["id_unit"])
    await _ensure_deleted(client_with_db, auth_headers_admin, _UNIT_SPARE["id_unit"])

    try:
        # Buat kedua unit
        r1 = await client_with_db.post(BASE, json=_UNIT_LINKED, headers=auth_headers_admin)
        assert r1.status_code == 201
        r2 = await client_with_db.post(BASE, json=_UNIT_SPARE, headers=auth_headers_admin)
        assert r2.status_code == 201

        # Tautkan pegawai fixture ke unit yang akan dihapus
        link = await client_with_db.put(
            "/api/v1/pegawai/TST_PGW_A",
            json={"id_unit": _UNIT_LINKED["id_unit"]},
            headers=auth_headers_admin,
        )
        assert link.status_code == 200, f"Gagal link pegawai: {link.text}"

        # Force delete harus ditolak (409) karena pegawai masih terhubung
        resp = await client_with_db.delete(
            f"{BASE}/{_UNIT_LINKED['id_unit']}?force=true",
            headers=auth_headers_admin,
        )
        assert resp.status_code == 409

        # Soft delete TETAP diperbolehkan meski ada pegawai
        soft = await client_with_db.delete(
            f"{BASE}/{_UNIT_LINKED['id_unit']}", headers=auth_headers_admin
        )
        assert soft.status_code == 200

    finally:
        # Pindahkan pegawai ke unit spare agar unit_linked bisa di-force-delete
        await client_with_db.put(
            "/api/v1/pegawai/TST_PGW_A",
            json={"id_unit": _UNIT_SPARE["id_unit"]},
            headers=auth_headers_admin,
        )
        # Hard-delete unit_linked (pegawai sudah pindah → count=0 → aman)
        await _ensure_deleted(client_with_db, auth_headers_admin, _UNIT_LINKED["id_unit"])
        # Spare masih ditautkan pegawai; cukup soft-delete sekarang.
        # _ensure_deleted di awal test berikutnya akan force-delete setelah
        # conftest membersihkan TST_PGW_A (sehingga count=0).
        await client_with_db.delete(
            f"{BASE}/{_UNIT_SPARE['id_unit']}", headers=auth_headers_admin
        )


async def test_delete_unit_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Hapus unit yang tidak ada → 404 (berlaku untuk soft maupun hard)."""
    resp = await client_with_db.delete(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404

    resp_force = await client_with_db.delete(
        f"{BASE}/9999999?force=true", headers=auth_headers_admin
    )
    assert resp_force.status_code == 404


async def test_delete_unit_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa menghapus unit → 403."""
    resp = await client_with_db.delete(f"{BASE}/1", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_delete_unit_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.delete(f"{BASE}/1")
    assert resp.status_code == 403
