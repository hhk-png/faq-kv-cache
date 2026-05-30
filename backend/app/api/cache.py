from fastapi import APIRouter

from app.services.cache_service import get_cache_status

router = APIRouter(prefix="/api/cache", tags=["Cache"])


@router.get("/status")
async def api_cache_status():
    status = get_cache_status()
    return {"data": status}
