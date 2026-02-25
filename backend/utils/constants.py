from enum import Enum


# ============================================================
# Enums
# ============================================================

class UserRoleEnum(str, Enum):
    """Built-in application roles"""
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    KEPALA_UNIT = "kepala_unit"
    PEGAWAI = "pegawai"


class Gender(str, Enum):
    """Jenis kelamin"""
    MALE   = "MALE"
    FEMALE = "FEMALE"


class LoginMethod(str, Enum):
    """Method used to authenticate"""
    PASSWORD = "password"
    FACE = "face"
    PASSWORD_FACE = "password_face"


class LoginStatus(str, Enum):
    """Result of a login attempt"""
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"


class AbsensiStatus(str, Enum):
    """Attendance record status"""
    PRESENT  = "PRESENT"
    LATE     = "LATE"
    PERMITTED = "PERMITTED"
    SICK     = "SICK"
    ABSENT   = "ABSENT"
    LEAVE    = "LEAVE"


# ============================================================
# HTTP
# ============================================================

class HTTPStatus:
    """Common HTTP status codes"""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500


# ============================================================
# Messages
# ============================================================

class ErrorMessages:
    """Common error messages"""
    NOT_FOUND = "{} tidak ditemukan"
    ALREADY_EXISTS = "{} sudah ada"
    INVALID_CREDENTIALS = "Username atau password salah"
    UNAUTHORIZED = "Autentikasi diperlukan"
    FORBIDDEN = "Akses ditolak"
    INACTIVE_USER = "Akun tidak aktif"
    INVALID_TOKEN = "Token tidak valid atau sudah kadaluarsa"
    VALIDATION_ERROR = "Data tidak valid"
    INTERNAL_ERROR = "Terjadi kesalahan pada server"
    FACE_NOT_ENROLLED = "Wajah belum terdaftar"
    FACE_MISMATCH = "Wajah tidak cocok"
    ALREADY_CHECKED_IN = "Sudah melakukan absen masuk hari ini"
    NOT_CHECKED_IN = "Belum melakukan absen masuk"
    ABSENSI_EXISTS = "Sudah ada absensi untuk tanggal tersebut"


class SuccessMessages:
    """Common success messages"""
    CREATED = "{} berhasil ditambahkan"
    UPDATED = "{} berhasil diperbarui"
    DELETED = "{} berhasil dihapus"
    RETRIEVED = "{} berhasil diambil"
    LOGIN = "Login berhasil"
    LOGOUT = "Logout berhasil"


# ============================================================
# Pagination
# ============================================================

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 100

# ============================================================
# Date / Time formats
# ============================================================

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"

# ============================================================
# Token expiration (minutes)
# ============================================================

ACCESS_TOKEN_EXPIRE = 60
REFRESH_TOKEN_EXPIRE = 10080  # 7 days

# ============================================================
# File upload
# ============================================================

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png"]
ALLOWED_DOCUMENT_EXTENSIONS = [".jpg", ".jpeg", ".png", ".pdf"]
ALLOWED_EXTENSIONS = ALLOWED_DOCUMENT_EXTENSIONS
