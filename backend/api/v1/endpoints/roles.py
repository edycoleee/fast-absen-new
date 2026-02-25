from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.role import RoleCreate, RoleUpdate
from services.role_service import RoleService
from repositories.role_repository import RoleRepository
from utils.response import success_response, list_response
from utils.dependencies import require_permission
from utils.permission_registry import PermissionKeys
from utils.constants import SuccessMessages, HTTPStatus as HC

router = APIRouter(prefix="/roles", tags=["Roles"])


def _fmt(role):
    return {
        "id": role.id, "name": role.name, "description": role.description,
        "permissions": [{"id": p.id, "name": p.name} for p in (role.permissions or [])],
    }


@router.get("")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ROLES_READ)),
):
    svc = RoleService(RoleRepository(db))
    roles = await svc.get_all_with_permissions()
    return list_response("Berhasil", items=[_fmt(r) for r in roles], total=len(roles))


@router.get("/{role_id}")
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ROLES_READ)),
):
    svc = RoleService(RoleRepository(db))
    role = await svc.get_role(role_id)
    return success_response("Berhasil", data=_fmt(role))


@router.post("", status_code=HC.CREATED)
async def create_role(
    body: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ROLES_CREATE)),
):
    svc = RoleService(RoleRepository(db))
    role = await svc.create_role(body.name, body.description, body.permission_ids or [])
    return success_response(SuccessMessages.CREATED.format("Role"), data=_fmt(role))


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ROLES_UPDATE)),
):
    svc = RoleService(RoleRepository(db))
    role = await svc.update_role(role_id, body.model_dump(exclude_none=True, exclude={"permission_ids"}), body.permission_ids)
    return success_response(SuccessMessages.UPDATED.format("Role"), data=_fmt(role))


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.ROLES_DELETE)),
):
    svc = RoleService(RoleRepository(db))
    await svc.delete_role(role_id)
    return success_response(SuccessMessages.DELETED.format("Role"))
