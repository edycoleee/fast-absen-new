from typing import List, Optional
from repositories.permission_repository import PermissionRepository
from models.permission import Permission
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC


class PermissionService(BaseService[Permission, PermissionRepository]):
    def __init__(self, repo: PermissionRepository):
        super().__init__(repo)

    async def create_permission(self, name: str, description: Optional[str]) -> Permission:
        existing = await self.repo.get_by_name(name)
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_EXISTS.format("Permission"))
        return await self.repo.create({"name": name, "description": description})

    async def delete_permission(self, perm_id: int) -> bool:
        perm = await self.repo.get_by_id(perm_id)
        if not perm:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Permission"))
        count = await self.repo.count_roles(perm_id)
        if count > 0:
            raise HTTPException(status_code=HC.CONFLICT, detail=f"Tidak dapat menghapus permission: masih digunakan oleh {count} role.")
        return await self.repo.delete(perm_id)
