from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from schemas.base import BaseSchema, BaseResponseSchema


class CheckInRequest(BaseSchema):
    keterangan: Optional[str] = None
    face_image_b64: Optional[str] = None


class CheckOutRequest(BaseSchema):
    keterangan: Optional[str] = None
    face_image_b64: Optional[str] = None


class AbsensiCreate(BaseSchema):
    id_pegawai: str
    tanggal: date
    status: str = "PRESENT"
    keterangan: Optional[str] = None
    jam_masuk: Optional[datetime] = None
    jam_keluar: Optional[datetime] = None


class AbsensiUpdate(BaseSchema):
    status: Optional[str] = None
    keterangan: Optional[str] = None
    jam_masuk: Optional[datetime] = None
    jam_keluar: Optional[datetime] = None
    dokumen_pendukung: Optional[str] = None


class AbsensiOut(BaseResponseSchema):
    id_pegawai: str
    tanggal: date
    jam_masuk: Optional[datetime] = None
    jam_keluar: Optional[datetime] = None
    face_verified_masuk: bool
    face_verified_keluar: bool
    face_similarity_masuk: Optional[float] = None
    face_similarity_keluar: Optional[float] = None
    status: str
    keterangan: Optional[str] = None
    dokumen_pendukung: Optional[str] = None
    ip_address: Optional[str] = None
