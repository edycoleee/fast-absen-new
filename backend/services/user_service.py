from typing import Optional, List, Tuple
from repositories.user_repository import UserRepository
from models.user import User
from services.base import BaseService
from utils.security import hash_password
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC


class UserService(BaseService[User, UserRepository]):
    def __init__(self, repo: UserRepository):
        super().__init__(repo)

    async def get_by_id_with_roles(self, user_id: int) -> Optional[User]:
        return await self.repo.get_by_id_with_roles(user_id)

    async def create_user(self, data: dict, role_ids: List[int]) -> User:
        existing = await self.repo.get_by_username(data["username"])
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_EXISTS.format("Username"))
        data["password_hash"] = hash_password(data.pop("password"))
        user = await self.repo.create(data)
        if role_ids:
            await self.repo.sync_roles(user.id, role_ids)
        return await self.repo.get_by_id_with_roles(user.id)

    async def update_user(self, user_id: int, data: dict, role_ids: Optional[List[int]]) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("User"))
        if "password" in data and data["password"]:
            data["password_hash"] = hash_password(data.pop("password"))
        clean = {k: v for k, v in data.items() if v is not None}
        for k, v in clean.items():
            setattr(user, k, v)
        await self.repo.db.commit()
        if role_ids is not None:
            await self.repo.sync_roles(user_id, role_ids)
        return await self.repo.get_by_id_with_roles(user_id)

    async def delete_user(self, user_id: int, force: bool = False) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("User"))
        if not force:
            user.is_active = False
            await self.repo.db.commit()
            return True
        active = await self.repo.count_active_sessions(user_id)
        if active > 0:
            raise HTTPException(status_code=HC.CONFLICT, detail=f"Tidak dapat menghapus user: masih ada {active} sesi aktif.")
        return await self.repo.delete(user_id)

    async def import_users(self, rows: list) -> dict:
        """Bulk-create users from parsed Excel rows.

        Each row dict must have:
          username (str, required)
          password (str, optional — defaults to 'Absen@1234')
          id_pegawai (str, optional)
          role_names (str, optional — comma-separated role names)
          is_active (bool, optional — defaults to True)

        Returns {'created': N, 'skipped': N, 'errors': [{'row': N, 'reason': str}]}
        """
        from repositories.role_repository import RoleRepository
        role_repo = RoleRepository(self.repo.db)

        created = 0
        skipped = 0
        errors: list = []

        for i, row in enumerate(rows, start=2):   # row 1 = header
            username = (row.get("username") or "").strip()
            if not username:
                skipped += 1
                continue

            password = (row.get("password") or "").strip() or "Absen@1234"
            id_pegawai = (row.get("id_pegawai") or "").strip() or None
            is_active_raw = str(row.get("is_active") or "TRUE").strip().upper()
            is_active = is_active_raw in ("TRUE", "1", "YES", "AKTIF")

            # resolve role_names → role_ids
            raw_roles = (row.get("role_names") or "").strip()
            role_names = [r.strip() for r in raw_roles.split(",") if r.strip()] if raw_roles else []
            roles = await role_repo.get_by_names(role_names) if role_names else []
            role_ids = [r.id for r in roles]

            try:
                user = await self.create_user(
                    {"username": username, "password": password, "id_pegawai": id_pegawai, "is_active": is_active},
                    role_ids,
                )
                created += 1
            except Exception as exc:
                detail = getattr(exc, "detail", str(exc))
                errors.append({"row": i, "username": username, "reason": detail})

        return {"created": created, "skipped": skipped, "errors": errors}
