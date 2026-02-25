from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from schemas.base import BaseSchema
from utils.constants import Gender


class PegawaiCreate(BaseSchema):
    id_pegawai: str
    nip: Optional[str] = None
    nama: str
    id_unit: Optional[int] = None
    kepala_id_unit: Optional[int] = None
    jenis_kelamin: Optional[Gender] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[date] = None
    alamat: Optional[str] = None
    is_active: bool = True


class PegawaiUpdate(BaseSchema):
    nip: Optional[str] = None
    nama: Optional[str] = None
    id_unit: Optional[int] = None
    kepala_id_unit: Optional[int] = None
    jenis_kelamin: Optional[Gender] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[date] = None
    alamat: Optional[str] = None
    is_active: Optional[bool] = None
    foto: Optional[str] = None


class PegawaiOut(BaseSchema):
    id_pegawai: str
    nip: Optional[str] = None
    nama: str
    id_unit: Optional[int] = None
    kepala_id_unit: Optional[int] = None
    jenis_kelamin: Optional[Gender] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[date] = None
    alamat: Optional[str] = None
    is_active: bool
    foto: Optional[str] = None
    created_at: datetime
    updated_at: datetime
