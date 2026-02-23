"""
Exception handlers untuk FastAPI.
Production-safe error messages dengan request-ID logging.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from config.settings import settings
from utils.logger import logger
from utils.response import error_response


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions (4xx / 5xx yang sudah diketahui).

    Args:
        request: FastAPI request object.
        exc: Starlette HTTP exception.

    Returns:
        JSONResponse dengan detail error.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        f"[{request_id}] HTTP {exc.status_code} — {exc.detail} | path: {request.url.path}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors dari Pydantic / FastAPI request parsing.

    Args:
        request: FastAPI request object.
        exc: RequestValidationError dari Pydantic.

    Returns:
        JSONResponse 422 dengan daftar field yang gagal validasi.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    raw_errors = exc.errors()

    logger.warning(
        f"[{request_id}] Validation error | path: {request.url.path} | errors: {raw_errors}"
    )

    formatted_errors = [
        {
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in raw_errors
    ]

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response(
            message="Data tidak valid",
            errors=formatted_errors,
        ),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle semua exception yang tidak tertangani (500).

    Args:
        request: FastAPI request object.
        exc: Exception yang tidak terduga.

    Returns:
        JSONResponse 500. Di production hanya request_id yang dikembalikan;
        di development detail error ditampilkan untuk memudahkan debugging.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        f"[{request_id}] Unhandled exception | path: {request.url.path} | error: {exc}",
        exc_info=True,
    )

    if settings.is_production:
        extra_data: dict = {"request_id": request_id}
    else:
        extra_data = {
            "request_id": request_id,
            "error": str(exc),
            "type": type(exc).__name__,
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            message="Terjadi kesalahan pada server",
            meta=extra_data,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Daftarkan semua exception handler ke instance FastAPI.

    Args:
        app: FastAPI application instance.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

