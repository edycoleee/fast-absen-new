from pydantic import BaseModel
from typing import Optional
from schemas.base import BaseSchema


class StatsOverview(BaseSchema):
    total_pegawai: int
    total_hadir_hari_ini: int
    total_terlambat_hari_ini: int
    total_izin_hari_ini: int
    total_sakit_hari_ini: int
    total_alpha_hari_ini: int
    total_belum_absen: int
    total_sessions_aktif: int
    persentase_kehadiran: float
