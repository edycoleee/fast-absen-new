"""FaceService — InsightFace-based face registration & verification.

Design decisions:
- FaceEmbedding rows are keyed by *user_id* (FK → users.id).
  Lookup by id_pegawai always goes through the User table first.
- Multi-image registration: each valid image is stored as its own
  FaceEmbedding row AND a single L2-normalised average embedding is
  also stored (image_path == AVG_MARKER sentinel).
- Quality filtering: high-quality embeddings are preferred; if fewer
  than MIN_REQUIRED pass the threshold, the top-N by score are used.
- At verify time we compare against every active embedding and keep
  the highest cosine similarity.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any
import base64
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from models.face_embedding import FaceEmbedding
from models.user import User
from utils.logger import logger
from utils.constants import ErrorMessages, HTTPStatus as HC


# ─────────────────────────────────────────────────────────────────────────────
# Singleton model wrapper
# ─────────────────────────────────────────────────────────────────────────────

class FaceAnalysisModel:
    """
    Singleton wrapper for InsightFace FaceAnalysis.
    Ensures only one model instance is loaded into memory.
    """
    _instance = None
    _initialized: bool = False

    @classmethod
    def get_instance(cls, use_gpu: bool = False):
        """Get or create the FaceAnalysis instance."""
        if cls._instance is None:
            try:
                import insightface
                logger.info("Initializing InsightFace model...")
                provider = "CUDAExecutionProvider" if use_gpu else "CPUExecutionProvider"
                cls._instance = insightface.app.FaceAnalysis(
                    name="buffalo_l",
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                )
                cls._instance.prepare(ctx_id=0, det_size=(640, 640))
                cls._initialized = True
                logger.info(f"InsightFace model initialized (provider: {provider})")
            except Exception as exc:
                logger.error(f"InsightFace failed to load: {exc}")
                raise
        return cls._instance

    @classmethod
    def is_initialized(cls) -> bool:
        """Return True if the model has been loaded."""
        return cls._initialized

    @classmethod
    def reset(cls) -> None:
        """Release the model instance (useful for testing)."""
        cls._instance = None
        cls._initialized = False
        logger.info("InsightFace model reset")


# ─────────────────────────────────────────────────────────────────────────────
# Embedding utilities
# ─────────────────────────────────────────────────────────────────────────────

def normalize_embedding(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector; returns zero-vector unchanged."""
    norm = np.linalg.norm(v)
    if norm > 0:
        return v / norm
    return v


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Cosine similarity between two embedding vectors.
    Returns 0.0 if either vector has zero norm.
    """
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def average_embeddings(embeddings: List[np.ndarray], normalize: bool = True) -> np.ndarray:
    """Compute element-wise mean of multiple embeddings, optionally L2-normalized."""
    if not embeddings:
        raise ValueError("Cannot average an empty list of embeddings")
    arr = np.array(embeddings, dtype=np.float32)
    avg = np.mean(arr, axis=0)
    return normalize_embedding(avg) if normalize else avg


def filter_high_quality_embeddings(
    embeddings_data: List[Dict[str, Any]],
    quality_threshold: float,
    min_required: int = 3,
) -> List[Dict[str, Any]]:
    """
    Return embeddings at or above *quality_threshold*.
    If fewer than *min_required* pass, fall back to the top-N by quality score.

    Each item in *embeddings_data* must have 'embedding' and 'quality' keys.
    """
    high_quality = [e for e in embeddings_data if e["quality"] >= quality_threshold]

    if len(high_quality) >= min_required:
        logger.info(
            f"Quality filter: using {len(high_quality)} embeddings "
            f"(quality >= {quality_threshold})"
        )
        return high_quality

    # Fallback: sort by quality descending and take enough
    sorted_embs = sorted(embeddings_data, key=lambda x: x["quality"], reverse=True)
    selected = sorted_embs[:max(min_required, len(high_quality))]
    logger.info(
        f"Quality filter fallback: using top {len(selected)} embeddings "
        f"({len(high_quality)} passed threshold {quality_threshold})"
    )
    return selected


def calculate_embedding_statistics(embeddings: List[np.ndarray]) -> Dict[str, Any]:
    """Return count, mean_norm, std_norm, and dimension for a list of embeddings."""
    if not embeddings:
        return {}
    arr = np.array(embeddings, dtype=np.float32)
    norms = [float(np.linalg.norm(e)) for e in embeddings]
    return {
        "count": len(embeddings),
        "mean_norm": float(np.mean(norms)),
        "std_norm": float(np.std(norms)),
        "dimension": arr.shape[1] if arr.ndim > 1 else len(embeddings[0]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class FaceService:
    THRESHOLD: float     = 0.4    # cosine-similarity cut-off for verification
    MIN_QUALITY: float   = 0.3    # per-image quality score threshold
    MIN_FACE_COVERAGE: float = 0.25  # min fraction of image area a face must cover
    AVG_MARKER: str      = "__avg__"  # image_path sentinel for averaged embeddings

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── InsightFace model ─────────────────────────────────────────────────────

    @classmethod
    def get_model(cls):
        """Delegate to the FaceAnalysisModel singleton."""
        return FaceAnalysisModel.get_instance()

    # ── Low-level helpers ─────────────────────────────────────────────────────

    def _decode_image(self, b64_str: str) -> "np.ndarray":
        import cv2
        # Strip data-URI prefix e.g. "data:image/jpeg;base64,..."
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        try:
            data = base64.b64decode(b64_str)
            arr  = np.frombuffer(data, np.uint8)
            img  = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("cv2.imdecode returned None")
            return img
        except Exception as exc:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail=f"Gambar tidak valid: {exc}")

    def _extract_embedding(self, b64_str: str) -> Tuple[List[float], float]:
        """Return (embedding_list, quality_score) or raise HTTPException."""
        model  = self.get_model()
        img    = self._decode_image(b64_str)
        faces  = model.get(img)
        if not faces:
            raise HTTPException(status_code=HC.BAD_REQUEST, detail="Wajah tidak terdeteksi")
        face    = faces[0]
        emb     = face.normed_embedding.tolist()
        quality = float(face.det_score) if hasattr(face, "det_score") else 0.0
        return emb, quality

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Delegate to the module-level cosine_similarity utility."""
        return cosine_similarity(a, b)

    # ── User look-up ──────────────────────────────────────────────────────────

    async def _get_user_by_pegawai(self, id_pegawai: str) -> User:
        result = await self.db.execute(
            select(User).where(User.id_pegawai == id_pegawai)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=HC.NOT_FOUND,
                detail=ErrorMessages.NOT_FOUND.format(f"User untuk pegawai {id_pegawai}"),
            )
        if not user.is_active:
            raise HTTPException(status_code=HC.FORBIDDEN, detail=ErrorMessages.INACTIVE_USER)
        return user

    def validate_face(self, b64_image: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate a single image for face quality.

        Returns (success, message, face_data).
        face_data on success: {quality_score, bbox, face_coverage, landmarks}
        face_data on failure: {error}
        """
        try:
            model = self.get_model()
            img   = self._decode_image(b64_image)
        except HTTPException as exc:
            return False, exc.detail, {"error": exc.detail}
        except Exception as exc:
            return False, f"Gambar tidak valid: {exc}", {"error": str(exc)}

        faces = model.get(img)

        if not faces:
            return False, "Wajah tidak terdeteksi dalam gambar", {"error": "no_face"}

        if len(faces) > 1:
            return (
                False,
                f"Terdeteksi {len(faces)} wajah; pastikan hanya 1 wajah dalam frame",
                {"error": "multiple_faces", "face_count": len(faces)},
            )

        face    = faces[0]
        quality = float(face.det_score) if hasattr(face, "det_score") else 0.0

        # Face coverage check
        h, w    = img.shape[:2]
        img_area = h * w
        bbox     = face.bbox.tolist() if hasattr(face, "bbox") else None
        if bbox:
            fx1, fy1, fx2, fy2 = bbox
            face_area  = (fx2 - fx1) * (fy2 - fy1)
            coverage   = face_area / img_area if img_area > 0 else 0.0
        else:
            coverage = 0.0

        if coverage < self.MIN_FACE_COVERAGE:
            return (
                False,
                f"Wajah terlalu kecil (coverage {coverage:.1%}); pastikan wajah mengisi ≥25% frame",
                {"error": "face_too_small", "face_coverage": round(coverage, 4)},
            )

        if quality < self.MIN_QUALITY:
            return (
                False,
                f"Kualitas wajah rendah (score {quality:.2f}); perbaiki pencahayaan atau posisi",
                {"error": "low_quality", "quality_score": round(quality, 4)},
            )

        landmarks = face.kps.tolist() if hasattr(face, "kps") and face.kps is not None else None
        return (
            True,
            "Wajah valid",
            {
                "quality_score":  round(quality, 4),
                "face_coverage":  round(coverage, 4),
                "bbox":           [round(v, 1) for v in bbox] if bbox else None,
                "landmarks":      landmarks,
            },
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def register_face(self, id_pegawai: str, images: List[str]) -> dict:
        """
        Multi-image registration.

        1. Deactivate existing embeddings for the user.
        2. Process each image; collect valid embeddings.
        3. Save individual FaceEmbedding rows.
        4. Compute L2-normalised average and save with image_path == AVG_MARKER.

        Returns a dict suitable for FaceRegisterResponse.
        """
        user = await self._get_user_by_pegawai(id_pegawai)

        # Deactivate old embeddings
        existing = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == user.id,
                FaceEmbedding.is_active == True,
            )
        )
        for fe in existing.scalars().all():
            fe.is_active = False

        processed, raw_embeddings, failed = 0, [], 0

        for b64 in images:
            processed += 1
            try:
                emb, quality = self._extract_embedding(b64)
                raw_embeddings.append({"embedding": emb, "quality": quality})
            except HTTPException:
                failed += 1
            except Exception as exc:
                logger.warning(f"register_face image #{processed}: {exc}")
                failed += 1

        if not raw_embeddings:
            raise HTTPException(
                status_code=HC.BAD_REQUEST,
                detail="Tidak ada wajah valid yang terdeteksi dari gambar yang dikirim",
            )

        # Quality filtering with fallback — prefer high-quality, fall back to top-N
        selected = filter_high_quality_embeddings(
            raw_embeddings,
            quality_threshold=self.MIN_QUALITY,
            min_required=max(1, len(raw_embeddings) // 2),
        )

        saved_rows: List[FaceEmbedding] = []

        # Save individual embeddings
        for item in selected:
            fe = FaceEmbedding(
                user_id=user.id,
                embedding=item["embedding"],
                quality_score=item["quality"],
                is_active=True,
            )
            self.db.add(fe)
            saved_rows.append(fe)

        # Save L2-normalised averaged embedding
        avg_vec = average_embeddings(
            [np.array(item["embedding"]) for item in selected], normalize=True
        )
        avg_fe = FaceEmbedding(
            user_id=user.id,
            embedding=avg_vec.tolist(),
            image_path=self.AVG_MARKER,
            quality_score=None,
            is_active=True,
        )
        self.db.add(avg_fe)
        await self.db.commit()

        for fe in saved_rows:
            await self.db.refresh(fe)
        await self.db.refresh(avg_fe)

        stats = calculate_embedding_statistics(
            [np.array(item["embedding"]) for item in selected]
        )

        return {
            "user_id": user.id,
            "id_pegawai": id_pegawai,
            "processed_count": processed,
            "valid_count": len(raw_embeddings),
            "selected_count": len(selected),
            "failed_count": failed,
            "embeddings": [
                {
                    "embedding_id": fe.id,
                    "quality_score": fe.quality_score,
                    "created_at": fe.created_at,
                }
                for fe in saved_rows
            ],
            "average_embedding_created": True,
            "embedding_statistics": stats,
        }

    async def get_embeddings_info(self, id_pegawai: str) -> dict:
        """Return metadata for all active individual embeddings (avg row excluded)."""
        user = await self._get_user_by_pegawai(id_pegawai)
        result = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == user.id,
                FaceEmbedding.is_active == True,
                FaceEmbedding.image_path != self.AVG_MARKER,
            )
        )
        rows = result.scalars().all()
        return {
            "user_id": user.id,
            "id_pegawai": id_pegawai,
            "embeddings_count": len(rows),
            "embeddings": [
                {"id": fe.id, "quality_score": fe.quality_score, "created_at": fe.created_at}
                for fe in rows
            ],
        }

    async def delete_embeddings(self, id_pegawai: str) -> int:
        """Delete (hard) all active embeddings; returns deleted count."""
        user = await self._get_user_by_pegawai(id_pegawai)
        result = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == user.id,
                FaceEmbedding.is_active == True,
            )
        )
        rows = result.scalars().all()
        count = len(rows)
        for fe in rows:
            await self.db.delete(fe)
        await self.db.commit()
        return count

    async def verify(
        self,
        b64_image: str,
        id_pegawai: Optional[str] = None,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        1:1 verification if id_pegawai given, otherwise 1:N search.

        Returns (matched, best_similarity, matched_id_pegawai).
        """
        try:
            embedding, _ = self._extract_embedding(b64_image)
        except HTTPException:
            return False, 0.0, None

        if id_pegawai:
            user = await self._get_user_by_pegawai(id_pegawai)
            result = await self.db.execute(
                select(FaceEmbedding).where(
                    FaceEmbedding.user_id == user.id,
                    FaceEmbedding.is_active == True,
                )
            )
            rows = result.scalars().all()
            if not rows:
                raise HTTPException(
                    status_code=HC.NOT_FOUND,
                    detail=ErrorMessages.FACE_NOT_ENROLLED,
                )
            best = max(self._cosine_similarity(embedding, fe.embedding) for fe in rows)
            return best >= self.THRESHOLD, best, id_pegawai

        # 1:N — compare against all active embeddings
        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.is_active == True)
        )
        best_sim, best_user_id = -1.0, None
        for fe in result.scalars().all():
            sim = self._cosine_similarity(embedding, fe.embedding)
            if sim > best_sim:
                best_sim, best_user_id = sim, fe.user_id

        if best_sim >= self.THRESHOLD and best_user_id is not None:
            user_result = await self.db.execute(
                select(User).where(User.id == best_user_id)
            )
            found_user = user_result.scalar_one_or_none()
            return True, best_sim, found_user.id_pegawai if found_user else None

        return False, best_sim, None

    async def verify_by_user_id(
        self,
        user_id: int,
        b64_image: str,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """1:1 verification given an internal user.id — used by auth login-face."""
        thr = threshold if threshold is not None else self.THRESHOLD
        try:
            embedding, _ = self._extract_embedding(b64_image)
        except HTTPException:
            return False, 0.0

        result = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == user_id,
                FaceEmbedding.is_active == True,
            )
        )
        rows = result.scalars().all()
        if not rows:
            raise HTTPException(
                status_code=HC.BAD_REQUEST,
                detail=ErrorMessages.FACE_NOT_ENROLLED,
            )
        best = max(self._cosine_similarity(embedding, fe.embedding) for fe in rows)
        return best >= thr, best

    # ── Legacy single-enroll (backward compat) ────────────────────────────────

    async def enroll(self, id_pegawai: str, b64_image: str) -> FaceEmbedding:
        """Single-image enroll — kept for backward compatibility."""
        user = await self._get_user_by_pegawai(id_pegawai)
        embedding, quality = self._extract_embedding(b64_image)

        # Deactivate existing
        result = await self.db.execute(
            select(FaceEmbedding).where(
                FaceEmbedding.user_id == user.id,
                FaceEmbedding.is_active == True,
            )
        )
        for fe in result.scalars().all():
            fe.is_active = False

        new_fe = FaceEmbedding(
            user_id=user.id,
            embedding=embedding,
            quality_score=quality,
            is_active=True,
        )
        self.db.add(new_fe)
        await self.db.commit()
        await self.db.refresh(new_fe)
        return new_fe
