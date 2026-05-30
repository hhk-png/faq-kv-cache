from app.tasks.celery_app import celery_app
from app.storage.file_store import get_faq_store, get_cache_status_store
from app.services.cache_service import build_faq_blocks, set_cache_status
from app.core.llm_client import cache_warmup_completion, build_prefix_cache_request


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def warm_all_caches(self):
    """Cache warmup task: build L1 and L2 blocks, send prefix cache requests."""
    all_faqs = get_faq_store().read_all()
    if not all_faqs:
        return {"status": "skipped", "reason": "No FAQs to warm up"}

    l1_index, l1_prefix, l2_blocks = build_faq_blocks(all_faqs)
    results = []

    # Warm L1
    try:
        l1_messages = build_prefix_cache_request(l1_prefix, l1_index)
        l1_result = cache_warmup_completion(l1_messages)
        results.append({
            "block_id": "CATEGORY_INDEX",
            "type": "L1",
            "prefix": l1_prefix,
            "status": "success",
            "usage": l1_result.get("usage", {}),
        })
    except Exception as e:
        results.append({
            "block_id": "CATEGORY_INDEX",
            "type": "L1",
            "prefix": l1_prefix,
            "status": "error",
            "error": str(e),
        })

    # Warm L2 blocks
    for block in l2_blocks:
        try:
            messages = build_prefix_cache_request(block["prefix"], block["content"])
            result = cache_warmup_completion(messages)
            results.append({
                "block_id": block["block_id"],
                "type": "L2",
                "category": block["category"],
                "prefix": block["prefix"],
                "status": "success",
                "usage": result.get("usage", {}),
            })
        except Exception as e:
            results.append({
                "block_id": block["block_id"],
                "type": "L2",
                "category": block.get("category", ""),
                "prefix": block["prefix"],
                "status": "error",
                "error": str(e),
            })

    set_cache_status(results)
    return {
        "status": "completed",
        "total_blocks": len(results),
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
    }
