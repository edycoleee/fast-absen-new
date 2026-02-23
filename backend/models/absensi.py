from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Date, Boolean, Float, Text, DateTime, ForeignKey, func
from models.base import BaseModel


class Absensi(BaseModel):
    __tablename__ = "absensi"

    id_pegawai:             Mapped[str]            = mapped_column(String(20), ForeignKey("pegawai.id_pegawai", ondelete="RESTRICT"), nullable=False)
    tanggal:                Mapped[date]            = mapped_column(Date, nullable=False)
    jam_masuk:              Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    jam_keluar:             Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    face_verified_masuk:    Mapped[bool]            = mapped_column(Boolean, default=False)
    face_verified_keluar:   Mapped[bool]            = mapped_column(Boolean, default=False)
    face_similarity_masuk:  Mapped[Optional[float]] = mapped_column(Float)
    face_similarity_keluar: Mapped[Optional[float]] = mapped_column(Float)
    status:                 Mapped[str]             = mapped_column(String(20), default="HADIR", nullable=False)
    keterangan:             Mapped[Optional[str]]   = mapped_column(Text)
    dokumen_pendukung:      Mapped[Optional[str]]   = mapped_column(String(255))
    ip_address:             Mapped[Optional[str]]   = mapped_column(String(45))
    created_at:             Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:             Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pegawai = relationship("Pegawai", foreign_keys=[id_pegawai])
