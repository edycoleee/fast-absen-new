from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.unit import UnitCreate, UnitUpdate
from services.unit_service import UnitService
from repositories.unit_repository import UnitRepository
from utils.response import success_response, paginated_response
from utils.dependencies import CommonQueryParams, require_permission
from utils.permission_registry import PermissionKeys
from utils.constants import SuccessMessages, HTTPStatus as HC

router = APIRouter(prefix="/unit", tags=["Unit"])


def _fmt(u): return {"id_unit": u.id_unit, "nama_unit": u.nama_unit, "is_active": u.is_active}


@router.get("")
async def list_units(
    q: CommonQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.UNIT_READ)),
):
    svc = UnitService(UnitRepository(db))
    items, total = await svc.get_paged(q.page, q.limit)
    return paginated_response("Berhasil", items=[_fmt(u) for u in items], page=q.page, limit=q.limit, total=total)


@router.get("/{id_unit}")
async def get_unit(
    id_unit: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.UNIT_READ)),
):
    svc = UnitService(UnitRepository(db))
    unit = await svc.get_unit(id_unit)
    return success_response("Berhasil", data=_fmt(unit))


@router.post("", status_code=HC.CREATED)
async def create_unit(
    body: UnitCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.UNIT_CREATE)),
):
    svc = UnitService(UnitRepository(db))
    unit = await svc.create_unit(body.id_unit, body.nama_unit, body.is_active)
    return success_response(SuccessMessages.CREATED.format("Unit"), data=_fmt(unit))


@router.put("/{id_unit}")
async def update_unit(
    id_unit: int,
    body: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.UNIT_UPDATE)),
):
    svc = UnitService(UnitRepository(db))
    unit = await svc.update_unit(id_unit, body.model_dump())
    return success_response(SuccessMessages.UPDATED.format("Unit"), data=_fmt(unit))


@router.delete("/{id_unit}")
async def delete_unit(
    id_unit: int,
    force: bool = Query(
        False,
        description="Jika True, hapus permanen dari DB (hard delete). "
                    "Hanya diizinkan jika tidak ada pegawai yang masih terhubung. "
                    "Default False = soft delete (nonaktifkan).",
    ),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.UNIT_DELETE)),
):
    svc = UnitService(UnitRepository(db))
    await svc.delete_unit(id_unit, force=force)
    msg = SuccessMessages.DELETED.format("Unit") if force else "Unit berhasil dinonaktifkan"
    return success_response(msg)
