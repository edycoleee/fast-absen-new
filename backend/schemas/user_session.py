from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from schemas.base import BaseSchema, BaseResponseSchema


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
