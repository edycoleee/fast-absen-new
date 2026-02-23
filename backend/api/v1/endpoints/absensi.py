from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
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
        from fastapi import HTTPException
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
        from fastapi import HTTPException
        raise HTTPException(HC.BAD_REQUEST, ErrorMessages.NOT_FOUND.format("Data pegawai pada user ini"))
    svc = AbsensiService(db)
    absensi = await svc.check_out(current_user.id_pegawai, body.keterangan)
    return success_response(SuccessMessages.UPDATED.format("Absen keluar"), data=_fmt(absensi))


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
        from fastapi import HTTPException
        raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Absensi"))
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(a, k, v)
    await db.commit()
    await db.refresh(a)
    return success_response(SuccessMessages.UPDATED.format("Absensi"), data=_fmt(a))
