from fastapi import APIRouter
from config.database import check_database_connection, get_database_info
from utils.response import success_response

router = APIRouter(prefix="/halo", tags=["Halo"])


@router.get("")
async def halo():
    return success_response("OK", data={"message": "Halo dari FastAPI Attendance System!"})


@router.get("/health")
async def health_check():
    db_ok = await check_database_connection()
    return success_response("OK", data={
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    })


@router.get("/db-info")
async def db_info():
    info = await get_database_info()
    return success_response("OK", data=info)
