"""
FAQ Block Manager

Splits all FAQs into blocks of >= faq_block_min_tokens (default 10000).
Each block gets a fixed prefix for KV cache during warmup.
On query, ALL blocks are searched CONCURRENTLY to find relevant FAQ IDs.
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from app.storage.file_store import get_faq_store
from app.core.llm_client import chat_completion, cache_warmup_completion, build_prefix_cache_request
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FaqBlock:
    block_id: str
    prefix: str
    content: str
    faq_ids: list[str] = field(default_factory=list)


class FaqBlockManager:
    """Manages FAQ blocks for KV-cache accelerated search."""

    def __init__(self):
        self._blocks: list[FaqBlock] = []
        self._faq_map: dict[str, dict] = {}

    @property
    def block_count(self) -> int:
        return len(self._blocks)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (~1.3 chars per token for Chinese/English mix)."""
        return int(len(text) / 1.3)

    def _load_all_faqs(self) -> list[dict]:
        faqs = get_faq_store().read_all()
        self._faq_map = {faq["id"]: faq for faq in faqs}
        return faqs

    def rebuild_blocks(self):
        """Rebuild all FAQ blocks from current data."""
        faqs = self._load_all_faqs()
        if not faqs:
            self._blocks = []
            logger.info("No FAQs to build blocks from")
            return

        blocks: list[FaqBlock] = []
        current_faqs: list[dict] = []
        current_content = ""
        seq = 0
        min_tokens = settings.faq_block_min_tokens

        def _build_block_content(faq_list: list[dict]) -> str:
            parts = ["以下是FAQ库中的一些问答对：\n"]
            for i, f in enumerate(faq_list):
                parts.append(f"【FAQ {i+1}】")
                parts.append(f"ID: {f['id']}")
                if f.get("category"):
                    parts.append(f"类别: {f['category']}")
                parts.append(f"问题: {f['question']}")
                parts.append(f"答案: {f['answer']}")
                if f.get("tags"):
                    parts.append(f"标签: {', '.join(f['tags'])}")
                parts.append("")
            return "\n".join(parts)

        def _flush_block():
            nonlocal current_faqs, current_content, seq
            if not current_faqs:
                return
            seq += 1
            content = _build_block_content(current_faqs)
            block = FaqBlock(
                block_id=f"BLOCK_{seq:03d}",
                prefix=f"[FAQ_BLOCK:{seq:03d}]",
                content=content,
                faq_ids=[f["id"] for f in current_faqs],
            )
            blocks.append(block)
            logger.info(
                f"Built block {block.block_id}: {len(current_faqs)} FAQs, "
                f"~{self._estimate_tokens(content)} tokens"
            )
            current_faqs = []
            current_content = ""

        for faq in faqs:
            faq_text = f"问题: {faq['question']}\n答案: {faq['answer']}\n"
            if current_faqs:
                current_tokens = self._estimate_tokens(current_content)
                if current_tokens >= min_tokens:
                    _flush_block()
            current_faqs.append(faq)
            current_content += faq_text + "\n"

        _flush_block()
        self._blocks = blocks
        logger.info(f"Total: {len(blocks)} blocks built from {len(faqs)} FAQs")

    async def warmup_all_blocks(self):
        """Send warmup requests CONCURRENTLY for all blocks."""
        if not self._blocks:
            logger.warning("No blocks to warm up")
            return

        async def _warm_one(block: FaqBlock) -> dict:
            try:
                messages = build_prefix_cache_request(block.prefix, block.content)
                result = await cache_warmup_completion(messages)
                tokens = result.get("usage", {}).get("prompt_tokens", 0)
                logger.info(f"Warmed up {block.block_id}: {tokens} tokens")
                return {"block_id": block.block_id, "status": "success", "tokens": tokens}
            except Exception as e:
                logger.error(f"Failed to warm up {block.block_id}: {e}")
                return {"block_id": block.block_id, "status": "error", "error": str(e)}

        results = await asyncio.gather(*[_warm_one(b) for b in self._blocks])
        success = sum(1 for r in results if r["status"] == "success")
        logger.info(f"Warmup complete: {success}/{len(results)} blocks success")

    async def search_relevant_faq_ids(
        self, question: str, history: list[dict] | None = None
    ) -> list[str]:
        """Search ALL blocks CONCURRENTLY for FAQ IDs relevant to the conversation."""
        if not self._blocks:
            return []

        # Build conversation context once
        conv_parts = []
        if history:
            for msg in history[-4:]:
                role = "用户" if msg["role"] == "user" else "助手"
                conv_parts.append(f"{role}: {msg['content']}")
        conv_parts.append(f"用户: {question}")
        conv_context = "\n".join(conv_parts)

        search_prompt = (
            "你是一个FAQ检索专家。请仔细阅读以下FAQ内容，"
            "找出与当前对话相关的FAQ。\n\n"
            "返回这些FAQ的ID列表（JSON数组格式），如果都不相关则返回空数组。\n"
            "只返回JSON，不要包含其他文字。"
        )

        async def _search_block(block: FaqBlock) -> list[str]:
            try:
                messages = [
                    {"role": "system", "content": block.prefix + "\n" + block.content},
                    {
                        "role": "user",
                        "content": search_prompt + "\n\n当前对话：\n" + conv_context,
                    },
                ]
                result = await chat_completion(
                    messages=messages,
                    model=settings.llm_model,
                    max_tokens=500,
                    temperature=0,
                )
                ids = self._parse_json_ids(result)
                if ids:
                    valid = [i for i in ids if i in self._faq_map]
                    if valid:
                        logger.info(
                            f"Block {block.block_id}: found {len(valid)} relevant FAQs"
                        )
                        return valid
                return []
            except Exception as e:
                logger.error(f"Block {block.block_id} search error: {e}")
                return []

        # 并发搜索所有 Block
        results = await asyncio.gather(*[_search_block(b) for b in self._blocks])

        # 合并去重
        all_ids: list[str] = []
        seen: set[str] = set()
        for ids in results:
            for i in ids:
                if i not in seen:
                    seen.add(i)
                    all_ids.append(i)

        return all_ids

    def get_faqs_by_ids(self, faq_ids: list[str], max_results: int = 5) -> list[dict]:
        """Get full FAQ dicts by IDs. Returns up to max_results items.
        If less than max_results, returns all."""
        results = [self._faq_map[i] for i in faq_ids if i in self._faq_map]
        return results[:max_results]  # If < max_results, returns all

    def _parse_json_ids(self, text: str) -> list[str]:
        text = text.strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x) for x in data if x]
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                if isinstance(data, list):
                    return [str(x) for x in data if x]
            except json.JSONDecodeError:
                pass
        return []


# Global singleton
block_manager = FaqBlockManager()
