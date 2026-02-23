from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from repositories.base import BaseRepository
from models.permission import Permission


class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: AsyncSession):
        super().__init__(Permission, db)

    async def get_by_name(self, name: str) -> Optional[Permission]:
        result = await self.db.execute(select(Permission).where(Permission.name == name))
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: List[int]) -> List[Permission]:
        result = await self.db.execute(select(Permission).where(Permission.id.in_(ids)))
        return list(result.scalars().all())

    async def get_all_names(self) -> List[str]:
        result = await self.db.execute(select(Permission.name))
        return [row[0] for row in result.all()]
