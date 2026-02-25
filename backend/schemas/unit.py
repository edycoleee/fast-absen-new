from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from schemas.base import BaseSchema


class UnitCreate(BaseSchema):
    id_unit: int
    nama_unit: str
    is_active: bool = True


class UnitUpdate(BaseSchema):
    nama_unit: Optional[str] = None
    is_active: Optional[bool] = None


class UnitOut(BaseSchema):
    id_unit: int
    nama_unit: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
