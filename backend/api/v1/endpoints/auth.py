from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.auth import LoginRequest, TokenResponse
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
