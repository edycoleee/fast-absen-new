"""
Standard response utilities untuk FastAPI.

Struktur envelope yang konsisten di seluruh API:

  Success (single resource):
    { "success": true, "message": "...", "data": { ... } }

  Success (list / non-paginated):
    { "success": true, "message": "...", "data": { "items": [...], "total": N } }

  Success (paginated):
    {
      "success": true,
      "message": "...",
      "data": { "items": [...] },
      "meta": { "page": 1, "limit": 10, "total": 50, "totalPages": 5 }
    }

  Error:
    { "success": false, "message": "..." }
    { "success": false, "message": "...", "errors": [ { "field": "...", "message": "...", "type": "..." } ] }
    { "success": false, "message": "...", "meta": { "request_id": "..." } }

Aturan:
- `data`   → selalu object, tidak pernah null / primitive
- `errors` → list field-level errors (validasi)
- `meta`   → pagination info atau debug metadata (request_id, dll.)
- HTTP status code TIDAK ada di body; ditentukan sepenuhnya oleh decorator route / JSONResponse
"""
from typing import Any, Optional, Dict, List
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Pydantic response models — gunakan sebagai response_model= di route decorator
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Pagination metadata (field `meta` pada paginated response)."""
    page: int
    limit: int
    total: int
    totalPages: int


class FieldError(BaseModel):
    """Single field-level validation error."""
    field: str
    message: str
    type: str


class SuccessResponse(BaseModel):
    """Generic success response — cocok untuk single resource."""
    success: bool = True
    message: str
    data: Dict[str, Any] = {}


class ListResponse(BaseModel):
    """Non-paginated list response."""
    success: bool = True
    message: str
    data: Dict[str, Any]          # {"items": [...], "total": N}


class PaginatedResponseModel(BaseModel):
    """Paginated response dengan `meta` terpisah dari `data`."""
    success: bool = True
    message: str
    data: Dict[str, Any]          # {"items": [...]}
    meta: PaginationMeta


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    message: str
    errors: Optional[List[FieldError]] = None
    meta: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def success_response(
    message: str = "Berhasil",
    data: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Single-resource success response.

    Args:
        message: Pesan sukses.
        data:    Object resource. Jika None, dikembalikan sebagai {}.

    Returns:
        { "success": true, "message": "...", "data": { ... } }

    Example:
        return success_response("User ditemukan", data={"id": 1, "name": "Budi"})
    """
    return {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
    }


def error_response(
    message: str = "Terjadi kesalahan",
    errors: Optional[List[Dict[str, Any]]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Standard error response.

    Args:
        message: Pesan error yang ditampilkan ke user.
        errors:  List field-level errors, umumnya dari validasi Pydantic.
                 Format tiap item: {"field": "...", "message": "...", "type": "..."}
        meta:    Metadata tambahan (mis. request_id, debug info di development).

    Returns:
        { "success": false, "message": "...", "errors": [...], "meta": {...} }
        Field `errors` dan `meta` hanya muncul jika diisi.

    Example:
        # HTTP error biasa
        return error_response("Data tidak ditemukan")

        # Validation error
        return error_response("Input tidak valid", errors=[{"field": "email", ...}])

        # Server error dengan request_id
        return error_response("Server error", meta={"request_id": "abc123"})
    """
    result: Dict[str, Any] = {"success": False, "message": message}
    if errors is not None:
        result["errors"] = errors
    if meta is not None:
        result["meta"] = meta
    return result


def list_response(
    message: str = "Berhasil",
    items: Optional[List[Any]] = None,
    total: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Non-paginated list response.

    Args:
        message: Pesan sukses.
        items:   List item resource.
        total:   Jumlah total item (opsional, untuk informasi saja).

    Returns:
        { "success": true, "message": "...", "data": { "items": [...], "total": N } }

    Example:
        return list_response("Roles ditemukan", items=role_list, total=len(role_list))
    """
    data: Dict[str, Any] = {"items": items if items is not None else []}
    if total is not None:
        data["total"] = total
    return {"success": True, "message": message, "data": data}


def paginated_response(
    message: str = "Berhasil",
    items: Optional[List[Any]] = None,
    page: int = 1,
    limit: int = 10,
    total: int = 0,
) -> Dict[str, Any]:
    """
    Paginated list response dengan `meta` terpisah dari `data`.

    Args:
        message: Pesan sukses.
        items:   List item halaman ini.
        page:    Halaman saat ini (1-based).
        limit:   Jumlah item per halaman.
        total:   Total seluruh item (semua halaman).

    Returns:
        {
          "success": true,
          "message": "...",
          "data": { "items": [...] },
          "meta": { "page": 1, "limit": 10, "total": 50, "totalPages": 5 }
        }

    Example:
        return paginated_response("Pegawai ditemukan", items=rows, page=1, limit=10, total=50)
    """
    total_pages = (total + limit - 1) // limit if limit > 0 else 0
    return {
        "success": True,
        "message": message,
        "data": {"items": items if items is not None else []},
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": total_pages,
        },
    }
