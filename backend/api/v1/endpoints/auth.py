from fastapi import APIRouter, Depends, Request, Response, Cookie, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from config.database import get_db
from schemas.auth import LoginRequest, LoginFaceRequest, TokenResponse
from services.auth_service import AuthService
from utils.response import success_response
from utils.dependencies import get_current_user
from utils.constants import SuccessMessages, ACCESS_TOKEN_EXPIRE
from utils.menu_guard import build_menu_guard
from models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

# ── Cookie helpers ────────────────────────────────────────────────────────────
_REFRESH_COOKIE = "refresh_token"          # nama cookie sesuai spesifikasi
_COOKIE_PATH    = "/api/v1/auth"            # mencakup /refresh dan /logout
_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE * 60  # sama dengan lifetime access token


def _set_refresh_cookie(response: Response, session_id: str) -> None:
    """Tanam httpOnly refresh cookie setelah login berhasil."""
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Hapus cookie refresh saat logout."""
    response.delete_cookie(key=_REFRESH_COOKIE, path=_COOKIE_PATH)


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    user, token, session = await svc.login_password(
        body.username, body.password, request,
        device_type=body.device_type or "web",
    )
    if session and session.session_id:
        _set_refresh_cookie(response, session.session_id)
    return success_response(SuccessMessages.LOGIN, data=TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE * 60,
        user_id=user.id,
        username=user.username,
        roles=[r.name for r in user.roles],
        permissions=list(user.permissions),
        menu_guard=build_menu_guard(user),
    ).model_dump())


@router.post("/login-face")
async def login_face(
    body: LoginFaceRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Login menggunakan verifikasi wajah 1:1.

    User memasukkan username + gambar wajah (base64).  Backend memverifikasi
    apakah wajah cocok dengan embedding yang terdaftar untuk username tersebut.
    Berhasil → JWT token dikembalikan sama seperti login password.
    """
    svc = AuthService(db)
    user, token, session, similarity = await svc.login_face(
        body.username,
        body.face_image_b64,
        request,
        device_type=body.device_type or "web",
        threshold=body.threshold,
    )
    if session and session.session_id:
        _set_refresh_cookie(response, session.session_id)
    return success_response(SuccessMessages.LOGIN, data={
        **TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE * 60,
            user_id=user.id,
            username=user.username,
            roles=[r.name for r in user.roles],
            permissions=list(user.permissions),
            menu_guard=build_menu_guard(user),
        ).model_dump(),
        "confidence": round(similarity, 4),
    })


@router.post("/logout", summary="Logout — invalidasi sesi via cookie refresh_token")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias=_REFRESH_COOKIE),
):
    """
    Tidak memerlukan Authorization header.  Cookie ``refresh_token`` digunakan
    untuk mengidentifikasi sesi yang akan di-invalidasi.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Cookie refresh_token tidak ditemukan")
    svc = AuthService(db)
    await svc.logout_by_session_id(refresh_token)
    _clear_refresh_cookie(response)
    return success_response(SuccessMessages.LOGOUT)


# ── POST /auth/refresh ────────────────────────────────────────────────────────
@router.post("/refresh", summary="Refresh JWT access token menggunakan session cookie")
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: Optional[str] = Cookie(None, alias=_REFRESH_COOKIE),
):
    """
    Endpoint ini dipanggil frontend ketika access token mendekati kedaluwarsa.
    Tidak memerlukan Authorization header — cukup kirimkan cookie ``refresh_token``
    yang ditanam saat login.

    Respons: access token baru + cookie refresh diperbarui.
    """
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Cookie refresh_token tidak ditemukan")

    svc = AuthService(db)
    user, new_token = await svc.refresh_session(refresh_token)

    # Reset max_age cookie agar tidak kedaluwarsa
    _set_refresh_cookie(response, refresh_token)

    return success_response("Token berhasil diperbarui", data=TokenResponse(
        access_token=new_token,
        token_type="bearer",
        expires_in=_COOKIE_MAX_AGE,
        user_id=user.id,
        username=user.username,
        roles=[r.name for r in user.roles],
        permissions=list(user.permissions),
        menu_guard=build_menu_guard(user),
    ).model_dump())


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return success_response("OK", data={
        "id": current_user.id,
        "username": current_user.username,
        "id_pegawai": current_user.id_pegawai,
        "roles": [r.name for r in current_user.roles],
        "permissions": list(current_user.permissions),
        "menu_guard": build_menu_guard(current_user),
    })
