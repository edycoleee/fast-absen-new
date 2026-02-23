from typing import Optional, List, Tuple
from repositories.pegawai_repository import PegawaiRepository
from models.pegawai import Pegawai
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC


class PegawaiService(BaseService[Pegawai, PegawaiRepository]):
    def __init__(self, repo: PegawaiRepository):
        super().__init__(repo)

    async def get_by_id(self, id_pegawai: str) -> Optional[Pegawai]:
        return await self.repo.get_by_id(id_pegawai)

    async def get_paged(self, page: int, limit: int, search: Optional[str] = None, unit_id: Optional[int] = None) -> Tuple[List[Pegawai], int]:
        skip = (page - 1) * limit
        return await self.repo.get_all_paged(skip, limit, search, unit_id)

    async def create_pegawai(self, data: dict) -> Pegawai:
        existing = await self.repo.get_by_id(data["id_pegawai"])
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_EXISTS.format("ID Pegawai"))
        return await self.repo.create(data)

    async def update_pegawai(self, id_pegawai: str, data: dict) -> Pegawai:
        pegawai = await self.repo.get_by_id(id_pegawai)
        if not pegawai:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Pegawai"))
        clean = {k: v for k, v in data.items() if v is not None}
        for k, v in clean.items():
            setattr(pegawai, k, v)
        await self.repo.db.commit()
        await self.repo.db.refresh(pegawai)
        return pegawai

    async def delete_pegawai(self, id_pegawai: str) -> bool:
        pegawai = await self.repo.get_by_id(id_pegawai)
        if not pegawai:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Pegawai"))
        await self.repo.db.delete(pegawai)
        await self.repo.db.commit()
        return True
