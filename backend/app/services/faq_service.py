import uuid
from datetime import datetime, timezone
from typing import Optional

from app.storage.file_store import get_all_faqs, insert_faq, update_faq_by_id, delete_faq_by_id
from app.services.block_manager import block_manager


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def list_faqs(category: Optional[str] = None, keyword: Optional[str] = None) -> list[dict]:
    items = get_all_faqs()
    if category:
        items = [i for i in items if i.get("category") == category]
    if keyword:
        kw = keyword.lower()
        items = [
            i for i in items
            if kw in i.get("question", "").lower()
            or kw in i.get("answer", "").lower()
            or kw in " ".join(i.get("tags", []))
        ]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_faq(faq_id: str) -> dict | None:
    all_faqs = get_all_faqs()
    for f in all_faqs:
        if f.get("id") == faq_id:
            return f
    return None


def create_faq(data: dict) -> dict:
    faq = {
        "id": data.get("id", _new_id()),
        "category": data["category"],
        "question": data["question"],
        "answer": data["answer"],
        "tags": data.get("tags", []),
        "created_at": _now(),
        "updated_at": _now(),
    }
    insert_faq(faq)
    block_manager.rebuild_blocks()
    return faq


def update_faq(faq_id: str, data: dict) -> dict | None:
    updates = {k: v for k, v in data.items() if k in ("category", "question", "answer", "tags")}
    if not updates:
        return None
    updates["updated_at"] = _now()
    success = update_faq_by_id(faq_id, updates)
    if success:
        result = get_faq(faq_id)
        block_manager.rebuild_blocks()
        return result
    return None


def delete_faq(faq_id: str) -> bool:
    result = delete_faq_by_id(faq_id)
    if result:
        block_manager.rebuild_blocks()
    return result


def batch_create_faqs(items: list[dict]) -> list[dict]:
    now = _now()
    created = []
    for data in items:
        faq = {
            "id": data.get("id", _new_id()),
            "category": data["category"],
            "question": data["question"],
            "answer": data["answer"],
            "tags": data.get("tags", []),
            "created_at": now,
            "updated_at": now,
        }
        created.append(faq)
        insert_faq(faq)
    block_manager.rebuild_blocks()
    return created


def get_categories() -> list[dict]:
    items = get_all_faqs()
    cat_map = {}
    for item in items:
        cat = item.get("category", "未分类")
        cat_map[cat] = cat_map.get(cat, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(cat_map.items())]
