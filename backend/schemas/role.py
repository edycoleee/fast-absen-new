from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from schemas.base import BaseSchema, BaseResponseSchema


class PermissionOut(BaseSchema):
    id: int
    name: str
    description: Optional[str] = None


class RoleCreate(BaseSchema):
    name: str
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = []


class RoleUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class RoleOut(BaseResponseSchema):
    name: str
    description: Optional[str] = None
    permissions: List[PermissionOut] = []
