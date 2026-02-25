from typing import Optional, List, Tuple
from datetime import datetime, timezone
from repositories.user_session_repository import UserSessionRepository
from models.user_session import UserSession
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC, LoginStatus


class UserSessionService(BaseService[UserSession, UserSessionRepository]):
    def __init__(self, repo: UserSessionRepository):
        super().__init__(repo)

    # ─── LIST / PAGED ────────────────────────────────────────────────────────

    async def get_paged(
        self, page: int, limit: int, user_id: Optional[int] = None
    ) -> Tuple[List[UserSession], int]:
        skip = (page - 1) * limit
        return await self.repo.get_paged(skip, limit, user_id)

    async def get_active(
        self, page: int, limit: int, user_id: Optional[int] = None
    ) -> Tuple[List[UserSession], int]:
        """Only sessions where logout_at IS NULL."""
        skip = (page - 1) * limit
        return await self.repo.get_active_paged(skip, limit, user_id)

    async def get_history(
        self, page: int, limit: int, user_id: Optional[int] = None
    ) -> Tuple[List[UserSession], int]:
        """All sessions, optionally filtered by user_id."""
        skip = (page - 1) * limit
        return await self.repo.get_paged(skip, limit, user_id)

    # ─── SINGLE RECORD ───────────────────────────────────────────────────────

    async def get_by_record_id(self, session_record_id: int) -> UserSession:
        s = await self.repo.get_by_id(session_record_id)
        if not s:
            raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Sesi"))
        return s

    async def get_by_session_id(self, session_id: str) -> UserSession:
        """Get session by the session_id string field (not PK)."""
        s = await self.repo.get_by_session_id_str(session_id)
        if not s:
            raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Sesi"))
        return s

    # ─── CREATE ──────────────────────────────────────────────────────────────

    async def create_session(self, data: dict) -> UserSession:
        """Manually create a session record (admin / system use)."""
        return await self.repo.create(data)

    # ─── STATISTICS ──────────────────────────────────────────────────────────

    async def get_statistics(self) -> dict:
        return await self.repo.get_statistics()

    # ─── FORCE-LOGOUT (admin) ─────────────────────────────────────────────────

    async def force_logout(self, session_record_id: int) -> UserSession:
        """Admin: force-terminate any session regardless of owner."""
        session = await self.repo.get_by_id(session_record_id)
        if not session:
            raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Sesi"))
        if session.logout_at is not None:
            raise HTTPException(HC.BAD_REQUEST, "Sesi sudah dilogout sebelumnya")
        session.logout_at = datetime.now(timezone.utc)
        session.login_status = LoginStatus.EXPIRED
        await self.repo.db.commit()
        await self.repo.db.refresh(session)
        return session

    # ─── LOGOUT (self) ────────────────────────────────────────────────────────

    async def logout_session(self, session_id: int, current_user_id: int) -> UserSession:
        """User logout their own session (ownership check)."""
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Sesi"))
        if session.user_id != current_user_id:
            raise HTTPException(HC.FORBIDDEN, ErrorMessages.FORBIDDEN)
        session.logout_at = datetime.now(timezone.utc)
        session.login_status = LoginStatus.EXPIRED
        await self.repo.db.commit()
        await self.repo.db.refresh(session)
        return session

    # ─── HEARTBEAT ───────────────────────────────────────────────────────────

    async def heartbeat(self, session_id: str) -> UserSession:
        """Update last_activity for the given session_id string."""
        session = await self.repo.get_by_session_id_str(session_id)
        if not session:
            raise HTTPException(HC.NOT_FOUND, ErrorMessages.NOT_FOUND.format("Sesi"))
        updated = await self.repo.update_heartbeat(session.id)
        return updated

    # ─── CLEANUP EXPIRED ─────────────────────────────────────────────────────

    async def cleanup_expired(self) -> int:
        """Mark all sessions with expires_at < NOW() and no logout_at as expired."""
        now = datetime.now(timezone.utc)
        return await self.repo.invalidate_expired(now)
