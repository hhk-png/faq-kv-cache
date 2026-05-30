import threading
from typing import Optional

from app.storage.file_store import get_cache_status_store
from app.core.config import settings

_debounce_timer: Optional[threading.Timer] = None


def get_cache_status() -> list[dict]:
    return get_cache_status_store().read_all()


def set_cache_status(items: list[dict]):
    get_cache_status_store().write_all(items)


def trigger_cache_warm():
    global _debounce_timer
    if _debounce_timer:
        _debounce_timer.cancel()

    def _warm():
        from app.tasks.cache_tasks import warm_all_caches
        warm_all_caches.delay()

    _debounce_timer = threading.Timer(settings.cache_warm_debounce_seconds, _warm)
    _debounce_timer.start()


def build_faq_blocks(all_faqs: list[dict]) -> tuple[str, list[dict]]:
    """Build L1 category index and L2 FAQ blocks for cache warming.

    Returns:
        (l1_category_index, l2_blocks)
        Each l2_block: {"block_id": str, "category": str, "prefix": str, "content": str}
    """
    categories = {}
    for faq in all_faqs:
        cat = faq.get("category", "未分类")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(faq)

    # L1: Category index
    l1_lines = ["# FAQ类别索引", f"总FAQ数: {len(all_faqs)}", ""]
    for cat, items in sorted(categories.items()):
        l1_lines.append(f"- {cat}: {len(items)}条")
    l1_index = "\n".join(l1_lines)
    l1_prefix = "[FAQ_CATEGORY_INDEX]"

    # L2: FAQ blocks per category
    l2_blocks = []
    block_size = settings.faq_block_size
    for cat, items in sorted(categories.items()):
        for i in range(0, len(items), block_size):
            chunk = items[i : i + block_size]
            block_num = i // block_size + 1
            block_id = f"BLOCK:{cat}:{block_num:02d}"
            prefix = f"[FAQ_BLOCK:{cat}:{block_num:02d}]"

            lines = [f"# FAQ块: {cat} - 第{block_num}组", ""]
            for j, faq in enumerate(chunk):
                lines.append(f"Q{i+j+1}: {faq['question']}")
                lines.append(f"A{i+j+1}: {faq['answer']}")
                if faq.get("tags"):
                    lines.append(f"  标签: {', '.join(faq['tags'])}")
                lines.append("")
            content = "\n".join(lines)

            l2_blocks.append({
                "block_id": block_id,
                "category": cat,
                "prefix": prefix,
                "content": content,
                "faq_ids": [f.get("id") for f in chunk],
            })

    return l1_index, l1_prefix, l2_blocks
