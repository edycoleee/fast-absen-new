from typing import Optional, List, Tuple
from repositories.unit_repository import UnitRepository
from models.unit import Unit
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC


class UnitService(BaseService[Unit, UnitRepository]):
    def __init__(self, repo: UnitRepository):
        super().__init__(repo)

    async def create_unit(self, id_unit: int, nama_unit: str, is_active: bool = True) -> Unit:
        existing = await self.repo.get_by_id(id_unit)
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_EXISTS.format("Unit"))
        return await self.repo.create({"id_unit": id_unit, "nama_unit": nama_unit, "is_active": is_active})

    async def get_unit(self, id_unit: int) -> Unit:
        unit = await self.repo.get_by_id(id_unit)
        if not unit:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Unit"))
        return unit

    async def update_unit(self, id_unit: int, data: dict) -> Unit:
        unit = await self.repo.get_by_id(id_unit)
        if not unit:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Unit"))
        clean = {k: v for k, v in data.items() if v is not None}
        for k, v in clean.items():
            setattr(unit, k, v)
        await self.repo.db.commit()
        await self.repo.db.refresh(unit)
        return unit

    async def delete_unit(self, id_unit: int, force: bool = False) -> bool:
        """
        Hapus unit.

        - force=False (default): soft delete — set status = 'INACTIVE'.
          Unit masih ada di DB; GET /unit tidak menampilkannya karena filter ACTIVE.
        - force=True: hard delete permanen.
          Hanya diizinkan jika tidak ada pegawai yang masih terhubung.
          Jika masih ada → 409 Conflict.
        """
        unit = await self.repo.get_by_id(id_unit)
        if not unit:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Unit"))

        if not force:
            # Soft delete: cukup nonaktifkan
            unit.is_active = False
            await self.repo.db.commit()
            return True

        # Hard delete: validasi tidak ada pegawai yang masih terhubung
        linked = await self.repo.count_pegawai(id_unit)
        if linked > 0:
            raise HTTPException(
                status_code=HC.CONFLICT,
                detail=f"Tidak dapat menghapus unit karena masih ada {linked} pegawai terhubung. "
                       "Pindahkan pegawai terlebih dahulu.",
            )
        await self.repo.db.delete(unit)
        await self.repo.db.commit()
        return True

    async def get_paged(self, page: int, limit: int) -> Tuple[List[Unit], int]:
        """Hanya kembalikan unit berstatus 'ACTIVE'."""
        from sqlalchemy import select, func
        from models.unit import Unit as UnitModel
        skip = (page - 1) * limit
        db = self.repo.db
        base_q = select(UnitModel).where(UnitModel.is_active == True)
        total = (await db.execute(
            select(func.count()).select_from(UnitModel).where(UnitModel.is_active == True)
        )).scalar() or 0
        result = await db.execute(base_q.offset(skip).limit(limit))
        return list(result.scalars().all()), total
