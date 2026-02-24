from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from schemas.base import BaseSchema


# ── Validation ────────────────────────────────────────────────────────────────

class FaceValidateRequest(BaseSchema):
    """Single-image face quality validation request."""
    image: str  # base64-encoded image


class FaceValidateResponse(BaseSchema):
    valid: bool
    message: str
    quality_score: Optional[float] = None
    face_coverage: Optional[float] = None
    bbox: Optional[List[float]] = None
    landmarks: Optional[Any] = None
    error: Optional[str] = None


# ── Registration ──────────────────────────────────────────────────────────────

class FaceRegisterRequest(BaseSchema):
    """Multi-image face registration request."""
    images: List[str]  # base64-encoded images (5–10 recommended)

    @field_validator("images")
    @classmethod
    def at_least_one_image(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Minimal 1 gambar diperlukan")
        if len(v) > 10:
            raise ValueError("Maksimal 10 gambar per registrasi")
        return v


class EmbeddingInfo(BaseSchema):
    embedding_id: int
    quality_score: Optional[float] = None
    created_at: Optional[datetime] = None


class FaceRegisterResponse(BaseSchema):
    user_id: int
    id_pegawai: str
    processed_count: int
    valid_count: int
    selected_count: int
    failed_count: int
    embeddings: List[EmbeddingInfo]
    average_embedding_created: bool
    embedding_statistics: Optional[Dict[str, Any]] = None


# ── Embeddings listing ────────────────────────────────────────────────────────

class EmbeddingDetail(BaseSchema):
    id: int
    quality_score: Optional[float] = None
    created_at: Optional[datetime] = None


class FaceEmbeddingsInfoResponse(BaseSchema):
    user_id: int
    id_pegawai: str
    embeddings_count: int
    embeddings: List[EmbeddingDetail]


# ── Legacy single-enroll (kept for backward compat) ──────────────────────────

class FaceEnrollResponse(BaseSchema):
    message: str
    embedding_id: int
    quality_score: Optional[float] = None
    image_path: Optional[str] = None


# ── Verification ──────────────────────────────────────────────────────────────

class FaceVerifyRequest(BaseSchema):
    face_image_b64: str
    id_pegawai: Optional[str] = None


class FaceVerifyResponse(BaseSchema):
    verified: bool
    similarity: float
    threshold: float
    id_pegawai: Optional[str] = None
    message: str
