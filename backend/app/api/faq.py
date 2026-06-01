from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.faq_service import (
    list_faqs,
    get_faq,
    create_faq,
    update_faq,
    delete_faq,
    batch_create_faqs,
)

router = APIRouter(prefix="/api/faqs", tags=["FAQ"])


@router.get("")
async def api_list_faqs(
    category: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    return {"data": list_faqs(category, keyword), "total": len(list_faqs(category, keyword))}


@router.get("/{faq_id}")
async def api_get_faq(faq_id: str):
    faq = get_faq(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"data": faq}


@router.post("")
async def api_create_faq(data: dict):
    required = ["category", "question", "answer"]
    for field in required:
        if field not in data or not data[field]:
            raise HTTPException(status_code=400, detail=f"Field '{field}' is required")
    faq = create_faq(data)
    return {"data": faq, "message": "FAQ created successfully"}


@router.post("/batch")
async def api_batch_create_faqs(data: dict):
    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="Items list is required")
    created = batch_create_faqs(items)
    return {"data": created, "total": len(created), "message": f"{len(created)} FAQs created successfully"}


@router.put("/{faq_id}")
async def api_update_faq(faq_id: str, data: dict):
    faq = update_faq(faq_id, data)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"data": faq, "message": "FAQ updated successfully"}


@router.delete("/{faq_id}")
async def api_delete_faq(faq_id: str):
    deleted = delete_faq(faq_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"message": "FAQ deleted successfully"}
