from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from repositories.base import BaseRepository
from models.user import User
from models.user_role import UserRole
from models.role import Role
from models.pegawai import Pegawai


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    def _with_all(self):
        """selectinload options yang memuat roles, permissions, dan pegawai sekaligus."""
        return (
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.pegawai),
        )

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(*self._with_all())
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_roles(self, id: int) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(*self._with_all())
            .where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_pegawai_id(self, id_pegawai: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id_pegawai == id_pegawai))
        return result.scalar_one_or_none()

    async def sync_roles(self, user_id: int, role_ids: List[int]) -> None:
        await self.db.execute(delete(UserRole).where(UserRole.user_id == user_id))
        for role_id in role_ids:
            self.db.add(UserRole(user_id=user_id, role_id=role_id))
        await self.db.commit()
