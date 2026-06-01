import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import docx

from app.storage.file_store import (
    save_document_file,
    save_document_text,
    save_document_meta,
    get_document_meta,
    get_document_text,
    get_document_file_path,
    delete_document_dir,
)
from app.core.config import settings


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    return "doc_" + uuid.uuid4().hex[:8]


SUPPORTED_TYPES = {".pdf": "pdf", ".docx": "docx", ".txt": "txt", ".md": "md"}


def get_file_type(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    return SUPPORTED_TYPES.get(ext)


def _extract_text(doc_id: str, filename: str):
    """Extract text synchronously."""
    file_path = get_document_file_path(doc_id, filename)
    if not file_path:
        update_document_status(doc_id, "error")
        return

    text = ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext in ("txt", "md"):
            text = file_path.read_text(encoding="utf-8")
        elif ext == "pdf":
            doc = fitz.open(str(file_path))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        elif ext == "docx":
            doc = docx.Document(str(file_path))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            update_document_status(doc_id, "error")
            return

        char_count = len(text)
        save_document_text(doc_id, text)
        update_document_status(doc_id, "ready", char_count)
    except Exception as e:
        update_document_status(doc_id, "error")


def store_upload(filename: str, content: bytes) -> dict:
    doc_id = _new_id()
    file_type = get_file_type(filename)
    if not file_type:
        raise ValueError(f"Unsupported file type: {filename}")

    meta = {
        "id": doc_id,
        "filename": filename,
        "title": Path(filename).stem,
        "file_type": file_type,
        "status": "processing",
        "char_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }

    save_document_file(doc_id, filename, content)
    save_document_meta(doc_id, meta)

    # Extract text synchronously
    _extract_text(doc_id, filename)

    return meta


def list_documents() -> list[dict]:
    docs_dir = Path(settings.documents_dir)
    if not docs_dir.exists():
        return []
    result = []
    for d in sorted(docs_dir.iterdir()):
        if d.is_dir():
            meta = get_document_meta(d.name)
            if meta:
                result.append(meta)
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return result


def get_document(doc_id: str) -> dict | None:
    return get_document_meta(doc_id)


def get_document_content(doc_id: str) -> str | None:
    return get_document_text(doc_id)


def update_document(doc_id: str, title: str) -> dict | None:
    meta = get_document_meta(doc_id)
    if not meta:
        return None
    meta["title"] = title
    meta["updated_at"] = _now()
    save_document_meta(doc_id, meta)
    return meta


def delete_document(doc_id: str) -> bool:
    meta = get_document_meta(doc_id)
    if not meta:
        return False
    delete_document_dir(doc_id)
    return True


def get_document_file(doc_id: str, filename: str) -> Path | None:
    return get_document_file_path(doc_id, filename)


def update_document_status(doc_id: str, status: str, char_count: int = 0):
    meta = get_document_meta(doc_id) or {}
    meta["status"] = status
    meta["char_count"] = char_count
    meta["updated_at"] = _now()
    save_document_meta(doc_id, meta)
