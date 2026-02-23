from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from schemas.base import BaseSchema, BaseResponseSchema
from schemas.role import RoleOut


class UserCreate(BaseSchema):
    id_pegawai: Optional[str] = None
    username: str
    password: str
    role_ids: Optional[List[int]] = []


class UserUpdate(BaseSchema):
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class UserOut(BaseResponseSchema):
    id_pegawai: Optional[str] = None
    username: str
    is_active: bool


class UserWithRoles(UserOut):
    roles: List[RoleOut] = []
    permissions: List[str] = []
