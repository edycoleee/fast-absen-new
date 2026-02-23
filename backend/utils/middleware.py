"""
Middleware untuk request tracking dan logging di FastAPI.

Kedua concern (request-ID generation dan request logging) digabung dalam satu
middleware untuk menjamin ID selalu tersedia sebelum logging — menghilangkan
kebutuhan mengatur urutan registrasi secara manual.

NOTE KEAMANAN:
  Request/response body TIDAK di-log secara sengaja.
  Body bisa mengandung credential (password, token, data sensitif).
  Jika perlu audit body di development, gunakan debugger atau tool terpisah.
"""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import logger
from utils.device_detector import get_client_ip


class RequestMiddleware(BaseHTTPMiddleware):
    """
    Single middleware yang menangani:
    1. Generate / propagasi request-ID (X-Request-ID header)
    2. Log setiap request masuk dan response keluar beserta durasinya

    Urutan eksekusi per request:
      generate request_id
      → store ke request.state.request_id
      → log request masuk
      → proses route
      → log response + durasi
      → tambahkan X-Request-ID & X-Process-Time ke response header
    """

    async def dispatch(self, request: Request, call_next):
        # --- Request ID -------------------------------------------------
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        client_host = get_client_ip(request)

        # --- Log request masuk -----------------------------------------
        # NOTE: body tidak di-log (lihat keterangan keamanan di module docstring)
        logger.info(
            f"[{request_id}] → {request.method} {request.url.path} from {client_host}"
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            process_time = time.perf_counter() - start_time

            # --- Log response keluar -----------------------------------
            logger.info(
                f"[{request_id}] ← {request.method} {request.url.path} "
                f"status={response.status_code} duration={process_time:.3f}s"
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            return response

        except Exception as exc:
            process_time = time.perf_counter() - start_time
            logger.error(
                f"[{request_id}] ✗ {request.method} {request.url.path} "
                f"duration={process_time:.3f}s error={exc}",
                exc_info=True,
            )
            raise
