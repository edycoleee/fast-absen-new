from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, DateTime, func
from models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name:        Mapped[str]           = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None]    = mapped_column(Text)
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    permissions = relationship("Permission", secondary="role_permissions", backref="roles", lazy="selectin")
