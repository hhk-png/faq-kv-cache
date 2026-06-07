from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.storage import session_store

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


class CreateSessionRequest(BaseModel):
    title: str = "新对话"


class UpdateTitleRequest(BaseModel):
    title: str


class AppendMessagesRequest(BaseModel):
    messages: list[dict]


def _get_user(x_user_id: str = Header("")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-ID header is required")
    return x_user_id


@router.get("")
async def api_list_sessions(x_user_id: str = Header("")):
    user_id = _get_user(x_user_id)
    return {"data": session_store.list_sessions(user_id)}


@router.post("")
async def api_create_session(req: CreateSessionRequest, x_user_id: str = Header("")):
    user_id = _get_user(x_user_id)
    return {"data": session_store.create_session(user_id, req.title)}


@router.get("/{session_id}")
async def api_get_session(session_id: str, x_user_id: str = Header("")):
    user_id = _get_user(x_user_id)
    session = session_store.get_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = session_store.get_messages(user_id, session_id)
    return {"data": {**session, "messages": messages}}


@router.put("/{session_id}")
async def api_update_session(session_id: str, req: UpdateTitleRequest, x_user_id: str = Header("")):
    user_id = _get_user(x_user_id)
    if not session_store.update_session_title(user_id, session_id, req.title):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session updated"}


@router.delete("/{session_id}")
async def api_delete_session(session_id: str, x_user_id: str = Header("")):
    user_id = _get_user(x_user_id)
    if not session_store.delete_session(user_id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}


@router.post("/{session_id}/messages")
async def api_append_messages(session_id: str, req: AppendMessagesRequest, x_user_id: str = Header("")):
    user_id = _get_user(x_user_id)
    if not session_store.get_session(user_id, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    session_store.append_messages(user_id, session_id, req.messages)
    return {"message": "Messages appended"}
