from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, func
from models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    id_pegawai:    Mapped[Optional[str]]  = mapped_column(String(20), ForeignKey("pegawai.id_pegawai", ondelete="SET NULL"), unique=True)
    username:      Mapped[str]            = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str]            = mapped_column(Text, nullable=False)
    is_active:     Mapped[bool]           = mapped_column(Boolean, default=True)
    last_login:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at:    Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pegawai         = relationship("Pegawai", back_populates="user")
    roles           = relationship("Role", secondary="user_roles", lazy="selectin")
    face_embeddings = relationship("FaceEmbedding", back_populates="user", cascade="all, delete-orphan")

    @property
    def permissions(self) -> set[str]:
        perms: set[str] = set()
        for role in self.roles:
            for p in role.permissions:
                perms.add(p.name)
        return perms

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions

    def has_role(self, role_name: str) -> bool:
        return any(r.name == role_name for r in self.roles)

    @property
    def is_superadmin(self) -> bool:
        return self.has_role("superadmin")
