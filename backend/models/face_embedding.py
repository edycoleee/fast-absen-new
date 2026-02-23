from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Boolean, Float, String, DateTime, ForeignKey, func
from pgvector.sqlalchemy import Vector
from models.base import BaseModel


class FaceEmbedding(BaseModel):
    __tablename__ = "face_embeddings"

    user_id:       Mapped[int]           = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    embedding:     Mapped[list]          = mapped_column(Vector(512), nullable=False)
    image_path:    Mapped[Optional[str]] = mapped_column(String(500))
    quality_score: Mapped[Optional[float]] = mapped_column(Float)
    is_active:     Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="face_embeddings")
