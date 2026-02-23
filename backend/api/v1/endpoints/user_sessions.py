from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from config.database import get_db
from services.user_session_service import UserSessionService
from repositories.user_session_repository import UserSessionRepository
from utils.response import success_response, paginated_response
from utils.dependencies import CommonQueryParams, require_permission, get_current_user
from utils.permission_registry import PermissionKeys
from models.user import User

router = APIRouter(prefix="/user-sessions", tags=["User Sessions"])


def _fmt(s):
    return {
        "id": s.id, "user_id": s.user_id,
        "ip_address": s.ip_address,
        "device_type": s.device_type,
        "device_model": s.device_model,
        "browser": s.browser,
        "os": s.os,
        "login_at": str(s.login_at),
        "logout_at": str(s.logout_at) if s.logout_at else None,
        "login_method": s.login_method, "login_status": s.login_status,
    }


@router.get("")
async def list_sessions(
    q: CommonQueryParams = Depends(),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    svc = UserSessionService(UserSessionRepository(db))
    items, total = await svc.get_paged(q.page, q.limit, user_id)
    return paginated_response("Berhasil", items=[_fmt(s) for s in items], page=q.page, limit=q.limit, total=total)


@router.post("/{session_id}/logout")
async def logout_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = UserSessionService(UserSessionRepository(db))
    session = await svc.logout_session(session_id, current_user.id)
    return success_response("Sesi berhasil dilogout", data=_fmt(session))


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_DELETE)),
):
    svc = UserSessionService(UserSessionRepository(db))
    await svc.repo.delete(session_id)
    return success_response("Sesi berhasil dihapus")
