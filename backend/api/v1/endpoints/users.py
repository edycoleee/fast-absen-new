from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.user import UserCreate, UserUpdate
from services.user_service import UserService
from repositories.user_repository import UserRepository
from utils.response import success_response, paginated_response
from utils.dependencies import CommonQueryParams, require_permission
from utils.permission_registry import PermissionKeys
from utils.constants import ErrorMessages, HTTPStatus as HC, SuccessMessages
import json

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("")
async def list_users(
    q: CommonQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USERS_READ)),
):
    svc = UserService(UserRepository(db))
    items, total = await svc.get_all(page=q.page, limit=q.limit)
    data = [{"id": u.id, "username": u.username, "id_pegawai": u.id_pegawai, "is_active": u.is_active} for u in items]
    return paginated_response("Berhasil", items=data, page=q.page, limit=q.limit, total=total)


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USERS_READ)),
):
    svc = UserService(UserRepository(db))
    user = await svc.get_by_id_with_roles(user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("User"))
    return success_response("Berhasil", data={
        "id": user.id, "username": user.username,
        "id_pegawai": user.id_pegawai, "is_active": user.is_active,
        "roles": [r.name for r in user.roles],
        "permissions": list(user.permissions),
    })


@router.post("", status_code=HC.CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USERS_CREATE)),
):
    svc = UserService(UserRepository(db))
    user = await svc.create_user(
        {"id_pegawai": body.id_pegawai, "username": body.username, "password": body.password},
        body.role_ids or [],
    )
    return success_response(SuccessMessages.CREATED.format("User"), data={"id": user.id, "username": user.username})


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USERS_UPDATE)),
):
    svc = UserService(UserRepository(db))
    user = await svc.update_user(user_id, body.model_dump(exclude_none=True), body.role_ids)
    return success_response(SuccessMessages.UPDATED.format("User"), data={"id": user.id, "username": user.username})


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USERS_DELETE)),
):
    svc = UserService(UserRepository(db))
    await svc.delete_user(user_id)
    return success_response(SuccessMessages.DELETED.format("User"))
