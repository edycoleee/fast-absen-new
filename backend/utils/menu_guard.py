"""
Menu Guard Builder
Membangun `menu_guard` yang disertakan dalam auth response.

Frontend menggunakan `menu_guard.menus.*.visible` sebagai satu-satunya sumber
kebenaran untuk visibilitas menu dan route guard — tidak boleh ada hardcode
role → menu di sisi frontend.

Logika visibilitas:
  dashboard           → semua user yang berhasil login
  kpi_unit_role       → admin (tanpa batasan unit) | kepala_unit (scope unit sendiri)
  monitoring_absensi  → admin | punya permission absensi.read
  approval            → admin | punya permission absensi.update
  user_sessions       → admin | punya permission user_sessions.read
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Optional
from config.settings import settings
from utils.constants import UserRoleEnum

if TYPE_CHECKING:
    from models.user import User


def build_menu_guard(user: "User") -> Dict[str, Any]:
    """
    Bangun dict `menu_guard` berdasarkan role dan permission user.

    Dipanggil saat login dan /me sehingga frontend selalu mendapat kontrak
    menu yang up-to-date.

    Args:
        user: User ORM object yang sudah di-load beserta roles, permissions,
              dan relasi pegawai.

    Returns:
        Dict menu_guard yang siap di-serialize ke JSON.
    """
    perms: set[str] = user.permissions
    pegawai = getattr(user, "pegawai", None)
    base = settings.API_V1_PREFIX

    # ── Role flags ────────────────────────────────────────────────────────
    is_admin: bool = user.has_role(UserRoleEnum.SUPERADMIN) or user.has_role(UserRoleEnum.ADMIN)
    is_kepala_unit: bool = bool(pegawai and pegawai.kepala_id_unit)
    kepala_unit_scope_id: Optional[int] = pegawai.kepala_id_unit if is_kepala_unit else None

    # ── Menu visibility ───────────────────────────────────────────────────
    has_kpi = is_admin or is_kepala_unit or "report.read" in perms
    has_monitoring = is_admin or "absensi.read" in perms
    has_approval = is_admin or "absensi.update" in perms
    has_sessions = is_admin or "user_sessions.read" in perms

    menus: Dict[str, Any] = {
        "dashboard": {
            "visible": True,
        },
        "kpi_unit_role": {
            "visible": has_kpi,
            "endpoint": f"{base}/stats/overview",
            # Kepala unit hanya boleh melihat data unit miliknya;
            # frontend TIDAK mengirim id_unit jika flag ini True.
            "force_my_unit_scope": is_kepala_unit and not is_admin,
            # Admin boleh memilih unit mana pun di filter.
            "allow_optional_unit_filter": is_admin,
        },
        "monitoring_absensi": {
            "visible": has_monitoring,
        },
        "approval": {
            "visible": has_approval,
            "can_decide": has_approval,
        },
        "user_sessions": {
            "visible": has_sessions,
        },
    }

    return {
        "is_admin": is_admin,
        "is_kepala_unit": is_kepala_unit,
        "kepala_unit_scope_id": kepala_unit_scope_id,
        "menus": menus,
    }
