from typing import Optional, List, Tuple
from repositories.role_repository import RoleRepository
from models.role import Role
from services.base import BaseService
from fastapi import HTTPException
from utils.constants import ErrorMessages, HTTPStatus as HC


class RoleService(BaseService[Role, RoleRepository]):
    def __init__(self, repo: RoleRepository):
        super().__init__(repo)

    async def get_all_with_permissions(self) -> List[Role]:
        return await self.repo.get_all_with_permissions()

    async def get_role(self, role_id: int) -> Role:
        role = await self.repo.get_by_id_with_permissions(role_id)
        if not role:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Role"))
        return role

    async def create_role(self, name: str, description: Optional[str], permission_ids: List[int]) -> Role:
        existing = await self.repo.get_by_name(name)
        if existing:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=ErrorMessages.ALREADY_EXISTS.format("Role"))
        role = await self.repo.create({"name": name, "description": description})
        if permission_ids:
            await self.repo.sync_permissions(role.id, permission_ids)
        return await self.repo.get_by_id_with_permissions(role.id)

    async def update_role(self, role_id: int, data: dict, permission_ids: Optional[List[int]]) -> Role:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Role"))
        clean = {k: v for k, v in data.items() if v is not None}
        await self.repo.update(role_id, clean)
        if permission_ids is not None:
            await self.repo.sync_permissions(role_id, permission_ids)
        return await self.repo.get_by_id_with_permissions(role_id)

    async def delete_role(self, role_id: int) -> bool:
        role = await self.repo.get_by_id(role_id)
        if not role:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Role"))
        count = await self.repo.count_users(role_id)
        if count > 0:
            raise HTTPException(status_code=HC.CONFLICT, detail=f"Tidak dapat menghapus role: masih ada {count} user menggunakan role ini.")
        return await self.repo.delete(role_id)
