from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from services.stats_service import StatsService
from utils.response import success_response
from utils.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    svc = StatsService(db)
    stats = await svc.get_overview()
    return success_response("OK", data=stats.model_dump())
