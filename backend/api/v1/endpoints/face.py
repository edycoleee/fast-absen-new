from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from schemas.face import FaceVerifyRequest, FaceRegisterRequest, FaceValidateRequest
from services.face_service import FaceService
from utils.response import success_response
from utils.dependencies import require_permission, get_current_user
from utils.permission_registry import PermissionKeys
from utils.constants import SuccessMessages
from models.user import User
import base64

router = APIRouter(prefix="/face", tags=["Face"])


# ── Single-image quality validation ──────────────────────────────────────────

@router.post("/validate")
async def validate_face(
    body: FaceValidateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validasi kualitas wajah dari satu gambar.

    Gunakan endpoint ini sebelum registrasi untuk memastikan setiap foto:
    - Mengandung tepat satu wajah
    - Wajah memenuhi ukuran minimum (≥25% frame)
    - Skor kualitas memenuhi threshold (≥0.3)

    Respons menyertakan quality_score, face_coverage, dan bbox untuk
    debugging di frontend.
    """
    svc = FaceService(db)
    success, message, face_data = svc.validate_face(body.image)
    data = {
        "valid":         success,
        "message":       message,
        "quality_score": face_data.get("quality_score"),
        "face_coverage": face_data.get("face_coverage"),
        "bbox":          face_data.get("bbox"),
        "landmarks":     face_data.get("landmarks"),
        "error":         face_data.get("error") if not success else None,
    }
    return success_response(message, data=data)


# ── Multi-image face registration ─────────────────────────────────────────────

@router.post("/users/{id_pegawai}/register")
async def register_face(
    id_pegawai: str,
    body: FaceRegisterRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.FACE_ENROLL)),
):
    """
    Daftarkan wajah pegawai menggunakan multiple image (5–10 disarankan).

    Setiap gambar diproses secara independen; hasil embedding individual
    disimpan beserta satu rata-rata embedding (averaged).
    Pendaftaran ulang otomatis menon-aktifkan embedding lama.
    """
    svc = FaceService(db)
    result = await svc.register_face(id_pegawai, body.images)
    msg = (
        f"Registrasi wajah berhasil: {result['valid_count']} dari "
        f"{result['processed_count']} gambar valid, averaged embedding dibuat"
    )
    return success_response(msg, data=result)


@router.get("/users/{id_pegawai}/embeddings")
async def get_embeddings(
    id_pegawai: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.FACE_MANAGE)),
):
    """Lihat daftar embedding wajah yang terdaftar untuk pegawai."""
    svc = FaceService(db)
    info = await svc.get_embeddings_info(id_pegawai)
    msg  = f"Ditemukan {info['embeddings_count']} embedding wajah"
    return success_response(msg, data=info)


@router.delete("/users/{id_pegawai}/embeddings")
async def delete_embeddings(
    id_pegawai: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.FACE_MANAGE)),
):
    """Hapus semua embedding wajah pegawai (gunakan sebelum re-register)."""
    svc   = FaceService(db)
    count = await svc.delete_embeddings(id_pegawai)
    return success_response(
        SuccessMessages.DELETED.format(f"{count} embedding wajah"),
        data={"deleted_count": count},
    )


# ── Legacy single-image enroll (backward compat) ──────────────────────────────

@router.post("/enroll/{id_pegawai}")
async def enroll_face(
    id_pegawai: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(PermissionKeys.FACE_ENROLL)),
):
    """Single-image enroll (deprecated — gunakan /users/{id_pegawai}/register)."""
    svc     = FaceService(db)
    content = await file.read()
    b64     = base64.b64encode(content).decode()
    fe      = await svc.enroll(id_pegawai, b64)
    return success_response(
        SuccessMessages.CREATED.format("Wajah"),
        data={"embedding_id": fe.id, "user_id": fe.user_id},
    )


# ── Verification ──────────────────────────────────────────────────────────────

@router.post("/verify")
async def verify_face(
    body: FaceVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verifikasi wajah 1:1 (dengan id_pegawai) atau 1:N (tanpa id_pegawai)."""
    svc = FaceService(db)
    verified, similarity, matched_id = await svc.verify(body.face_image_b64, body.id_pegawai)
    return success_response("Berhasil", data={
        "verified":   verified,
        "similarity": similarity,
        "threshold":  FaceService.THRESHOLD,
        "id_pegawai": matched_id,
        "message":    "Wajah cocok" if verified else "Wajah tidak cocok",
    })
