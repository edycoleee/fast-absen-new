"""
Tests untuk /api/v1/pegawai endpoints.

Endpoint yang tersedia:
  GET    /pegawai                       → paginated (meta.page, meta.limit, meta.total)
  GET    /pegawai/{id_pegawai}          → detail (200)
  POST   /pegawai                       → create (201)
  PUT    /pegawai/{id_pegawai}          → update (200)
  DELETE /pegawai/{id_pegawai}          → soft delete default (is_active → False)
  DELETE /pegawai/{id_pegawai}?force=true → hard delete permanen (hanya jika tidak ada deps)

Catatan:
  - id_pegawai bukan auto-increment, harus disuplai saat create.
  - Soft delete → is_active = False, record masih ada tapi hilang dari GET list.
  - Hard delete ditolak (409) jika ada absensi / user / embedding terhubung.
  - conftest menyediakan TST_PGW_A (linked ke tst_admin) untuk uji conflict.

Fixtures dari conftest:
  - client_with_db     : AsyncClient + real DB + tst_admin / tst_user seeded
  - auth_headers_admin : Bearer token tst_admin (semua permission)
  - auth_headers_user  : Bearer token tst_user (hanya user.login)
"""
from httpx import AsyncClient

BASE = "/api/v1/pegawai"

# ID & nama jauh dari range data produksi
_TEST_PEGAWAI = {"id_pegawai": "TST_P_001", "nama": "Pegawai Test CRUD"}
_TEST_PEGAWAI_2 = {"id_pegawai": "TST_P_002", "nama": "Pegawai Test Extra"}

# ID yang terhubung ke tst_admin (dari conftest) — dipakai untuk uji conflict
_PEGAWAI_WITH_USER = "TST_PGW_A"


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

async def _ensure_deleted(client: AsyncClient, headers: dict, id_pegawai: str) -> None:
    """Hard-delete pegawai agar cleanup benar-benar bersih.
    Pakai ?force=true. Abaikan error (404 = sudah bersih).
    """
    await client.delete(f"{BASE}/{id_pegawai}", params={"force": "true"}, headers=headers)


async def _create_test_pegawai(
    client: AsyncClient,
    headers: dict,
    payload: dict = None,
) -> dict:
    """Buat pegawai test, pre-cleanup dulu. Kembalikan data response."""
    if payload is None:
        payload = _TEST_PEGAWAI
    await _ensure_deleted(client, headers, payload["id_pegawai"])
    resp = await client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, f"Gagal membuat pegawai: {resp.text}"
    return resp.json()["data"]


# ─────────────────────────────────────────────────────────────────────────────
# LIST  GET /api/v1/pegawai
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_pegawai_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin mendapatkan daftar pegawai (200)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert "meta" in body
    assert "total" in body["meta"]
    assert isinstance(body["data"]["items"], list)


async def test_list_pegawai_pagination(
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


async def test_list_pegawai_item_fields(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setiap item memiliki field id_pegawai, nama, status."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.get(BASE, params={"limit": 100}, headers=auth_headers_admin)
        items = resp.json()["data"]["items"]
        assert len(items) > 0
        for item in items[:5]:
            assert "id_pegawai" in item
            assert "nama" in item
            assert "is_active" in item
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_list_pegawai_search(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Parameter search memfilter berdasarkan nama / nip."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.get(
            BASE, params={"search": "Pegawai Test CRUD", "limit": 50}, headers=auth_headers_admin
        )
        assert resp.status_code == 200
        ids = [p["id_pegawai"] for p in resp.json()["data"]["items"]]
        assert _TEST_PEGAWAI["id_pegawai"] in ids
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_list_pegawai_filter_unit(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Parameter unit_id memfilter pegawai berdasarkan unit."""
    payload = {**_TEST_PEGAWAI, "id_unit": 1}
    data = await _create_test_pegawai(client_with_db, auth_headers_admin, payload)
    try:
        resp = await client_with_db.get(
            BASE, params={"unit_id": 1, "limit": 100}, headers=auth_headers_admin
        )
        assert resp.status_code == 200
        ids = [p["id_pegawai"] for p in resp.json()["data"]["items"]]
        assert _TEST_PEGAWAI["id_pegawai"] in ids
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_list_pegawai_only_aktif(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """GET list hanya menampilkan pegawai dengan is_active = True."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        # Soft-delete
        await client_with_db.delete(f"{BASE}/{data['id_pegawai']}", headers=auth_headers_admin)
        resp = await client_with_db.get(BASE, params={"limit": 100}, headers=auth_headers_admin)
        ids = [p["id_pegawai"] for p in resp.json()["data"]["items"]]
        assert data["id_pegawai"] not in ids, "Pegawai is_active=False tidak boleh muncul di daftar"
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_list_pegawai_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa (tanpa pegawai.read) → 403."""
    resp = await client_with_db.get(BASE, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_list_pegawai_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(BASE)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DETAIL  GET /api/v1/pegawai/{id_pegawai}
# ─────────────────────────────────────────────────────────────────────────────

async def test_get_pegawai_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa melihat detail pegawai (200)."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.get(f"{BASE}/{data['id_pegawai']}", headers=auth_headers_admin)
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["id_pegawai"] == data["id_pegawai"]
        assert body["nama"] == _TEST_PEGAWAI["nama"]
        assert "is_active" in body
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_get_pegawai_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Detail pegawai yang tidak ada → 404."""
    resp = await client_with_db.get(f"{BASE}/TST_GHOST_9999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_get_pegawai_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa (tanpa pegawai.read) → 403."""
    resp = await client_with_db.get(f"{BASE}/{_PEGAWAI_WITH_USER}", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_get_pegawai_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(f"{BASE}/{_PEGAWAI_WITH_USER}")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CREATE  POST /api/v1/pegawai
# ─────────────────────────────────────────────────────────────────────────────

async def test_create_pegawai_minimal(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Payload minimal (id_pegawai + nama) berhasil create (201)."""
    await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_PEGAWAI["id_pegawai"])
    resp = await client_with_db.post(BASE, json=_TEST_PEGAWAI, headers=auth_headers_admin)
    try:
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["id_pegawai"] == _TEST_PEGAWAI["id_pegawai"]
        assert data["nama"] == _TEST_PEGAWAI["nama"]
        assert data["is_active"] == True
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, _TEST_PEGAWAI["id_pegawai"])


async def test_create_pegawai_full(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Payload lengkap berhasil create (201)."""
    payload = {
        **_TEST_PEGAWAI_2,
        "nip": "TST202600001",
        "id_unit": 1,
        "jenis_kelamin": "MALE",
        "tempat_lahir": "Test City",
        "tanggal_lahir": "1990-01-15",
        "alamat": "Jl. Test No. 1",
    }
    await _ensure_deleted(client_with_db, auth_headers_admin, payload["id_pegawai"])
    resp = await client_with_db.post(BASE, json=payload, headers=auth_headers_admin)
    try:
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["id_pegawai"] == payload["id_pegawai"]
        assert data["id_unit"] == 1
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, payload["id_pegawai"])


async def test_create_pegawai_duplicate_id(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """ID pegawai yang sudah ada → 400."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.post(BASE, json=_TEST_PEGAWAI, headers=auth_headers_admin)
        assert resp.status_code == 400
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_create_pegawai_missing_nama(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Field nama wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE, json={"id_pegawai": "TST_P_NONAME"}, headers=auth_headers_admin
    )
    assert resp.status_code == 422


async def test_create_pegawai_missing_id(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Field id_pegawai wajib — 422 jika tidak ada."""
    resp = await client_with_db.post(
        BASE, json={"nama": "Tanpa ID"}, headers=auth_headers_admin
    )
    assert resp.status_code == 422


async def test_create_pegawai_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa membuat pegawai → 403."""
    resp = await client_with_db.post(BASE, json=_TEST_PEGAWAI, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_create_pegawai_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.post(BASE, json=_TEST_PEGAWAI)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE  PUT /api/v1/pegawai/{id_pegawai}
# ─────────────────────────────────────────────────────────────────────────────

async def test_update_pegawai_nama(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa update nama pegawai (200)."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.put(
            f"{BASE}/{data['id_pegawai']}",
            json={"nama": "Pegawai Test Updated"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["nama"] == "Pegawai Test Updated"
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_update_pegawai_unit(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa update id_unit pegawai (200)."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.put(
            f"{BASE}/{data['id_pegawai']}",
            json={"id_unit": 2},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["id_unit"] == 2
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_update_pegawai_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update pegawai yang tidak ada → 404."""
    resp = await client_with_db.put(
        f"{BASE}/TST_GHOST_9999",
        json={"nama": "Ghost"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 404


async def test_update_pegawai_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa update pegawai → 403."""
    resp = await client_with_db.put(
        f"{BASE}/{_PEGAWAI_WITH_USER}",
        json={"nama": "Hijack"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_update_pegawai_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.put(f"{BASE}/{_PEGAWAI_WITH_USER}", json={"nama": "Ghost"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DELETE  DELETE /api/v1/pegawai/{id_pegawai}
# ─────────────────────────────────────────────────────────────────────────────

async def test_delete_pegawai_soft_default(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE tanpa force → soft delete: is_active = False, record masih ada (200)."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        resp = await client_with_db.delete(f"{BASE}/{data['id_pegawai']}", headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # GET detail masih bisa, status berubah
        detail = await client_with_db.get(f"{BASE}/{data['id_pegawai']}", headers=auth_headers_admin)
        assert detail.status_code == 200
        assert detail.json()["data"]["is_active"] == False
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_delete_pegawai_soft_hidden_from_list(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Pegawai is_active=False tidak muncul di GET list (hanya is_active=True yang tampil)."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)
    try:
        await client_with_db.delete(f"{BASE}/{data['id_pegawai']}", headers=auth_headers_admin)
        resp = await client_with_db.get(BASE, params={"limit": 100}, headers=auth_headers_admin)
        ids = [p["id_pegawai"] for p in resp.json()["data"]["items"]]
        assert data["id_pegawai"] not in ids
    finally:
        await _ensure_deleted(client_with_db, auth_headers_admin, data["id_pegawai"])


async def test_delete_pegawai_hard_force(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE ?force=true → hard delete: record benar-benar hilang dari DB (200 → 404)."""
    data = await _create_test_pegawai(client_with_db, auth_headers_admin)

    resp = await client_with_db.delete(
        f"{BASE}/{data['id_pegawai']}", params={"force": "true"}, headers=auth_headers_admin
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verifikasi benar-benar hilang
    detail = await client_with_db.get(f"{BASE}/{data['id_pegawai']}", headers=auth_headers_admin)
    assert detail.status_code == 404


async def test_delete_pegawai_hard_conflict_with_user(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """DELETE ?force=true pada pegawai yang terhubung ke user → 409 Conflict."""
    # TST_PGW_A sudah di-seed di conftest dan linked ke tst_admin
    resp = await client_with_db.delete(
        f"{BASE}/{_PEGAWAI_WITH_USER}", params={"force": "true"}, headers=auth_headers_admin
    )
    assert resp.status_code == 409


async def test_delete_pegawai_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Hapus pegawai yang tidak ada → 404."""
    resp = await client_with_db.delete(f"{BASE}/TST_GHOST_9999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_delete_pegawai_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """User biasa tidak bisa menghapus pegawai → 403."""
    resp = await client_with_db.delete(f"{BASE}/{_PEGAWAI_WITH_USER}", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_delete_pegawai_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.delete(f"{BASE}/{_PEGAWAI_WITH_USER}")
    assert resp.status_code == 403
