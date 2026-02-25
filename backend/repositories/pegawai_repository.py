from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import Optional, List, Tuple
from repositories.base import BaseRepository
from models.pegawai import Pegawai
from models.absensi import Absensi
from models.user import User
from models.face_embedding import FaceEmbedding


class PegawaiRepository(BaseRepository[Pegawai]):
    def __init__(self, db: AsyncSession):
        super().__init__(Pegawai, db)

    async def get_by_id(self, id: str) -> Optional[Pegawai]:
        result = await self.db.execute(select(Pegawai).where(Pegawai.id_pegawai == id))
        return result.scalar_one_or_none()

    async def get_by_nip(self, nip: str) -> Optional[Pegawai]:
        result = await self.db.execute(select(Pegawai).where(Pegawai.nip == nip))
        return result.scalar_one_or_none()

    async def get_all_paged(self, skip: int, limit: int, search: Optional[str] = None, unit_id: Optional[int] = None) -> Tuple[List[Pegawai], int]:
        query = select(Pegawai).where(Pegawai.is_active == True)
        count_q = select(func.count()).select_from(Pegawai).where(Pegawai.is_active == True)
        if search:
            cond = or_(Pegawai.nama.ilike(f"%{search}%"), Pegawai.nip.ilike(f"%{search}%"))
            query = query.where(cond)
            count_q = count_q.where(cond)
        if unit_id:
            query = query.where(Pegawai.id_unit == unit_id)
            count_q = count_q.where(Pegawai.id_unit == unit_id)
        total = (await self.db.execute(count_q)).scalar() or 0
        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def count_absensi(self, id_pegawai: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Absensi).where(Absensi.id_pegawai == id_pegawai)
        )
        return result.scalar() or 0

    async def count_users(self, id_pegawai: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.id_pegawai == id_pegawai)
        )
        return result.scalar() or 0

    async def count_embeddings(self, id_pegawai: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(FaceEmbedding)
            .join(User, FaceEmbedding.user_id == User.id)
            .where(User.id_pegawai == id_pegawai)
        )
        return result.scalar() or 0
