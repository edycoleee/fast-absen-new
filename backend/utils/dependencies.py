"""
Dependencies untuk FastAPI.
Common dependencies seperti authentication, authorization, pagination, dll.
"""
from typing import Optional, List
from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.security import verify_token
from utils.constants import DEFAULT_PAGE, DEFAULT_LIMIT, MAX_LIMIT, ErrorMessages, UserRoleEnum
from repositories.user_repository import UserRepository
from models.user import User

# Security scheme
security = HTTPBearer()


async def get_request_id(
    x_request_id: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Get request ID from header.

    Args:
        x_request_id: Optional request ID passed via X-Request-ID header.

    Returns:
        Request ID string or None.
    """
    return x_request_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials.
        db: Async database session.

    Returns:
        Authenticated User object with roles and permissions loaded.

    Raises:
        HTTPException 401: If token is missing, invalid, or user not found.
        HTTPException 403: If user account is inactive.
    """
    _401 = {"WWW-Authenticate": "Bearer"}

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INVALID_TOKEN,
            headers=_401,
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INVALID_TOKEN,
            headers=_401,
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INVALID_TOKEN,
            headers=_401,
        )

    repo = UserRepository(db)
    user = await repo.get_by_id_with_roles(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.NOT_FOUND.format("User"),
            headers=_401,
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.INACTIVE_USER,
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user (convenience wrapper around get_current_user).

    Args:
        current_user: Resolved user from get_current_user.

    Returns:
        Active User object.
    """
    return current_user


class RoleChecker:
    """
    Dependency untuk memeriksa apakah user memiliki salah satu role yang diizinkan.
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """
        Verify that the current user has at least one of the allowed roles.

        Args:
            current_user: Authenticated user.

        Returns:
            User object if authorized.

        Raises:
            HTTPException 403: If user does not have any of the required roles.
        """
        if current_user.is_superadmin:
            return current_user

        user_roles = {role.name for role in current_user.roles}
        if not any(role in user_roles for role in self.allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{ErrorMessages.FORBIDDEN}. Role dibutuhkan: {', '.join(self.allowed_roles)}",
            )

        return current_user


# Pre-defined role checkers
require_superadmin = RoleChecker([UserRoleEnum.SUPERADMIN])
require_admin = RoleChecker([UserRoleEnum.SUPERADMIN, UserRoleEnum.ADMIN])
require_kepala_unit = RoleChecker([UserRoleEnum.SUPERADMIN, UserRoleEnum.ADMIN, UserRoleEnum.KEPALA_UNIT])
require_any_role = RoleChecker([UserRoleEnum.SUPERADMIN, UserRoleEnum.ADMIN, UserRoleEnum.KEPALA_UNIT, UserRoleEnum.PEGAWAI])


class PermissionChecker:
    """
    Dependency untuk memeriksa apakah user memiliki permission tertentu.
    Superadmin selalu diizinkan tanpa pengecekan permission.
    """

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """
        Verify that the current user has the required permission.

        Args:
            current_user: Authenticated user.

        Returns:
            User object if authorized.

        Raises:
            HTTPException 403: If user lacks the required permission.
        """
        if current_user.is_superadmin:
            return current_user

        if not current_user.has_permission(self.required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{ErrorMessages.FORBIDDEN}. Permission dibutuhkan: {self.required_permission}",
            )

        return current_user


def require_permission(permission_name: str) -> PermissionChecker:
    """
    Factory function untuk membuat PermissionChecker dependency.

    Args:
        permission_name: Dot-notation permission key, e.g. 'users.read'.

    Returns:
        PermissionChecker instance yang dapat digunakan sebagai FastAPI dependency.
    """
    return PermissionChecker(permission_name)


def require_any_permission(permissions: List[str]) -> PermissionChecker:
    """
    Factory function untuk membuat checker yang menerima salah satu dari beberapa permission.

    Args:
        permissions: List of dot-notation permission keys.

    Returns:
        PermissionChecker instance untuk permission pertama yang cocok.
    """
    class _AnyPermissionChecker(PermissionChecker):
        async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
            if current_user.is_superadmin:
                return current_user
            if not any(current_user.has_permission(p) for p in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{ErrorMessages.FORBIDDEN}. Salah satu permission dibutuhkan: {', '.join(permissions)}",
                )
            return current_user

    return _AnyPermissionChecker(permissions[0] if permissions else "")


class CommonQueryParams:
    """
    Common query parameters untuk pagination, search, dan sorting.
    Digunakan sebagai FastAPI dependency di endpoint list.
    """

    def __init__(
        self,
        page: int = Query(DEFAULT_PAGE, ge=1, description="Nomor halaman"),
        limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Jumlah item per halaman"),
        search: Optional[str] = Query(None, description="Kata kunci pencarian"),
        sort_by: Optional[str] = Query(None, description="Field untuk sorting"),
        sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Urutan sorting: asc atau desc"),
    ):
        self.page = page
        self.limit = limit
        self.search = search
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def offset(self) -> int:
        """Hitung offset dari page dan limit."""
        return (self.page - 1) * self.limit
