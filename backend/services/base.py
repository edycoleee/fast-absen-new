from typing import TypeVar, Generic, Optional, List, Tuple, Dict, Any
from repositories.base import BaseRepository

ModelType = TypeVar("ModelType")
RepoType = TypeVar("RepoType")


class BaseService(Generic[ModelType, RepoType]):
    def __init__(self, repository: RepoType):
        self.repo: RepoType = repository

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        return await self.repo.get_by_id(id)

    async def get_all(
        self,
        page: int = 1,
        limit: int = 10,
        order_by: Optional[str] = None,
        order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ModelType], int]:
        skip = (page - 1) * limit
        return await self.repo.get_all(
            skip=skip, limit=limit, order_by=order_by, order=order, filters=filters
        )

    async def create(self, data: Dict[str, Any]) -> ModelType:
        return await self.repo.create(data)

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[ModelType]:
        return await self.repo.update(id, data)

    async def delete(self, id: Any) -> bool:
        return await self.repo.delete(id)
