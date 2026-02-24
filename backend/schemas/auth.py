from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class LoginRequest(BaseModel):
    username: str
    password: str
    device_type: Optional[str] = "web"
    uid: Optional[str] = None
    player_id: Optional[str] = None


class LoginFaceRequest(BaseModel):
    username: str
    face_image_b64: str
    device_type: Optional[str] = "web"
    threshold: Optional[float] = None   # default: FaceService.THRESHOLD (0.4)
    uid: Optional[str] = None
    player_id: Optional[str] = None


# ── Menu Guard schemas ────────────────────────────────────────────────────────

class DashboardMenu(BaseModel):
    visible: bool


class KpiMenu(BaseModel):
    visible: bool
    endpoint: Optional[str] = None
    force_my_unit_scope: bool = False
    allow_optional_unit_filter: bool = False


class ApprovalMenu(BaseModel):
    visible: bool
    can_decide: bool = False


class SimpleMenu(BaseModel):
    visible: bool


class MenuGuardMenus(BaseModel):
    dashboard: DashboardMenu
    kpi_unit_role: KpiMenu
    monitoring_absensi: SimpleMenu
    approval: ApprovalMenu
    user_sessions: SimpleMenu


class MenuGuard(BaseModel):
    """Kontrak menu untuk frontend — satu-satunya sumber kebenaran visibilitas."""
    is_admin: bool
    is_kepala_unit: bool
    kepala_unit_scope_id: Optional[int] = None
    menus: MenuGuardMenus


# ── Token Response ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str
    roles: List[str]
    permissions: List[str]
    menu_guard: Dict[str, Any]
