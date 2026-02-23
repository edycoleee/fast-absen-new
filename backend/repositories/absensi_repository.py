from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List, Tuple
from datetime import date
from repositories.base import BaseRepository
from models.absensi import Absensi


class AbsensiRepository(BaseRepository[Absensi]):
    def __init__(self, db: AsyncSession):
        super().__init__(Absensi, db)

    async def get_today(self, id_pegawai: str, today: date) -> Optional[Absensi]:
        result = await self.db.execute(
            select(Absensi).where(
                and_(Absensi.id_pegawai == id_pegawai, Absensi.tanggal == today)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_pegawai(self, id_pegawai: str, skip: int, limit: int) -> Tuple[List[Absensi], int]:
        query = select(Absensi).where(Absensi.id_pegawai == id_pegawai).order_by(Absensi.tanggal.desc())
        count_q = select(func.count()).select_from(Absensi).where(Absensi.id_pegawai == id_pegawai)
        total = (await self.db.execute(count_q)).scalar() or 0
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def get_by_date_range(self, start: date, end: date, id_unit: Optional[int] = None) -> List[Absensi]:
        query = select(Absensi).where(and_(Absensi.tanggal >= start, Absensi.tanggal <= end))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_status_today(self, today: date, status: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Absensi).where(
                and_(Absensi.tanggal == today, Absensi.status == status)
            )
        )
        return result.scalar() or 0
