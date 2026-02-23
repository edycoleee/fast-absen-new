from typing import TypeVar, Generic, Type, Optional, List, Tuple, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, asc, desc
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        order_by: Optional[str] = None,
        order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[ModelType], int]:
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)
                    count_query = count_query.where(getattr(self.model, field) == value)

        # soft delete filter
        if hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)
            count_query = count_query.where(self.model.is_deleted == False)

        if order_by and hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            query = query.order_by(asc(col) if order == "asc" else desc(col))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def update(self, id: Any, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        obj = await self.get_by_id(id)
        if not obj:
            return None
        for field, value in obj_in.items():
            if hasattr(obj, field) and value is not None:
                setattr(obj, field, value)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: Any) -> bool:
        obj = await self.get_by_id(id)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.commit()
        return True

    async def soft_delete(self, id: Any) -> Optional[ModelType]:
        obj = await self.get_by_id(id)
        if not obj or not hasattr(obj, "soft_delete"):
            return None
        obj.soft_delete()
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        query = select(func.count()).select_from(self.model)
        if hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def exists(self, filters: Dict[str, Any]) -> bool:
        return await self.count(filters) > 0

    async def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        if not hasattr(self.model, field):
            return None
        result = await self.db.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def get_by_fields(self, filters: Dict[str, Any]) -> Optional[ModelType]:
        query = select(self.model)
        for field, value in filters.items():
            if hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search(
        self,
        keyword: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[ModelType], int]:
        conditions = [
            getattr(self.model, f).ilike(f"%{keyword}%")
            for f in search_fields
            if hasattr(self.model, f)
        ]
        if not conditions:
            return [], 0
        query = select(self.model).where(or_(*conditions))
        count_query = select(func.count()).select_from(self.model).where(or_(*conditions))
        if hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)
            count_query = count_query.where(self.model.is_deleted == False)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
