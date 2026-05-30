from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from app.services.document_service import (
    store_upload,
    list_documents,
    get_document,
    get_document_content,
    update_document,
    delete_document,
    get_document_file,
    get_file_type,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("/upload")
async def api_upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    file_type = get_file_type(file.filename)
    if not file_type:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")
    content = await file.read()
    doc = store_upload(file.filename, content)
    return {"data": doc, "message": "Document uploaded, text extraction started"}


@router.get("")
async def api_list_documents():
    docs = list_documents()
    return {"data": docs, "total": len(docs)}


@router.get("/{doc_id}")
async def api_get_document(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"data": doc}


@router.get("/{doc_id}/content")
async def api_get_document_content(doc_id: str):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    content = get_document_content(doc_id)
    return {"data": {"id": doc_id, "content": content or "", "status": doc.get("status")}}


@router.put("/{doc_id}")
async def api_update_document(doc_id: str, data: dict):
    title = data.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    doc = update_document(doc_id, title)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"data": doc, "message": "Document updated successfully"}


@router.delete("/{doc_id}")
async def api_delete_document(doc_id: str):
    deleted = delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}
