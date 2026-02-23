from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from config.database import get_db
from schemas.face import FaceVerifyRequest
from services.face_service import FaceService
from utils.response import success_response
from utils.dependencies import require_permission, get_current_user
from utils.permission_registry import PermissionKeys
from utils.constants import SuccessMessages, HTTPStatus as HC
from models.user import User
import base64

router = APIRouter(prefix="/face", tags=["Face"])


@router.post("/enroll/{id_pegawai}")
async def enroll_face(
    id_pegawai: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.FACE_ENROLL)),
):
    svc = FaceService(db)
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    fe = await svc.enroll(id_pegawai, b64)
    return success_response(SuccessMessages.CREATED.format("Wajah"), data={"embedding_id": fe.id, "id_pegawai": fe.id_pegawai})


@router.post("/verify")
async def verify_face(
    body: FaceVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = FaceService(db)
    verified, similarity, matched_id = await svc.verify(body.face_image_b64, body.id_pegawai)
    return success_response("Berhasil", data={
        "verified": verified,
        "similarity": similarity,
        "threshold": FaceService.THRESHOLD,
        "id_pegawai": matched_id,
        "message": "Wajah cocok" if verified else "Wajah tidak cocok",
    })
