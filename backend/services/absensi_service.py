from datetime import date, datetime, timezone
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from repositories.absensi_repository import AbsensiRepository
from repositories.user_session_repository import UserSessionRepository
from models.absensi import Absensi
from utils.constants import ErrorMessages, AbsensiStatus, HTTPStatus as HC


class AbsensiService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AbsensiRepository(db)

    async def check_in(
        self,
        id_pegawai: str,
        ip_address: str,
        keterangan: Optional[str] = None,
        face_verified: bool = False,
        face_similarity: Optional[float] = None,
    ) -> Absensi:
        today = date.today()
        existing = await self.repo.get_today(id_pegawai, today)
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_CHECKED_IN)

        now = datetime.now(timezone.utc)
        # Simple late check: after 08:00 local time considered terlambat
        status = AbsensiStatus.PRESENT
        if now.hour >= 8 and now.minute > 0:
            status = AbsensiStatus.LATE

        absensi = Absensi(
            id_pegawai=id_pegawai,
            tanggal=today,
            jam_masuk=now,
            status=status,
            keterangan=keterangan,
            face_verified_masuk=face_verified,
            face_similarity_masuk=face_similarity,
            ip_address=ip_address,
        )
        self.db.add(absensi)
        await self.db.commit()
        await self.db.refresh(absensi)
        return absensi

    async def check_out(
        self,
        id_pegawai: str,
        keterangan: Optional[str] = None,
        face_verified: bool = False,
        face_similarity: Optional[float] = None,
    ) -> Absensi:
        today = date.today()
        absensi = await self.repo.get_today(id_pegawai, today)
        if not absensi:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.NOT_CHECKED_IN)
        if absensi.jam_keluar:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_CHECKED_IN)

        absensi.jam_keluar = datetime.now(timezone.utc)
        if face_verified:
            absensi.face_verified_keluar = True
            absensi.face_similarity_keluar = face_similarity
        if keterangan:
            absensi.keterangan = keterangan
        await self.db.commit()
        await self.db.refresh(absensi)
        return absensi

    async def get_paged(
        self, page: int, limit: int,
        id_pegawai: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[Absensi], int]:
        skip = (page - 1) * limit
        if id_pegawai:
            return await self.repo.get_by_pegawai(id_pegawai, skip, limit)
        return await self.repo.get_all(skip=skip, limit=limit)

    async def get_today(self, id_pegawai: str) -> Optional[Absensi]:
        """Return today's absensi record for a pegawai, or None."""
        return await self.repo.get_today(id_pegawai, date.today())

    async def get_history(
        self,
        id_pegawai: str,
        page: int,
        limit: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[Absensi], int]:
        """Paginated history for a single pegawai, optionally filtered by date range."""
        skip = (page - 1) * limit
        return await self.repo.get_history(id_pegawai, skip, limit, start_date, end_date)

    async def get_summary(
        self,
        id_pegawai: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Return per-status count summary for a pegawai."""
        records = await self.repo.get_by_date_range_pegawai(id_pegawai, start_date, end_date)
        summary: dict = {}
        for a in records:
            summary[a.status] = summary.get(a.status, 0) + 1
        return {
            "id_pegawai": id_pegawai,
            "start_date": str(start_date) if start_date else None,
            "end_date":   str(end_date)   if end_date   else None,
            "total":      len(records),
            "breakdown":  summary,
        }

    async def get_by_id(self, absensi_id: int) -> Optional[Absensi]:
        return await self.repo.get_by_id(absensi_id)

    async def delete_absensi(self, absensi_id: int) -> bool:
        a = await self.repo.get_by_id(absensi_id)
        if not a:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Absensi"))
        await self.db.delete(a)
        await self.db.commit()
        return True

    async def get_statistics(
        self,
        target_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        id_unit: Optional[int] = None,
    ) -> dict:
        """Admin-level statistics across all pegawai."""
        return await self.repo.get_statistics(target_date, start_date, end_date, id_unit)
