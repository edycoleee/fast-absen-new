from typing import Optional, List, Tuple
from repositories.user_session_repository import UserSessionRepository
from models.user_session import UserSession
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC, LoginStatus


class UserSessionService(BaseService[UserSession, UserSessionRepository]):
    def __init__(self, repo: UserSessionRepository):
        super().__init__(repo)

    async def get_paged(self, page: int, limit: int, user_id: Optional[int] = None) -> Tuple[List[UserSession], int]:
        skip = (page - 1) * limit
        return await self.repo.get_paged(skip, limit, user_id)

    async def logout_session(self, session_id: int, current_user_id: int) -> UserSession:
        from datetime import datetime, timezone
        session = await self.repo.get_by_id(session_id)
        if not session:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Sesi"))
        if session.user_id != current_user_id:
            raise HTTPException(status_code=HC.FORBIDDEN, detail=ErrorMessages.FORBIDDEN)
        session.logout_at = datetime.now(timezone.utc)
        session.login_status = LoginStatus.EXPIRED
        await self.repo.db.commit()
        await self.repo.db.refresh(session)
        return session
