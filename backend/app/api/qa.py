from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.services.qa_service import process_question, process_question_stream

router = APIRouter(prefix="/api/qa", tags=["QA"])


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    user_id: str = ""
    session_id: str = ""
    messages: list[MessageItem]
    prior_knowledge_type: Optional[str] = None
    prior_knowledge_content: Optional[str] = None
    document_id: Optional[str] = None


@router.post("/ask")
async def api_ask(req: AskRequest):
    """Non-streaming Q&A endpoint."""
    if not req.messages or not req.messages[-1].content.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    msgs = [{"role": m.role, "content": m.content} for m in req.messages]
    result = await process_question(
        messages=msgs,
        session_id=req.session_id,
        prior_knowledge_type=req.prior_knowledge_type,
        prior_knowledge_content=req.prior_knowledge_content,
        document_id=req.document_id,
    )
    return {"data": result}


@router.post("/ask/stream")
async def api_ask_stream(req: AskRequest):
    """Streaming Q&A endpoint (Server-Sent Events)."""
    if not req.messages or not req.messages[-1].content.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    msgs = [{"role": m.role, "content": m.content} for m in req.messages]

    return StreamingResponse(
        process_question_stream(
            messages=msgs,
            session_id=req.session_id,
            user_id=req.user_id,
            prior_knowledge_type=req.prior_knowledge_type,
            prior_knowledge_content=req.prior_knowledge_content,
            document_id=req.document_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
