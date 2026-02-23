from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, func
from config.database import Base


class Unit(Base):
    __tablename__ = "unit"

    id_unit:   Mapped[int]  = mapped_column(Integer, primary_key=True)
    nama_unit: Mapped[str]  = mapped_column(String(150), unique=True, nullable=False)
    status:    Mapped[str]  = mapped_column(String(20), default="Aktif", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def update_from_dict(self, data: dict):
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)
