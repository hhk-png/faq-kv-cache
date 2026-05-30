from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.services.qa_service import process_question, process_question_stream

router = APIRouter(prefix="/api/qa", tags=["QA"])


class AskRequest(BaseModel):
    question: str
    prior_knowledge_type: Optional[str] = None
    prior_knowledge_content: Optional[str] = None
    document_id: Optional[str] = None


@router.post("/ask")
async def api_ask(req: AskRequest):
    """Non-streaming Q&A endpoint."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    result = await process_question(
        question=req.question,
        prior_knowledge_type=req.prior_knowledge_type,
        prior_knowledge_content=req.prior_knowledge_content,
        document_id=req.document_id,
    )
    return {"data": result}


@router.post("/ask/stream")
async def api_ask_stream(req: AskRequest):
    """Streaming Q&A endpoint (Server-Sent Events)."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    return StreamingResponse(
        process_question_stream(
            question=req.question,
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
