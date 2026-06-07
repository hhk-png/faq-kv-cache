from fastapi import APIRouter
from pydantic import BaseModel

from app.storage import user_store

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    user_id: str


@router.post("/login")
async def api_login(req: LoginRequest):
    if not req.user_id.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="User ID is required")
    user = user_store.login(req.user_id.strip())
    return {"data": user}
