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

    async def delete_user(self, user_id: int) -> bool:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("User"))
        return await self.repo.delete(user_id)
