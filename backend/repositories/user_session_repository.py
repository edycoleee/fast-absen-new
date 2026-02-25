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

    async def get_by_session_id_str(self, session_id: str) -> Optional[UserSession]:
        """Get session by session_id string field (not the PK)."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_paged(self, skip: int, limit: int, user_id: Optional[int] = None) -> Tuple[List[UserSession], int]:
        """Paginated active sessions (logout_at IS NULL)."""
        base_filter = UserSession.logout_at == None
        query = select(UserSession).where(base_filter).order_by(UserSession.login_at.desc())
        count_q = select(func.count()).select_from(UserSession).where(base_filter)
        if user_id:
            query = query.where(UserSession.user_id == user_id)
            count_q = count_q.where(UserSession.user_id == user_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def update_heartbeat(self, session_record_id: int) -> Optional[UserSession]:
        """Update last_activity to NOW for the given record PK."""
        from sqlalchemy import update as sa_update
        from datetime import timezone
        now = datetime.now(timezone.utc)
        await self.db.execute(
            sa_update(UserSession)
            .where(UserSession.id == session_record_id)
            .values(last_activity=now)
        )
        await self.db.commit()
        return await self.get_by_id(session_record_id)

    async def get_statistics(self) -> dict:
        """Aggregate session statistics."""
        from datetime import date, timezone
        today = date.today()
        total = (await self.db.execute(select(func.count()).select_from(UserSession))).scalar() or 0
        active = (await self.db.execute(
            select(func.count()).select_from(UserSession).where(UserSession.logout_at == None)
        )).scalar() or 0
        today_logins = (await self.db.execute(
            select(func.count()).select_from(UserSession).where(
                func.date(UserSession.login_at) == today
            )
        )).scalar() or 0
        # by device_type
        from sqlalchemy import case, literal_column
        device_rows = (await self.db.execute(
            select(UserSession.device_type, func.count().label("cnt"))
            .where(UserSession.device_type != None)
            .group_by(UserSession.device_type)
        )).fetchall()
        by_device = {row[0]: row[1] for row in device_rows}
        # by login_method
        method_rows = (await self.db.execute(
            select(UserSession.login_method, func.count().label("cnt"))
            .group_by(UserSession.login_method)
        )).fetchall()
        by_method = {row[0]: row[1] for row in method_rows}
        return {
            "total_sessions": total,
            "active_sessions": active,
            "today_logins": today_logins,
            "by_device": by_device,
            "by_login_method": by_method,
        }
