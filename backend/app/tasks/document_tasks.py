from app.tasks.celery_app import celery_app
from app.services.document_service import (
    get_document,
    get_document_file,
    update_document_status,
    save_document_text,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def extract_text_from_document(self, doc_id: str, filename: str):
    """Extract text from uploaded document."""
    try:
        file_path = get_document_file(doc_id, filename)
        if not file_path:
            update_document_status(doc_id, "error")
            return {"status": "error", "error": "File not found"}

        text = ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if ext == "txt" or ext == "md":
            text = file_path.read_text(encoding="utf-8")
        elif ext == "pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(str(file_path))
            for page in doc:
                text += page.get_text()
            doc.close()
        elif ext == "docx":
            import docx
            doc = docx.Document(str(file_path))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            update_document_status(doc_id, "error")
            return {"status": "error", "error": f"Unsupported file type: {ext}"}

        char_count = len(text)
        save_document_text(doc_id, text)
        update_document_status(doc_id, "ready", char_count)

        return {"status": "success", "doc_id": doc_id, "char_count": char_count}

    except Exception as e:
        update_document_status(doc_id, "error")
        raise self.retry(exc=e)
