import uuid
from datetime import datetime, timezone
from typing import Optional

from app.storage.file_store import get_faq_store
from app.services.block_manager import block_manager


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def list_faqs(category: Optional[str] = None, keyword: Optional[str] = None) -> list[dict]:
    store = get_faq_store()
    items = store.read_all()
    if category:
        items = [i for i in items if i.get("category") == category]
    if keyword:
        kw = keyword.lower()
        items = [
            i
            for i in items
            if kw in i.get("question", "").lower()
            or kw in i.get("answer", "").lower()
            or kw in " ".join(i.get("tags", []))
        ]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return items


def get_faq(faq_id: str) -> dict | None:
    return get_faq_store().find_by_id(faq_id)


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
    get_faq_store().insert(faq)
    block_manager.rebuild_blocks()
    return faq


def update_faq(faq_id: str, data: dict) -> dict | None:
    updates = {k: v for k, v in data.items() if k in ("category", "question", "answer", "tags")}
    if not updates:
        return None
    updates["updated_at"] = _now()
    result = get_faq_store().update(faq_id, updates)
    if result:
        block_manager.rebuild_blocks()
    return result


def delete_faq(faq_id: str) -> bool:
    result = get_faq_store().delete(faq_id)
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
    store = get_faq_store()
    existing = store.read_all()
    existing.extend(created)
    store.write_all(existing)
    block_manager.rebuild_blocks()
    return created


def get_categories() -> list[dict]:
    items = get_faq_store().read_all()
    cat_map = {}
    for item in items:
        cat = item.get("category", "未分类")
        if cat not in cat_map:
            cat_map[cat] = 0
        cat_map[cat] += 1
    return [{"name": k, "count": v} for k, v in sorted(cat_map.items())]
