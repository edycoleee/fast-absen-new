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

    async def get_statistics(
        self,
        target_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        id_unit: Optional[int] = None,
    ) -> dict:
        """Return per-status counts across all pegawai (admin statistics view)."""
        filters = []
        if target_date:
            filters.append(Absensi.tanggal == target_date)
        else:
            if start_date:
                filters.append(Absensi.tanggal >= start_date)
            if end_date:
                filters.append(Absensi.tanggal <= end_date)

        base_q = select(Absensi)
        if filters:
            base_q = base_q.where(and_(*filters))

        # id_unit filter via join to pegawai
        if id_unit:
            from models.pegawai import Pegawai
            from sqlalchemy.orm import aliased
            pg = aliased(Pegawai)
            base_q = base_q.join(pg, Absensi.id_pegawai == pg.id_pegawai).where(
                (pg.id_unit == id_unit) | (pg.kepala_id_unit == id_unit)
            )

        result = await self.db.execute(base_q)
        records = result.scalars().all()

        breakdown: dict = {}
        for a in records:
            breakdown[a.status] = breakdown.get(a.status, 0) + 1

        return {
            "date":       str(target_date) if target_date else None,
            "start_date": str(start_date)  if start_date  else None,
            "end_date":   str(end_date)    if end_date    else None,
            "id_unit":    id_unit,
            "total":      len(records),
            "breakdown":  breakdown,
        }

    async def get_history(
        self, id_pegawai: str, skip: int, limit: int,
        start_date: Optional[date] = None, end_date: Optional[date] = None,
    ) -> Tuple[List[Absensi], int]:
        filters = [Absensi.id_pegawai == id_pegawai]
        if start_date:
            filters.append(Absensi.tanggal >= start_date)
        if end_date:
            filters.append(Absensi.tanggal <= end_date)
        query   = select(Absensi).where(and_(*filters)).order_by(Absensi.tanggal.desc())
        count_q = select(func.count()).select_from(Absensi).where(and_(*filters))
        total   = (await self.db.execute(count_q)).scalar() or 0
        result  = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def get_by_date_range_pegawai(
        self, id_pegawai: str,
        start_date: Optional[date] = None, end_date: Optional[date] = None,
    ) -> List[Absensi]:
        filters = [Absensi.id_pegawai == id_pegawai]
        if start_date:
            filters.append(Absensi.tanggal >= start_date)
        if end_date:
            filters.append(Absensi.tanggal <= end_date)
        result = await self.db.execute(select(Absensi).where(and_(*filters)))
        return list(result.scalars().all())
