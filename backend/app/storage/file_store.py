from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any
from filelock import FileLock

from app.core.config import settings


class JsonFileStore:
    """Thread-safe JSON file store using file locks."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.lock_path = self.file_path.with_suffix(".json.lock")
        self._ensure_file()

    def _ensure_file(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("[]", encoding="utf-8")

    def read_all(self) -> list[dict]:
        with FileLock(str(self.lock_path)):
            raw = self.file_path.read_text(encoding="utf-8")
            return json.loads(raw) if raw.strip() else []

    def write_all(self, data: list[dict]):
        with FileLock(str(self.lock_path)):
            self.file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def find_one(self, pred) -> dict | None:
        items = self.read_all()
        for item in items:
            if pred(item):
                return item
        return None

    def find_by_id(self, item_id: str, id_field: str = "id") -> dict | None:
        return self.find_one(lambda x: x.get(id_field) == item_id)

    def insert(self, item: dict) -> dict:
        items = self.read_all()
        items.append(item)
        self.write_all(items)
        return item

    def update(self, item_id: str, updates: dict, id_field: str = "id") -> dict | None:
        items = self.read_all()
        for i, item in enumerate(items):
            if item.get(id_field) == item_id:
                items[i].update(updates)
                self.write_all(items)
                return items[i]
        return None

    def delete(self, item_id: str, id_field: str = "id") -> bool:
        items = self.read_all()
        new_items = [i for i in items if i.get(id_field) != item_id]
        if len(new_items) == len(items):
            return False
        self.write_all(new_items)
        return True

    def count(self) -> int:
        return len(self.read_all())


# Lazy-loaded FAQ store (re-created when settings change, e.g. in tests)
_faq_store: JsonFileStore | None = None


def get_faq_store() -> JsonFileStore:
    global _faq_store
    path = os.path.join(settings.data_dir, "faqs.json")
    if _faq_store is None or str(_faq_store.file_path) != path:
        _faq_store = JsonFileStore(path)
    return _faq_store


def _faqs_dir() -> Path:
    return Path(settings.faq_dataset_path)


def _build_cat_index() -> dict[str, str]:
    """Build {category: filename} from files on disk."""
    idx = {}
    faqs_dir = _faqs_dir()
    if not faqs_dir.exists():
        return idx
    for f in sorted(faqs_dir.glob("*.json")):
        if f.name == "format.md":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data:
                cat = data[0].get("category", "")
                if cat:
                    idx[cat] = f.name
        except Exception:
            continue
    return idx


def _cat_to_file(category: str) -> Path:
    """Get the file path for a category's FAQ file. Builds index from disk."""
    idx = _build_cat_index()
    if category in idx:
        return _faqs_dir() / idx[category]
    # New category: use sanitized category name as filename
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in category)
    return _faqs_dir() / f"{safe}.json"


def _write_category(category: str, faqs: list[dict]):
    """Write FAQs for a single category to its file."""
    target = _cat_to_file(category)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_suffix(".json.lock")
    with FileLock(str(lock_path)):
        target.write_text(
            json.dumps(faqs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def get_all_faqs() -> list[dict]:
    """Read all FAQs from the dataset path (config.faq_dataset_path)."""
    faqs_dir = _faqs_dir()
    if not faqs_dir.exists():
        return []

    all_faqs = []
    for f in sorted(faqs_dir.glob("*.json")):
        if f.name == "format.md":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            all_faqs.extend(data)
        except Exception:
            continue
    return all_faqs


def insert_faq(faq: dict):
    """Insert a FAQ into the appropriate category file."""
    cat = faq.get("category", "未分类")
    target = _cat_to_file(cat)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
    else:
        existing = []
    existing.append(faq)
    _write_category(cat, existing)


def update_faq_by_id(faq_id: str, updates: dict) -> bool:
    """Update a FAQ by ID, handling possible category change."""
    all_faqs = get_all_faqs()
    for faq in all_faqs:
        if faq["id"] == faq_id:
            old_cat = faq.get("category", "未分类")
            faq.update(updates)
            new_cat = faq.get("category", "未分类")
            if old_cat == new_cat:
                same_cat = [f for f in all_faqs if f.get("category") == old_cat]
                _write_category(old_cat, same_cat)
            else:
                # Rewrite both old and new category files
                old_faqs = [f for f in all_faqs if f.get("category") == old_cat and f["id"] != faq_id]
                new_faqs = [f for f in all_faqs if f.get("category") == new_cat]
                _write_category(old_cat, old_faqs)
                _write_category(new_cat, new_faqs)
            return True
    return False


def delete_faq_by_id(faq_id: str) -> bool:
    """Delete a FAQ by ID from its category file."""
    all_faqs = get_all_faqs()
    target = None
    for faq in all_faqs:
        if faq["id"] == faq_id:
            target = faq
            break
    if not target:
        return False
    cat = target.get("category", "未分类")
    remaining = [f for f in all_faqs if f["id"] != faq_id]
    cat_faqs = [f for f in remaining if f.get("category") == cat]
    _write_category(cat, cat_faqs)
    return True


# Module-level __getattr__ for backward-compatible `from X import faq_store`
def __getattr__(name: str) -> Any:
    if name == "faq_store":
        return get_faq_store()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Document file operations
def save_document_file(doc_id: str, filename: str, content_bytes: bytes) -> Path:
    doc_dir = Path(settings.documents_dir) / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    file_path = doc_dir / filename
    file_path.write_bytes(content_bytes)
    return file_path


def save_document_text(doc_id: str, text: str):
    doc_dir = Path(settings.documents_dir) / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    text_path = doc_dir / "content.txt"
    text_path.write_text(text, encoding="utf-8")


def get_document_text(doc_id: str) -> str | None:
    text_path = Path(settings.documents_dir) / doc_id / "content.txt"
    if text_path.exists():
        return text_path.read_text(encoding="utf-8")
    return None


def get_document_file_path(doc_id: str, filename: str) -> Path | None:
    file_path = Path(settings.documents_dir) / doc_id / filename
    return file_path if file_path.exists() else None


def delete_document_dir(doc_id: str):
    doc_dir = Path(settings.documents_dir) / doc_id
    if doc_dir.exists():
        shutil.rmtree(doc_dir)


def save_document_meta(doc_id: str, meta: dict):
    doc_dir = Path(settings.documents_dir) / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    meta_path = doc_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def get_document_meta(doc_id: str) -> dict | None:
    meta_path = Path(settings.documents_dir) / doc_id / "meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return None
