from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Tuple
from repositories.base import BaseRepository
from models.unit import Unit


class UnitRepository(BaseRepository[Unit]):
    def __init__(self, db: AsyncSession):
        super().__init__(Unit, db)

    async def get_by_id(self, id: int) -> Optional[Unit]:
        result = await self.db.execute(select(Unit).where(Unit.id_unit == id))
        return result.scalar_one_or_none()

    async def get_by_nama(self, nama: str) -> Optional[Unit]:
        result = await self.db.execute(select(Unit).where(Unit.nama_unit == nama))
        return result.scalar_one_or_none()

    async def get_all_aktif(self) -> List[Unit]:
        result = await self.db.execute(select(Unit).where(Unit.status == "Aktif"))
        return list(result.scalars().all())
