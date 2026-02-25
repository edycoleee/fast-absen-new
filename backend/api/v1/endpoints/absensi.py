from fastapi import APIRouter, Depends, Request, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date
from config.database import get_db
from schemas.absensi import CheckInRequest, CheckOutRequest, AbsensiUpdate
from services.absensi_service import AbsensiService
from utils.response import success_response, paginated_response
from utils.dependencies import CommonQueryParams, require_permission, get_current_user
from utils.permission_registry import PermissionKeys
from utils.constants import ErrorMessages, HTTPStatus as HC, SuccessMessages
from utils.device_detector import get_client_ip
from models.user import User

router = APIRouter(prefix="/absensi", tags=["Absensi"])


def _fmt(a):
    return {
        "id": a.id, "id_pegawai": a.id_pegawai, "tanggal": str(a.tanggal),
        "jam_masuk": str(a.jam_masuk) if a.jam_masuk else None,
        "jam_keluar": str(a.jam_keluar) if a.jam_keluar else None,
        "status": a.status, "keterangan": a.keterangan,
        "face_verified_masuk": a.face_verified_masuk,
        "face_verified_keluar": a.face_verified_keluar,
    }


# ─── GET /absensi/today ───────────────────────────────────────────────────
@router.get("/today", summary="Absensi hari ini milik user yang sedang login")
async def get_today(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_permission(PermissionKeys.ABSENSI_READ)),
):
    if not current_user.id_pegawai:
        raise HTTPException(HC.BAD_REQUEST, ErrorMessages.NOT_FOUND.format("Data pegawai pada user ini"))
    svc = AbsensiService(db)
    a = await svc.get_today(current_user.id_pegawai)
    return success_response("Berhasil", data=_fmt(a) if a else None)


# ─── GET /absensi/history ─────────────────────────────────────────────────
@router.get("/history", summary="Riwayat absensi user yang sedang login (paginated, optional date filter)")
async def get_history(
    q: CommonQueryParams = Depends(),
    start_date: Optional[date] = Query(None, description="Filter dari tanggal (YYYY-MM-DD)"),
    end_date:   Optional[date] = Query(None, description="Filter sampai tanggal (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_permission(PermissionKeys.ABSENSI_READ)),
):
    if not current_user.id_pegawai:
        raise HTTPException(HC.BAD_REQUEST, ErrorMessages.NOT_FOUND.format("Data pegawai pada user ini"))
    svc = AbsensiService(db)
    items, total = await svc.get_history(current_user.id_pegawai, q.page, q.limit, start_date, end_date)
    return paginated_response("Berhasil", items=[_fmt(a) for a in items], page=q.page, limit=q.limit, total=total)


# ─── GET /absensi/summary ─────────────────────────────────────────────────
@router.get("/summary", summary="Rekap jumlah absensi per status untuk user yang sedang login")
async def get_summary(
    start_date: Optional[date] = Query(None, description="Filter dari tanggal (YYYY-MM-DD)"),
    end_date:   Optional[date] = Query(None, description="Filter sampai tanggal (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _=Depends(require_permission(PermissionKeys.ABSENSI_READ)),
):
    if not current_user.id_pegawai:
        raise HTTPException(HC.BAD_REQUEST, ErrorMessages.NOT_FOUND.format("Data pegawai pada user ini"))
    svc = AbsensiService(db)
    result = await svc.get_summary(current_user.id_pegawai, start_date, end_date)
    return success_response("Berhasil", data=result)


# ─── GET /absensi/statistics ──────────────────────────────────────────────
@router.get("/statistics", summary="Statistik absensi global (admin) per status, opsional filter tanggal & unit")
async def get_statistics(
    target_date: Optional[date] = Query(None, description="Tanggal spesifik (YYYY-MM-DD)"),
    start_date:  Optional[date] = Query(None, description="Filter dari tanggal"),
    end_date:    Optional[date] = Query(None, description="Filter sampai tanggal"),
    id_unit:     Optional[int]  = Query(None, description="Filter per unit"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ABSENSI_READ)),
):
    svc = AbsensiService(db)
    result = await svc.get_statistics(target_date, start_date, end_date, id_unit)
    return success_response("Berhasil", data=result)


# ─── GET /absensi/ ────────────────────────────────────────────────────────────
@router.get("")
async def list_absensi(
    q: CommonQueryParams = Depends(),
    id_pegawai: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ABSENSI_READ)),
):
    svc = AbsensiService(db)
    items, total = await svc.get_paged(q.page, q.limit, id_pegawai)
    return paginated_response("Berhasil", items=[_fmt(a) for a in items], page=q.page, limit=q.limit, total=total)


@router.post("/check-in")
async def check_in(
    body: CheckInRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.id_pegawai:
        raise HTTPException(HC.BAD_REQUEST, ErrorMessages.NOT_FOUND.format("Data pegawai pada user ini"))
    svc = AbsensiService(db)
    ip = get_client_ip(request)
    absensi = await svc.check_in(current_user.id_pegawai, ip, body.keterangan)
    return success_response(SuccessMessages.CREATED.format("Absen masuk"), data=_fmt(absensi))


@router.post("/check-out")
async def check_out(
    body: CheckOutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.id_pegawai:
        raise HTTPException(HC.BAD_REQUEST, ErrorMessages.NOT_FOUND.format("Data pegawai pada user ini"))
    svc = AbsensiService(db)
    absensi = await svc.check_out(current_user.id_pegawai, body.keterangan)
    return success_response(SuccessMessages.UPDATED.format("Absen keluar"), data=_fmt(absensi))


# ─── GET /absensi/{absensi_id} ────────────────────────────────────────────────
@router.get("/{absensi_id}", summary="Detail satu record absensi")
async def get_absensi(
    absensi_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ABSENSI_READ)),
):
    svc = AbsensiService(db)
    a = await svc.get_by_id(absensi_id)
    if not a:
        raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Absensi"))
    return success_response("Berhasil", data=_fmt(a))


# ─── PUT /absensi/{absensi_id} ────────────────────────────────────────────────
@router.put("/{absensi_id}")
async def update_absensi(
    absensi_id: int,
    body: AbsensiUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ABSENSI_UPDATE)),
):
    from repositories.absensi_repository import AbsensiRepository
    repo = AbsensiRepository(db)
    a = await repo.get_by_id(absensi_id)
    if not a:
        raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Absensi"))
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return success_response(SuccessMessages.UPDATED.format("Absensi"), data=_fmt(a))


# ─── DELETE /absensi/{absensi_id} ─────────────────────────────────────────────
@router.delete("/{absensi_id}", summary="Hapus permanen record absensi")
async def delete_absensi(
    absensi_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ABSENSI_DELETE)),
):
    svc = AbsensiService(db)
    await svc.delete_absensi(absensi_id)
    return success_response(SuccessMessages.DELETED.format("Absensi"))
