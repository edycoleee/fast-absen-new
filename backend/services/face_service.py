from typing import Optional, List, Tuple
import base64
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from models.face_embedding import FaceEmbedding
from models.pegawai import Pegawai
from utils.logger import logger
from utils.constants import ErrorMessages, HTTPStatus as HC


class FaceService:
    _app = None
    THRESHOLD = 0.4

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def get_model(cls):
        if cls._app is None:
            try:
                import insightface
                cls._app = insightface.app.FaceAnalysis(
                    name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
                )
                cls._app.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("InsightFace model loaded")
            except Exception as e:
                logger.error(f"InsightFace failed to load: {e}")
                raise
        return cls._app

    def _decode_image(self, b64_str: str) -> np.ndarray:
        import cv2
        try:
            data = base64.b64decode(b64_str)
            arr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Cannot decode image")
            return img
        except Exception as e:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=f"Gambar tidak valid: {e}")

    def _get_embedding(self, b64_str: str) -> np.ndarray:
        model = self.get_model()
        img = self._decode_image(b64_str)
        faces = model.get(img)
        if not faces:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail="Wajah tidak terdeteksi")
        return faces[0].normed_embedding.tolist()

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        va, vb = np.array(a), np.array(b)
        return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-8))

    async def enroll(self, id_pegawai: str, b64_image: str) -> FaceEmbedding:
        pegawai = await self.db.get(Pegawai, id_pegawai)
        if not pegawai:
            raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.NOT_FOUND.format("Pegawai"))
        embedding = self._get_embedding(b64_image)
        # deactivate existing
        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.id_pegawai == id_pegawai, FaceEmbedding.is_active == True)
        )
        for fe in result.scalars().all():
            fe.is_active = False
        new_fe = FaceEmbedding(id_pegawai=id_pegawai, embedding=embedding, is_active=True)
        self.db.add(new_fe)
        await self.db.commit()
        await self.db.refresh(new_fe)
        return new_fe

    async def verify(self, b64_image: str, id_pegawai: Optional[str] = None) -> Tuple[bool, float, Optional[str]]:
        embedding = self._get_embedding(b64_image)
        if id_pegawai:
            result = await self.db.execute(
                select(FaceEmbedding).where(
                    FaceEmbedding.id_pegawai == id_pegawai, FaceEmbedding.is_active == True
                )
            )
            fe = result.scalar_one_or_none()
            if not fe:
                raise HTTPException(status_code=HC.NOT_FOUND, detail=ErrorMessages.FACE_NOT_ENROLLED)
            sim = self._cosine_similarity(embedding, fe.embedding)
            return sim >= self.THRESHOLD, sim, id_pegawai
        # search all
        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.is_active == True)
        )
        best_sim, best_id = -1.0, None
        for fe in result.scalars().all():
            sim = self._cosine_similarity(embedding, fe.embedding)
            if sim > best_sim:
                best_sim, best_id = sim, fe.id_pegawai
        if best_sim >= self.THRESHOLD:
            return True, best_sim, best_id
        return False, best_sim, None
