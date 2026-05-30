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


# Lazy-loaded store instances (re-created when settings change, e.g. in tests)
_store_cache: dict[str, JsonFileStore] = {}


def _get_store(file_key: str, settings_attr: str) -> JsonFileStore:
    path = getattr(settings, settings_attr)
    cache_key = f"{file_key}:{path}"
    if cache_key not in _store_cache:
        _store_cache[cache_key] = JsonFileStore(path)
    return _store_cache[cache_key]


def get_faq_store() -> JsonFileStore:
    return _get_store("faq", "faq_file")


def get_cache_status_store() -> JsonFileStore:
    return _get_store("cache_status", "cache_status_file")


# Module-level __getattr__ for backward-compatible `from X import faq_store`
def __getattr__(name: str) -> Any:
    if name == "faq_store":
        return get_faq_store()
    if name == "cache_status_store":
        return get_cache_status_store()
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
