from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.auth import LoginRequest, LoginFaceRequest, TokenResponse
from services.auth_service import AuthService
from utils.response import success_response
from utils.dependencies import get_current_user
from utils.constants import SuccessMessages, ACCESS_TOKEN_EXPIRE
from utils.menu_guard import build_menu_guard
from models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer = HTTPBearer()


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    user, token, session = await svc.login_password(
        body.username, body.password, request,
        device_type=body.device_type or "web",
    )
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


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AuthService(db)
    await svc.logout(credentials.credentials)
    return success_response(SuccessMessages.LOGOUT)


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
