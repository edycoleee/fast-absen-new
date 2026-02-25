from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from config.database import get_db
from schemas.user_session import UserSessionCreate
from services.user_session_service import UserSessionService
from repositories.user_session_repository import UserSessionRepository
from utils.response import success_response, paginated_response
from utils.dependencies import CommonQueryParams, require_permission, get_current_user
from utils.permission_registry import PermissionKeys
from utils.constants import ErrorMessages, HTTPStatus as HC, SuccessMessages
from models.user import User

router = APIRouter(prefix="/user-sessions", tags=["User Sessions"])


def _fmt(s):
    return {
        "id":           s.id,
        "user_id":      s.user_id,
        "session_id":   s.session_id,
        "ip_address":   s.ip_address,
        "device_type":  s.device_type,
        "device_model": s.device_model,
        "browser":      s.browser,
        "os":           s.os,
        "country":      s.country,
        "city":         s.city,
        "login_at":     str(s.login_at),
        "logout_at":    str(s.logout_at) if s.logout_at else None,
        "last_activity":str(s.last_activity) if s.last_activity else None,
        "expires_at":   str(s.expires_at) if s.expires_at else None,
        "login_method": s.login_method,
        "login_status": s.login_status,
    }


def _svc(db: AsyncSession) -> UserSessionService:
    return UserSessionService(UserSessionRepository(db))


# ─── NOTE ON ROUTE ORDER ──────────────────────────────────────────────────────
# Static paths (active, history, statistics, heartbeat, cleanup-expired,
# by-session) must be declared BEFORE dynamic /{session_id} paths so FastAPI
# does not confuse them with integer path parameters.
# ──────────────────────────────────────────────────────────────────────────────


# ─── GET /user-sessions/active ───────────────────────────────────────────────
@router.get("/active", summary="Daftar sesi aktif (logout_at IS NULL)")
async def list_active_sessions(
    q: CommonQueryParams = Depends(),
    user_id: Optional[int] = Query(None, description="Filter berdasarkan user_id"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    items, total = await _svc(db).get_active(q.page, q.limit, user_id)
    return paginated_response(
        "Berhasil", items=[_fmt(s) for s in items],
        page=q.page, limit=q.limit, total=total,
    )


# ─── GET /user-sessions/history ──────────────────────────────────────────────
@router.get("/history", summary="Riwayat semua sesi (termasuk yang sudah logout)")
async def list_session_history(
    q: CommonQueryParams = Depends(),
    user_id: Optional[int] = Query(None, description="Filter berdasarkan user_id"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    items, total = await _svc(db).get_history(q.page, q.limit, user_id)
    return paginated_response(
        "Berhasil", items=[_fmt(s) for s in items],
        page=q.page, limit=q.limit, total=total,
    )


# ─── GET /user-sessions/statistics ───────────────────────────────────────────
@router.get("/statistics", summary="Statistik agregat sesi login")
async def session_statistics(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    stats = await _svc(db).get_statistics()
    return success_response("Berhasil", data=stats)


# ─── POST /user-sessions/heartbeat?session_id=... ────────────────────────────
@router.post("/heartbeat", summary="Perbarui last_activity sesi yang sedang aktif")
async def heartbeat(
    session_id: str = Query(..., description="session_id string (bukan record ID)"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    session = await _svc(db).heartbeat(session_id)
    return success_response("last_activity diperbarui", data=_fmt(session))


# ─── POST /user-sessions/cleanup-expired ─────────────────────────────────────
@router.post("/cleanup-expired", summary="Tandai semua sesi kadaluarsa (expires_at < NOW())")
async def cleanup_expired_sessions(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_UPDATE)),
):
    count = await _svc(db).cleanup_expired()
    return success_response(f"{count} sesi kadaluarsa berhasil dibersihkan", data={"cleaned": count})


# ─── GET /user-sessions/by-session/{session_id} ──────────────────────────────
@router.get("/by-session/{session_id}", summary="Cari sesi berdasarkan session_id string")
async def get_by_session_id(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    session = await _svc(db).get_by_session_id(session_id)
    return success_response("Berhasil", data=_fmt(session))


# ─── GET /user-sessions/records/{session_record_id} ──────────────────────────
@router.get("/records/{session_record_id}", summary="Detail sesi berdasarkan record ID (PK)")
async def get_session_record(
    session_record_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    session = await _svc(db).get_by_record_id(session_record_id)
    return success_response("Berhasil", data=_fmt(session))


# ─── POST /user-sessions/{session_id}/force-logout ───────────────────────────
@router.post("/{session_id}/force-logout", summary="Admin: paksa logout sesi manapun")
async def force_logout(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_UPDATE)),
):
    session = await _svc(db).force_logout(session_id)
    return success_response("Sesi berhasil di-force-logout", data=_fmt(session))


# ─── GET /user-sessions/ ─────────────────────────────────────────────────────
@router.get("", summary="Daftar semua sesi (paginated)")
async def list_sessions(
    q: CommonQueryParams = Depends(),
    user_id: Optional[int] = Query(None, description="Filter berdasarkan user_id"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_READ)),
):
    items, total = await _svc(db).get_paged(q.page, q.limit, user_id)
    return paginated_response(
        "Berhasil", items=[_fmt(s) for s in items],
        page=q.page, limit=q.limit, total=total,
    )


# ─── POST /user-sessions/ ────────────────────────────────────────────────────
@router.post("", status_code=HC.CREATED, summary="Buat sesi secara manual (admin / sistem)")
async def create_session(
    body: UserSessionCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.USER_SESSIONS_CREATE)),
):
    session = await _svc(db).create_session(body.model_dump())
    return success_response(SuccessMessages.CREATED.format("Sesi"), data=_fmt(session))
