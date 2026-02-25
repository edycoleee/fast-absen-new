"""
Tests untuk /api/v1/absensi endpoints.

Endpoint yang tersedia:
  GET    /absensi/today           → absensi hari ini milik current_user
  GET    /absensi/history         → riwayat paginated current_user
  GET    /absensi/summary         → rekap per-status current_user
  GET    /absensi/statistics      → statistik global admin (absensi.read)
  GET    /absensi                 → paginated list (absensi.read)
  POST   /absensi/check-in        → check-in current_user
  POST   /absensi/check-out       → check-out current_user
  GET    /absensi/{absensi_id}    → detail satu record (absensi.read)
  PUT    /absensi/{absensi_id}    → update admin (absensi.update)
  DELETE /absensi/{absensi_id}    → hard delete (absensi.delete)

Catatan:
  - UNIQUE constraint: 1 record per pegawai per tanggal.
  - check-in/check-out/today/history/summary menggunakan current_user.id_pegawai.
  - conftest seeds: TST_PGW_A <-> tst_admin, TST_PGW_U <-> tst_user.
"""
from httpx import AsyncClient
from sqlalchemy import text
from config.database import AsyncSessionLocal

BASE = "/api/v1/absensi"

_PGW_ADMIN = "TST_PGW_A"   # tst_admin
_PGW_USER  = "TST_PGW_U"   # tst_user


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _delete_today_absensi(id_pegawai: str) -> None:
    """Hapus record absensi hari ini untuk pegawai tertentu (cleanup test)."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM absensi WHERE id_pegawai = :p AND tanggal = CURRENT_DATE"),
                {"p": id_pegawai},
            )


async def _delete_all_absensi(id_pegawai: str) -> None:
    """Hapus semua record absensi untuk pegawai tertentu."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM absensi WHERE id_pegawai = :p"),
                {"p": id_pegawai},
            )


# ─────────────────────────────────────────────────────────────────────────────
# GET /absensi/today
# ─────────────────────────────────────────────────────────────────────────────

async def test_today_no_record(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Belum check-in → data null (200)."""
    await _delete_today_absensi(_PGW_ADMIN)
    resp = await client_with_db.get(BASE + "/today", headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert not body["data"]


async def test_today_after_checkin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setelah check-in → today mengembalikan record hari ini."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        resp = await client_with_db.get(BASE + "/today", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data is not None
        assert data["id_pegawai"] == _PGW_ADMIN
        assert data["jam_masuk"] is not None
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_today_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(BASE + "/today")
    assert resp.status_code == 403


async def test_today_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """tst_user tidak punya absensi.read → 403."""
    resp = await client_with_db.get(BASE + "/today", headers=auth_headers_user)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# GET /absensi/history
# ─────────────────────────────────────────────────────────────────────────────

async def test_history_returns_list(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Riwayat mengembalikan struktur paginated."""
    resp = await client_with_db.get(BASE + "/history", headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert "meta" in body


async def test_history_contains_checkin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setelah check-in, record muncul di history."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        ci = await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        absensi_id = ci.json()["data"]["id"]
        resp = await client_with_db.get(
            BASE + "/history", params={"limit": 50}, headers=auth_headers_admin
        )
        ids = [a["id"] for a in resp.json()["data"]["items"]]
        assert absensi_id in ids
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_history_date_filter(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Filter start_date=tomorrow → tidak ada record hari ini."""
    from datetime import date, timedelta
    tomorrow = str(date.today() + timedelta(days=1))
    resp = await client_with_db.get(
        BASE + "/history",
        params={"start_date": tomorrow},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 0


async def test_history_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(BASE + "/history")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# GET /absensi/summary
# ─────────────────────────────────────────────────────────────────────────────

async def test_summary_structure(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Respons memiliki field id_pegawai, total, breakdown."""
    resp = await client_with_db.get(BASE + "/summary", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "id_pegawai" in data
    assert "total" in data
    assert "breakdown" in data
    assert data["id_pegawai"] == _PGW_ADMIN


async def test_summary_counts_checkin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setelah check-in, summary total bertambah 1."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        before = (
            await client_with_db.get(BASE + "/summary", headers=auth_headers_admin)
        ).json()["data"]["total"]
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        after = (
            await client_with_db.get(BASE + "/summary", headers=auth_headers_admin)
        ).json()["data"]["total"]
        assert after == before + 1
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_summary_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(BASE + "/summary")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# GET /absensi/statistics
# ─────────────────────────────────────────────────────────────────────────────

async def test_statistics_structure(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Respons memiliki field total dan breakdown."""
    resp = await client_with_db.get(BASE + "/statistics", headers=auth_headers_admin)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "total" in data
    assert "breakdown" in data
    assert isinstance(data["breakdown"], dict)


async def test_statistics_target_date(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Filter target_date mengembalikan data dengan field date yang sesuai."""
    from datetime import date
    today = str(date.today())
    resp = await client_with_db.get(
        BASE + "/statistics",
        params={"target_date": today},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["date"] == today


async def test_statistics_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """tst_user tidak punya absensi.read → 403."""
    resp = await client_with_db.get(BASE + "/statistics", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_statistics_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(BASE + "/statistics")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# LIST  GET /absensi
# ─────────────────────────────────────────────────────────────────────────────

async def test_list_absensi_admin(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin mendapatkan daftar absensi (200)."""
    resp = await client_with_db.get(BASE, headers=auth_headers_admin)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert "meta" in body
    assert "total" in body["meta"]
    assert isinstance(body["data"]["items"], list)


async def test_list_absensi_pagination(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Parameter page & limit bekerja dengan benar."""
    resp = await client_with_db.get(
        BASE, params={"page": 1, "limit": 1}, headers=auth_headers_admin
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]["items"]) <= 1
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 1


async def test_list_absensi_item_fields(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setiap item memiliki field id, id_pegawai, tanggal, status."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        resp = await client_with_db.get(
            BASE, params={"limit": 10}, headers=auth_headers_admin
        )
        items = resp.json()["data"]["items"]
        assert len(items) > 0
        item = items[0]
        for field in ("id", "id_pegawai", "tanggal", "status"):
            assert field in item, f"Field '{field}' tidak ada di response"
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_list_absensi_filter_by_pegawai(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Parameter id_pegawai memfilter hasil hanya untuk pegawai tersebut."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        resp = await client_with_db.get(
            BASE,
            params={"id_pegawai": _PGW_ADMIN, "limit": 50},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1
        for item in items:
            assert item["id_pegawai"] == _PGW_ADMIN
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_list_absensi_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """tst_user tidak punya absensi.read → 403."""
    resp = await client_with_db.get(BASE, headers=auth_headers_user)
    assert resp.status_code == 403


async def test_list_absensi_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(BASE)
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CHECK-IN  POST /absensi/check-in
# ─────────────────────────────────────────────────────────────────────────────

async def test_check_in_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-in berhasil (200), response berisi id, tanggal, jam_masuk."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        resp = await client_with_db.post(
            BASE + "/check-in", json={}, headers=auth_headers_admin
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["id_pegawai"] == _PGW_ADMIN
        assert data["jam_masuk"] is not None
        assert data["status"] in ("PRESENT", "LATE")
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_in_with_keterangan(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-in dengan keterangan opsional tersimpan di response."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        resp = await client_with_db.post(
            BASE + "/check-in",
            json={"keterangan": "Test hadir"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["keterangan"] == "Test hadir"
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_in_creates_list_entry(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Setelah check-in, record muncul di GET /absensi?id_pegawai=..."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        list_resp = await client_with_db.get(
            BASE,
            params={"id_pegawai": _PGW_ADMIN, "limit": 50},
            headers=auth_headers_admin,
        )
        ids = [a["id_pegawai"] for a in list_resp.json()["data"]["items"]]
        assert _PGW_ADMIN in ids
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_in_duplicate_today(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-in dua kali di hari yang sama → 400 (UNIQUE constraint)."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        first = await client_with_db.post(
            BASE + "/check-in", json={}, headers=auth_headers_admin
        )
        assert first.status_code == 200
        second = await client_with_db.post(
            BASE + "/check-in", json={}, headers=auth_headers_admin
        )
        assert second.status_code == 400
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_in_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.post(BASE + "/check-in", json={})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# CHECK-OUT  POST /absensi/check-out
# ─────────────────────────────────────────────────────────────────────────────

async def test_check_out_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-out setelah check-in berhasil, jam_keluar terisi."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        resp = await client_with_db.post(
            BASE + "/check-out", json={}, headers=auth_headers_admin
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id_pegawai"] == _PGW_ADMIN
        assert data["jam_keluar"] is not None
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_out_with_keterangan(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-out dengan keterangan tersimpan."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        resp = await client_with_db.post(
            BASE + "/check-out",
            json={"keterangan": "Selesai kerja"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["keterangan"] == "Selesai kerja"
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_out_without_check_in(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-out tanpa check-in terlebih dahulu → 400."""
    await _delete_today_absensi(_PGW_ADMIN)
    resp = await client_with_db.post(
        BASE + "/check-out", json={}, headers=auth_headers_admin
    )
    assert resp.status_code == 400


async def test_check_out_duplicate(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Check-out dua kali → 400."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        first = await client_with_db.post(
            BASE + "/check-out", json={}, headers=auth_headers_admin
        )
        assert first.status_code == 200
        second = await client_with_db.post(
            BASE + "/check-out", json={}, headers=auth_headers_admin
        )
        assert second.status_code == 400
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_check_out_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.post(BASE + "/check-out", json={})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# GET /absensi/{absensi_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_get_absensi_detail(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """GET /{id} mengembalikan record yang benar."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        ci = await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
        absensi_id = ci.json()["data"]["id"]
        resp = await client_with_db.get(f"{BASE}/{absensi_id}", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == absensi_id
        assert data["id_pegawai"] == _PGW_ADMIN
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_get_absensi_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """ID tidak ada → 404."""
    resp = await client_with_db.get(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_get_absensi_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """tst_user tidak punya absensi.read → 403."""
    resp = await client_with_db.get(f"{BASE}/1", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_get_absensi_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.get(f"{BASE}/1")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# PUT /absensi/{absensi_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_update_absensi_status(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa mengubah status absensi via PUT (200)."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        ci = await client_with_db.post(
            BASE + "/check-in", json={}, headers=auth_headers_admin
        )
        absensi_id = ci.json()["data"]["id"]
        resp = await client_with_db.put(
            f"{BASE}/{absensi_id}",
            json={"status": "SICK", "keterangan": "Sakit hari ini"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "SICK"
        assert data["keterangan"] == "Sakit hari ini"
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_update_absensi_jam_keluar(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Admin bisa mengisi jam_keluar manual via PUT."""
    await _delete_today_absensi(_PGW_ADMIN)
    try:
        ci = await client_with_db.post(
            BASE + "/check-in", json={}, headers=auth_headers_admin
        )
        absensi_id = ci.json()["data"]["id"]
        resp = await client_with_db.put(
            f"{BASE}/{absensi_id}",
            json={"jam_keluar": "2026-02-25T17:00:00+00:00"},
            headers=auth_headers_admin,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["jam_keluar"] is not None
    finally:
        await _delete_today_absensi(_PGW_ADMIN)


async def test_update_absensi_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Update absensi ID yang tidak ada → 404."""
    resp = await client_with_db.put(
        f"{BASE}/9999999",
        json={"keterangan": "Ghost"},
        headers=auth_headers_admin,
    )
    assert resp.status_code == 404


async def test_update_absensi_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """tst_user tidak punya absensi.update → 403."""
    resp = await client_with_db.put(
        f"{BASE}/1",
        json={"keterangan": "Hijack"},
        headers=auth_headers_user,
    )
    assert resp.status_code == 403


async def test_update_absensi_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.put(f"{BASE}/1", json={"keterangan": "Ghost"})
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /absensi/{absensi_id}
# ─────────────────────────────────────────────────────────────────────────────

async def test_delete_absensi_success(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Hard delete berhasil → record tidak bisa diambil lagi (404)."""
    await _delete_today_absensi(_PGW_ADMIN)
    ci = await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
    absensi_id = ci.json()["data"]["id"]

    resp = await client_with_db.delete(f"{BASE}/{absensi_id}", headers=auth_headers_admin)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    get_resp = await client_with_db.get(f"{BASE}/{absensi_id}", headers=auth_headers_admin)
    assert get_resp.status_code == 404


async def test_delete_absensi_not_found(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Delete ID yang tidak ada → 404."""
    resp = await client_with_db.delete(f"{BASE}/9999999", headers=auth_headers_admin)
    assert resp.status_code == 404


async def test_delete_absensi_forbidden(
    client_with_db: AsyncClient,
    auth_headers_user: dict,
):
    """tst_user tidak punya absensi.delete → 403."""
    resp = await client_with_db.delete(f"{BASE}/1", headers=auth_headers_user)
    assert resp.status_code == 403


async def test_delete_absensi_no_auth(client_with_db: AsyncClient):
    """Tanpa token → 403."""
    resp = await client_with_db.delete(f"{BASE}/1")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# FULL FLOW
# ─────────────────────────────────────────────────────────────────────────────

async def test_full_flow(
    client_with_db: AsyncClient,
    auth_headers_admin: dict,
):
    """Full flow: check-in -> today -> detail -> history -> summary -> check-out -> delete."""
    await _delete_today_absensi(_PGW_ADMIN)

    # 1. Check-in
    ci = await client_with_db.post(BASE + "/check-in", json={}, headers=auth_headers_admin)
    assert ci.status_code == 200
    absensi_id = ci.json()["data"]["id"]

    # 2. Today returns record
    today_resp = await client_with_db.get(BASE + "/today", headers=auth_headers_admin)
    assert today_resp.json()["data"]["id"] == absensi_id

    # 3. Detail
    detail_resp = await client_with_db.get(f"{BASE}/{absensi_id}", headers=auth_headers_admin)
    assert detail_resp.status_code == 200

    # 4. History contains it
    history_ids = [
        a["id"]
        for a in (
            await client_with_db.get(
                BASE + "/history", params={"limit": 50}, headers=auth_headers_admin
            )
        ).json()["data"]["items"]
    ]
    assert absensi_id in history_ids

    # 5. Summary total >= 1
    summary = (
        await client_with_db.get(BASE + "/summary", headers=auth_headers_admin)
    ).json()["data"]
    assert summary["total"] >= 1

    # 6. Check-out
    co = await client_with_db.post(BASE + "/check-out", json={}, headers=auth_headers_admin)
    assert co.status_code == 200
    assert co.json()["data"]["jam_keluar"] is not None

    # 7. Delete
    del_resp = await client_with_db.delete(f"{BASE}/{absensi_id}", headers=auth_headers_admin)
    assert del_resp.status_code == 200
    assert (
        await client_with_db.get(f"{BASE}/{absensi_id}", headers=auth_headers_admin)
    ).status_code == 404
