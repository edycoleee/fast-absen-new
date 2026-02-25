from typing import Dict, List


PERMISSIONS: Dict[str, str] = {
    # Auth
    "user.login": "Login user",
    # Users
    "users.read": "Lihat data user",
    "users.create": "Buat user baru",
    "users.update": "Update data user",
    "users.delete": "Hapus user",
    # Roles
    "roles.read": "Lihat data role",
    "roles.create": "Buat role baru",
    "roles.update": "Update data role",
    "roles.delete": "Hapus role",
    # Permissions
    "permissions.read": "Lihat data permission",
    "permissions.create": "Buat permission baru",
    "permissions.update": "Update data permission",
    "permissions.delete": "Hapus permission",
    # Pegawai
    "pegawai.read": "Lihat data pegawai",
    "pegawai.create": "Tambah pegawai",
    "pegawai.update": "Update data pegawai",
    "pegawai.delete": "Hapus pegawai",
    # Unit
    "unit.read": "Lihat data unit",
    "unit.create": "Tambah unit",
    "unit.update": "Update data unit",
    "unit.delete": "Hapus unit",
    # Absensi
    "absensi.read": "Lihat data absensi",
    "absensi.create": "Buat absensi",
    "absensi.update": "Update absensi",
    "absensi.delete": "Hapus absensi",
    # Face
    "face.enroll": "Daftarkan wajah",
    "face.verify": "Verifikasi wajah",
    "face.manage": "Kelola data wajah",
    # Sessions
    "user_sessions.read": "Lihat sesi login",
    "user_sessions.create": "Buat sesi login",
    "user_sessions.update": "Update sesi login",
    "user_sessions.delete": "Hapus sesi login",
    # Reports
    "report.read": "Lihat laporan",
    # Special
    "login_absensi.read": "Lihat absensi via login wajah",
    "login_absensi.create": "Absensi via login wajah",
}


class PermissionKeys:
    USER_LOGIN = "user.login"
    USERS_READ = "users.read"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_DELETE = "users.delete"
    ROLES_READ = "roles.read"
    ROLES_CREATE = "roles.create"
    ROLES_UPDATE = "roles.update"
    ROLES_DELETE = "roles.delete"
    PERMISSIONS_READ = "permissions.read"
    PERMISSIONS_CREATE = "permissions.create"
    PERMISSIONS_UPDATE = "permissions.update"
    PERMISSIONS_DELETE = "permissions.delete"
    PEGAWAI_READ = "pegawai.read"
    PEGAWAI_CREATE = "pegawai.create"
    PEGAWAI_UPDATE = "pegawai.update"
    PEGAWAI_DELETE = "pegawai.delete"
    UNIT_READ = "unit.read"
    UNIT_CREATE = "unit.create"
    UNIT_UPDATE = "unit.update"
    UNIT_DELETE = "unit.delete"
    ABSENSI_READ = "absensi.read"
    ABSENSI_CREATE = "absensi.create"
    ABSENSI_UPDATE = "absensi.update"
    ABSENSI_DELETE = "absensi.delete"
    FACE_ENROLL = "face.enroll"
    FACE_VERIFY = "face.verify"
    FACE_MANAGE = "face.manage"
    USER_SESSIONS_READ = "user_sessions.read"
    USER_SESSIONS_CREATE = "user_sessions.create"
    USER_SESSIONS_UPDATE = "user_sessions.update"
    USER_SESSIONS_DELETE = "user_sessions.delete"
    REPORT_READ = "report.read"
    LOGIN_ABSENSI_READ = "login_absensi.read"
    LOGIN_ABSENSI_CREATE = "login_absensi.create"


def list_permissions() -> List[Dict]:
    return [{"name": k, "description": v} for k, v in PERMISSIONS.items()]
