from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from services.permission_service import PermissionService
from repositories.permission_repository import PermissionRepository
from utils.response import success_response, list_response
from utils.dependencies import require_permission
from utils.permission_registry import PermissionKeys, list_permissions
from utils.constants import SuccessMessages, HTTPStatus as HC
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/permissions", tags=["Permissions"])


class PermissionCreate(BaseModel):
    name: str
    description: Optional[str] = None


@router.get("")
async def list_perms(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PERMISSIONS_READ)),
):
    svc = PermissionService(PermissionRepository(db))
    items, total = await svc.get_all(page=1, limit=500)
    data = [{"id": p.id, "name": p.name, "description": p.description} for p in items]
    return list_response("Berhasil", items=data, total=total)


@router.get("/registry")
async def get_registry(_=Depends(require_permission(PermissionKeys.PERMISSIONS_READ))):
    return success_response("OK", data={"items": list_permissions()})


@router.post("", status_code=HC.CREATED)
async def create_perm(
    body: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PERMISSIONS_CREATE)),
):
    svc = PermissionService(PermissionRepository(db))
    perm = await svc.create_permission(body.name, body.description)
    return success_response(SuccessMessages.CREATED.format("Permission"), data={"id": perm.id, "name": perm.name})


@router.delete("/{perm_id}")
async def delete_perm(
    perm_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.PERMISSIONS_DELETE)),
):
    svc = PermissionService(PermissionRepository(db))
    await svc.delete_permission(perm_id)
    return success_response(SuccessMessages.DELETED.format("Permission"))
