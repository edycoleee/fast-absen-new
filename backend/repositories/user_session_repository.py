from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update
from typing import Optional, List, Tuple
from datetime import datetime
from repositories.base import BaseRepository
from models.user_session import UserSession


class UserSessionRepository(BaseRepository[UserSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserSession, db)

    async def get_by_token(self, token: str) -> Optional[UserSession]:
        result = await self.db.execute(select(UserSession).where(UserSession.token == token))
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> List[UserSession]:
        result = await self.db.execute(
            select(UserSession).where(
                and_(UserSession.user_id == user_id, UserSession.login_status == "success", UserSession.logout_at == None)
            )
        )
        return list(result.scalars().all())

    async def get_paged(self, skip: int, limit: int, user_id: Optional[int] = None) -> Tuple[List[UserSession], int]:
        query = select(UserSession).order_by(UserSession.login_at.desc())
        count_q = select(func.count()).select_from(UserSession)
        if user_id:
            query = query.where(UserSession.user_id == user_id)
            count_q = count_q.where(UserSession.user_id == user_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def invalidate_expired(self, now: datetime) -> int:
        result = await self.db.execute(
            update(UserSession)
            .where(and_(UserSession.expires_at < now, UserSession.logout_at == None))
            .values(logout_at=now, login_status="expired")
        )
        await self.db.commit()
        return result.rowcount
