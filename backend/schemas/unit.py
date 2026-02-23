from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from schemas.base import BaseSchema


class UnitCreate(BaseSchema):
    id_unit: int
    nama_unit: str
    status: str = "Aktif"


class UnitUpdate(BaseSchema):
    nama_unit: Optional[str] = None
    status: Optional[str] = None


class UnitOut(BaseSchema):
    id_unit: int
    nama_unit: str
    status: str
    created_at: datetime
    updated_at: datetime
