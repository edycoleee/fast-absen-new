from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Date, Text, DateTime, ForeignKey, func
from config.database import Base


class Pegawai(Base):
    __tablename__ = "pegawai"

    id_pegawai:    Mapped[str]              = mapped_column(String(20), primary_key=True)
    nip:           Mapped[Optional[str]]    = mapped_column(String(50))
    nama:          Mapped[str]              = mapped_column(String(255), nullable=False)
    id_unit:       Mapped[Optional[int]]    = mapped_column(Integer, ForeignKey("unit.id_unit", ondelete="SET NULL"))
    kepala_id_unit:Mapped[Optional[int]]    = mapped_column(Integer, ForeignKey("unit.id_unit", ondelete="SET NULL"))
    jenis_kelamin: Mapped[Optional[str]]    = mapped_column(String(10))
    tempat_lahir:  Mapped[Optional[str]]    = mapped_column(String(100))
    tanggal_lahir: Mapped[Optional[date]]   = mapped_column(Date)
    alamat:        Mapped[Optional[str]]    = mapped_column(Text)
    status:        Mapped[str]              = mapped_column(String(20), default="Aktif", nullable=False)
    foto:          Mapped[Optional[str]]    = mapped_column(String(255))
    created_at:    Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime]         = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    unit        = relationship("Unit", foreign_keys=[id_unit])
    unit_kepala = relationship("Unit", foreign_keys=[kepala_id_unit])
    user        = relationship("User", back_populates="pegawai", uselist=False)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update_from_dict(self, data: dict):
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)
