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

    async def delete_pegawai(self, id_pegawai: str, force: bool = False) -> bool:
        pegawai = await self.repo.get_by_id(id_pegawai)
        if not pegawai:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Pegawai"))
        if not force:
            pegawai.is_active = False
            await self.repo.db.commit()
            return True
        counts = {
            "absensi": await self.repo.count_absensi(id_pegawai),
            "user": await self.repo.count_users(id_pegawai),
            "embedding": await self.repo.count_embeddings(id_pegawai),
        }
        blocking = {k: v for k, v in counts.items() if v > 0}
        if blocking:
            detail = ", ".join(f"{v} {k}" for k, v in blocking.items())
            raise HTTPException(status_code=HC.CONFLICT, detail=f"Tidak dapat menghapus pegawai: masih ada {detail} terhubung.")
        await self.repo.db.delete(pegawai)
        await self.repo.db.commit()
        return True

    async def import_pegawai(self, rows: list) -> dict:
        """Bulk-create pegawai from parsed Excel rows.

        Required per row: id_pegawai, nama.
        jenis_kelamin: L → MALE, P → FEMALE.
        tanggal_lahir: string YYYY-MM-DD or datetime.date.
        is_active: TRUE/1/YES → True, else False.

        Returns {'created': N, 'skipped': N, 'errors': [{'row': N, 'reason': str}]}
        """
        from datetime import date as date_type

        _GENDER_MAP = {"L": "MALE", "P": "FEMALE", "MALE": "MALE", "FEMALE": "FEMALE"}

        created = 0
        skipped = 0
        errors: list = []

        for i, row in enumerate(rows, start=2):   # row 1 = header
            id_pegawai = (row.get("id_pegawai") or "").strip()
            nama       = (row.get("nama") or "").strip()

            if not id_pegawai or not nama:
                skipped += 1
                continue

            # --- optional fields ---
            nip            = (row.get("nip") or "").strip() or None
            tempat_lahir   = (row.get("tempat_lahir") or "").strip() or None
            alamat         = (row.get("alamat") or "").strip() or None

            raw_gender     = (row.get("jenis_kelamin") or "").strip().upper()
            jenis_kelamin  = _GENDER_MAP.get(raw_gender) or None

            # tanggal_lahir: accept date obj or YYYY-MM-DD string
            raw_tgl = row.get("tanggal_lahir")
            tanggal_lahir = None
            if raw_tgl:
                if isinstance(raw_tgl, date_type):
                    tanggal_lahir = raw_tgl
                else:
                    try:
                        from datetime import datetime
                        tanggal_lahir = datetime.strptime(str(raw_tgl).strip(), "%Y-%m-%d").date()
                    except ValueError:
                        errors.append({"row": i, "id_pegawai": id_pegawai,
                                       "reason": f"Format tanggal_lahir tidak valid: '{raw_tgl}' (harus YYYY-MM-DD)"})
                        continue

            raw_unit        = (row.get("id_unit") or "").strip()
            id_unit         = int(raw_unit) if raw_unit.isdigit() else None

            raw_kepala      = (row.get("kepala_id_unit") or "").strip()
            kepala_id_unit  = int(raw_kepala) if raw_kepala.isdigit() else None

            raw_active      = str(row.get("is_active") or "TRUE").strip().upper()
            is_active       = raw_active in ("TRUE", "1", "YES", "AKTIF")

            data = {
                "id_pegawai":    id_pegawai,
                "nip":           nip,
                "nama":          nama,
                "jenis_kelamin": jenis_kelamin,
                "tempat_lahir":  tempat_lahir,
                "tanggal_lahir": tanggal_lahir,
                "alamat":        alamat,
                "id_unit":       id_unit,
                "kepala_id_unit":kepala_id_unit,
                "is_active":     is_active,
            }

            try:
                await self.create_pegawai(data)
                created += 1
            except Exception as exc:
                detail = getattr(exc, "detail", str(exc))
                errors.append({"row": i, "id_pegawai": id_pegawai, "reason": detail})

        return {"created": created, "skipped": skipped, "errors": errors}
