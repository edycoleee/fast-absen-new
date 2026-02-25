from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from repositories.base import BaseRepository
from models.role import Role
from models.role_permission import RolePermission
from models.permission import Permission
from models.user_role import UserRole


class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_id_with_permissions(self, id: int) -> Optional[Role]:
        result = await self.db.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Role]:
        result = await self.db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_by_names(self, names: List[str]) -> List[Role]:
        """Return roles whose name is in the given list."""
        if not names:
            return []
        result = await self.db.execute(select(Role).where(Role.name.in_(names)))
        return list(result.scalars().all())

    async def get_all_with_permissions(self) -> List[Role]:
        result = await self.db.execute(
            select(Role).options(selectinload(Role.permissions))
        )
        return list(result.scalars().unique().all())

    async def count_users(self, role_id: int) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
        )
        return result.scalar() or 0

    async def sync_permissions(self, role_id: int, permission_ids: List[int]) -> None:
        await self.db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        for perm_id in permission_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=perm_id))
        await self.db.commit()
