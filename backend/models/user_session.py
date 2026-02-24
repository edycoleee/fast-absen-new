from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from models.base import BaseModel


class UserSession(BaseModel):
    __tablename__ = "user_sessions"

    user_id:      Mapped[int]            = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id:   Mapped[Optional[str]]  = mapped_column(String(255), unique=True, index=True)
    token:        Mapped[Optional[str]]  = mapped_column(Text)

    device_type:  Mapped[Optional[str]]  = mapped_column(String(20))
    user_agent:   Mapped[Optional[str]]  = mapped_column(Text)
    browser:      Mapped[Optional[str]]  = mapped_column(String(100))
    os:           Mapped[Optional[str]]  = mapped_column(String(100))
    device_model: Mapped[Optional[str]]  = mapped_column(String(250))

    ip_address:   Mapped[str]            = mapped_column(String(45), nullable=False)
    country:      Mapped[Optional[str]]  = mapped_column(String(100))
    city:         Mapped[Optional[str]]  = mapped_column(String(100))

    uid:          Mapped[Optional[str]]  = mapped_column(String(50))
    player_id:    Mapped[Optional[str]]  = mapped_column(String(50))

    login_at:     Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    logout_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity:Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    login_method: Mapped[str]            = mapped_column(String(20), default="password")
    login_status: Mapped[str]            = mapped_column(String(20), default="success")
    failed_reason:Mapped[Optional[str]]  = mapped_column(Text)

    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
