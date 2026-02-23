from typing import Optional, List, Tuple
from repositories.unit_repository import UnitRepository
from models.unit import Unit
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC


class UnitService(BaseService[Unit, UnitRepository]):
    def __init__(self, repo: UnitRepository):
        super().__init__(repo)

    async def create_unit(self, id_unit: int, nama_unit: str, status: str = "Aktif") -> Unit:
        existing = await self.repo.get_by_id(id_unit)
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_EXISTS.format("Unit"))
        return await self.repo.create({"id_unit": id_unit, "nama_unit": nama_unit, "status": status})

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

    async def delete_unit(self, id_unit: int) -> bool:
        unit = await self.repo.get_by_id(id_unit)
        if not unit:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Unit"))
        await self.repo.db.delete(unit)
        await self.repo.db.commit()
        return True

    async def get_paged(self, page: int, limit: int) -> Tuple[List[Unit], int]:
        from sqlalchemy import select, func
        skip = (page - 1) * limit
        db = self.repo.db
        from models.unit import Unit as UnitModel
        from sqlalchemy import select, func
        total = (await db.execute(select(func.count()).select_from(UnitModel))).scalar() or 0
        result = await db.execute(select(UnitModel).offset(skip).limit(limit))
        return list(result.scalars().all()), total
