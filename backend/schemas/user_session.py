from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from schemas.base import BaseSchema, BaseResponseSchema


class UserSessionCreate(BaseSchema):
    user_id: int
    ip_address: str
    session_id: Optional[str] = None
    device_type: Optional[str] = None
    user_agent: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    device_model: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    uid: Optional[str] = None
    player_id: Optional[str] = None
    login_method: str = "password"
    login_status: str = "success"
    expires_at: Optional[datetime] = None


class UserSessionOut(BaseResponseSchema):
    user_id: int
    session_id: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    os: Optional[str] = None
    ip_address: str
    login_at: datetime
    logout_at: Optional[datetime] = None
    last_activity: datetime
    expires_at: Optional[datetime] = None
    login_method: str
    login_status: str
    failed_reason: Optional[str] = None
