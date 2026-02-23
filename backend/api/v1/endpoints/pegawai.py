from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.pegawai import PegawaiCreate, PegawaiUpdate
from services.pegawai_service import PegawaiService
from repositories.pegawai_repository import PegawaiRepository
from utils.response import success_response, paginated_response
from utils.dependencies import CommonQueryParams, require_permission
from utils.permission_registry import PermissionKeys
from utils.constants import ErrorMessages, HTTPStatus as HC, SuccessMessages
from fastapi import Query
from typing import Optional

router = APIRouter(prefix="/pegawai", tags=["Pegawai"])


def _fmt(p):
    return {
        "id_pegawai": p.id_pegawai, "nip": p.nip, "nama": p.nama,
        "id_unit": p.id_unit, "jenis_kelamin": p.jenis_kelamin,
        "status": p.status, "foto": p.foto,
    }


@router.get("")
async def list_pegawai(
    q: CommonQueryParams = Depends(),
    unit_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PEGAWAI_READ)),
):
    svc = PegawaiService(PegawaiRepository(db))
    items, total = await svc.get_paged(q.page, q.limit, q.search, unit_id)
    return paginated_response("Berhasil", items=[_fmt(p) for p in items], page=q.page, limit=q.limit, total=total)


@router.get("/{id_pegawai}")
async def get_pegawai(
    id_pegawai: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PEGAWAI_READ)),
):
    svc = PegawaiService(PegawaiRepository(db))
    p = await svc.get_by_id(id_pegawai)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Pegawai"))
    return success_response("Berhasil", data=_fmt(p))


@router.post("", status_code=HC.CREATED)
async def create_pegawai(
    body: PegawaiCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PEGAWAI_CREATE)),
):
    svc = PegawaiService(PegawaiRepository(db))
    p = await svc.create_pegawai(body.model_dump())
    return success_response(SuccessMessages.CREATED.format("Pegawai"), data=_fmt(p))


@router.put("/{id_pegawai}")
async def update_pegawai(
    id_pegawai: str,
    body: PegawaiUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PEGAWAI_UPDATE)),
):
    svc = PegawaiService(PegawaiRepository(db))
    p = await svc.update_pegawai(id_pegawai, body.model_dump())
    return success_response(SuccessMessages.UPDATED.format("Pegawai"), data=_fmt(p))


@router.delete("/{id_pegawai}")
async def delete_pegawai(
    id_pegawai: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PEGAWAI_DELETE)),
):
    svc = PegawaiService(PegawaiRepository(db))
    await svc.delete_pegawai(id_pegawai)
    return success_response(SuccessMessages.DELETED.format("Pegawai"))
