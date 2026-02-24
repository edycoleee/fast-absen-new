from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request
from repositories.user_repository import UserRepository
from repositories.user_session_repository import UserSessionRepository
from models.user import User
from models.user_session import UserSession
from utils.security import verify_password, create_access_token
from utils.logger import logger
from utils.constants import ErrorMessages, LoginMethod, LoginStatus, SuccessMessages
from utils.device_detector import detect_device_info
from config.settings import settings
import uuid
import secrets


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.session_repo = UserSessionRepository(db)

    async def login_password(
        self, username: str, password: str, request: Request,
        device_type: str = "web", uid: Optional[str] = None, player_id: Optional[str] = None
    ) -> Tuple[User, str, UserSession]:
        user = await self.user_repo.get_by_username(username)
        device = detect_device_info(request)
        ip = device["ip_address"]
        # Prefer auto-detected device_type; body value overrides only when explicitly
        # set to something other than the default "web" (e.g. mobile app sets "mobile").
        effective_device_type = device_type if device_type != "web" else device["device_type"]

        if not user or not verify_password(password, user.password_hash):
            await self._log_session(
                user_id=user.id if user else None,
                ip=ip, device_type=effective_device_type,
                user_agent=device["user_agent"],
                browser=device["browser"],
                os=device["os"],
                device_model=device["device_model"],
                login_method=LoginMethod.PASSWORD, status=LoginStatus.FAILED,
                reason=ErrorMessages.INVALID_CREDENTIALS,
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ErrorMessages.INVALID_CREDENTIALS)

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ErrorMessages.INACTIVE_USER)

        token = create_access_token({"sub": str(user.id)})
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        session = await self._log_session(
            user_id=user.id, ip=ip, device_type=effective_device_type,
            user_agent=device["user_agent"],
            browser=device["browser"],
            os=device["os"],
            device_model=device["device_model"],
            login_method=LoginMethod.PASSWORD, status=LoginStatus.SUCCESS,
            token=token, expires_at=expires,
        )
        logger.info(f"Login berhasil: {username} dari {ip} [{effective_device_type}]")
        return user, token, session

    async def login_face(
        self,
        username: str,
        face_image_b64: str,
        request: Request,
        device_type: str = "web",
        threshold: Optional[float] = None,
    ) -> Tuple[User, str, UserSession, float]:
        """
        Face login 1:1.

        1. Resolve user by username.
        2. Delegate face verification to FaceService.verify_by_user_id.
        3. On success: create JWT session and return (user, token, session, similarity).
        """
        from services.face_service import FaceService

        device               = detect_device_info(request)
        ip                   = device["ip_address"]
        effective_device_type = device_type if device_type != "web" else device["device_type"]

        user = await self.user_repo.get_by_username(username)

        if not user:
            await self._log_session(
                user_id=None,
                ip=ip, device_type=effective_device_type,
                user_agent=device["user_agent"],
                browser=device["browser"],
                os=device["os"],
                device_model=device["device_model"],
                login_method=LoginMethod.FACE, status=LoginStatus.FAILED,
                reason=ErrorMessages.INVALID_CREDENTIALS,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorMessages.INVALID_CREDENTIALS,
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ErrorMessages.INACTIVE_USER)

        face_svc             = FaceService(self.db)
        matched, similarity  = await face_svc.verify_by_user_id(user.id, face_image_b64, threshold)

        if not matched:
            await self._log_session(
                user_id=user.id,
                ip=ip, device_type=effective_device_type,
                user_agent=device["user_agent"],
                browser=device["browser"],
                os=device["os"],
                device_model=device["device_model"],
                login_method=LoginMethod.FACE, status=LoginStatus.FAILED,
                reason=f"{ErrorMessages.FACE_MISMATCH} (similarity={similarity:.3f})",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorMessages.FACE_MISMATCH,
            )

        token   = create_access_token({"sub": str(user.id)})
        expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        session = await self._log_session(
            user_id=user.id, ip=ip, device_type=effective_device_type,
            user_agent=device["user_agent"],
            browser=device["browser"],
            os=device["os"],
            device_model=device["device_model"],
            login_method=LoginMethod.FACE, status=LoginStatus.SUCCESS,
            token=token, expires_at=expires,
        )
        logger.info(f"Face login berhasil: {username} dari {ip} [{effective_device_type}] (sim={similarity:.3f})")
        return user, token, session, similarity

    async def _log_session(
        self, user_id: Optional[int], ip: str, device_type: str,
        login_method: str, status: str, reason: Optional[str] = None,
        token: Optional[str] = None, expires_at: Optional[datetime] = None,
        user_agent: Optional[str] = None,
        browser: Optional[str] = None,
        os: Optional[str] = None,
        device_model: Optional[str] = None,
    ) -> Optional[UserSession]:
        now = datetime.now(timezone.utc)
        data = {
            "user_id": user_id,
            "session_id": str(uuid.uuid4()),
            "token": token or secrets.token_urlsafe(16),
            "ip_address": ip,
            "device_type": device_type,
            "user_agent": user_agent,
            "browser": browser,
            "os": os,
            "device_model": device_model,
            "login_at": now,
            "last_activity": now,
            "expires_at": expires_at,
            "login_method": login_method,
            "login_status": status,
            "failed_reason": reason,
        }
        if user_id:
            from models.user_session import UserSession as US
            session = US(**data)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            return session
        return None

    async def logout(self, token: str) -> bool:
        session = await self.session_repo.get_by_token(token)
        if session:
            session.logout_at = datetime.now(timezone.utc)
            session.login_status = LoginStatus.EXPIRED
            await self.db.commit()
        return True
