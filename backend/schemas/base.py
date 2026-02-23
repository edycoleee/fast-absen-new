from pydantic import BaseModel as PydanticBase, ConfigDict
from datetime import datetime
from typing import Optional, Generic, TypeVar, List
from fastapi import Query

T = TypeVar("T")


class BaseSchema(PydanticBase):
    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(BaseSchema):
    id: int
    created_at: datetime
    updated_at: datetime


class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(10, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.limit = limit
        self.offset = (page - 1) * limit


class SearchParams:
    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search keyword"),
        sort_by: Optional[str] = Query(None, description="Sort field"),
        order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    ):
        self.search = search
        self.sort_by = sort_by
        self.order = order
