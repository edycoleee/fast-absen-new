from pydantic import BaseModel
from typing import Optional
from schemas.base import BaseSchema


class FaceEnrollResponse(BaseSchema):
    message: str
    embedding_id: int
    quality_score: Optional[float] = None
    image_path: Optional[str] = None


class FaceVerifyRequest(BaseSchema):
    face_image_b64: str
    id_pegawai: Optional[str] = None


class FaceVerifyResponse(BaseSchema):
    verified: bool
    similarity: float
    threshold: float
    id_pegawai: Optional[str] = None
    message: str
