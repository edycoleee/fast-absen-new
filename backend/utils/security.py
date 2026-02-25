"""
Security utilities: password hashing dan JWT token management.

JWT payload yang digunakan mengikuti RFC 7519:
  - sub  : subject (user ID)
  - iat  : issued at
  - exp  : expiration
  - iss  : issuer (JWT_ISSUER dari settings)
  - aud  : audience (JWT_AUDIENCE dari settings)
"""
import bcrypt as _bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from config.settings import settings


def hash_password(password: str) -> str:
    """Hash plain-text password menggunakan bcrypt."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifikasi plain-text password terhadap hash yang tersimpan."""
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Buat JWT access token dengan standard claims (RFC 7519).

    Args:
        data: Dict yang HARUS mengandung key "sub" (user ID sebagai string).
        expires_delta: Override durasi kedaluwarsa; default ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload = {
        **data,
        "iat": int(now.timestamp()),
        "exp": expire,          # jose/JWT lib menerima datetime maupun int
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode dan verifikasi JWT access token.
    Memvalidasi signature, expiration, issuer, dan audience.

    Args:
        token: JWT string dari Authorization header.

    Returns:
        Decoded payload dict, atau None jika token tidak valid.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        return None


# Backward-compatible alias — kode lama yang memanggil verify_token tetap berjalan
verify_token = decode_access_token
