"""
FAQ Block Manager

Splits FAQs into per-category blocks for KV cache.
Search flow: LLM matches categories → sample from matched categories.
"""
import asyncio
import json
import logging
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from app.storage.file_store import get_all_faqs
from app.core.llm_client import chat_completion, cache_warmup_completion, build_prefix_cache_request
from app.core.config import settings

logger = logging.getLogger(__name__)

CATEGORY_MATCH_PROMPT = """你是一个医疗FAQ分类专家。请判断以下类别中哪些与用户问题相关。

类别列表：
{category_list}

用户问题：{question}

返回一个JSON对象，格式为 {{"categories": ["类别1", "类别2", ...]}}。
如果都不相关则返回 {{"categories": []}}。"""


@dataclass
class FaqBlock:
    block_id: str
    prefix: str
    content: str
    faq_ids: list[str] = field(default_factory=list)


class FaqBlockManager:
    """Manages per-category FAQ blocks for KV-cache accelerated search."""

    def __init__(self):
        self._category_blocks: dict[str, list[FaqBlock]] = {}
        self._category_list: list[str] = []
        self._faq_map: dict[str, dict] = {}

    @property
    def block_count(self) -> int:
        return sum(len(blocks) for blocks in self._category_blocks.values())

    @property
    def category_count(self) -> int:
        return len(self._category_list)

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text) / 1.3)

    def _load_all_faqs(self) -> list[dict]:
        faqs = get_all_faqs()
        for faq in faqs:
            if "id" not in faq or not faq["id"]:
                faq["id"] = uuid.uuid4().hex[:12]
        self._faq_map = {faq["id"]: faq for faq in faqs}
        return faqs

    def _build_block_content(self, faq_list: list[dict]) -> str:
        parts = []
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

    def rebuild_blocks(self):
        """Build blocks grouped by category."""
        faqs = self._load_all_faqs()
        if not faqs:
            self._category_blocks = {}
            self._category_list = []
            logger.info("No FAQs to build blocks from")
            return

        # Group FAQs by category
        grouped: dict[str, list[dict]] = defaultdict(list)
        for faq in faqs:
            cat = faq.get("category", "未分类")
            grouped[cat].append(faq)

        min_tokens = settings.faq_block_min_tokens
        cat_blocks: dict[str, list[FaqBlock]] = {}
        total_blocks = 0

        for cat_name, cat_faqs in sorted(grouped.items()):
            blocks: list[FaqBlock] = []
            current: list[dict] = []
            content = ""
            seq = 0

            def _flush():
                nonlocal current, content, seq
                if not current:
                    return
                seq += 1
                c = self._build_block_content(current)
                blocks.append(FaqBlock(
                    block_id=f"{cat_name}:{seq:03d}",
                    prefix=f"[CAT:{cat_name}:{seq:03d}]",
                    content=c,
                    faq_ids=[f["id"] for f in current],
                ))
                logger.info(f"  Block [{cat_name}:{seq:03d}]: {len(current)} FAQs, ~{self._estimate_tokens(c)} tokens")
                current = []
                content = ""

            for faq in cat_faqs:
                faq_text = f"问题: {faq['question']}\n答案: {faq['answer']}\n"
                if current and self._estimate_tokens(content) >= min_tokens:
                    _flush()
                current.append(faq)
                content += faq_text + "\n"

            _flush()
            if blocks:
                cat_blocks[cat_name] = blocks
                total_blocks += len(blocks)

        self._category_blocks = cat_blocks
        self._category_list = sorted(grouped.keys())
        logger.info(
            f"Built {total_blocks} blocks across {len(cat_blocks)} categories "
            f"from {len(faqs)} FAQs"
        )

    async def warmup_all_blocks(self):
        """Warm up blocks per category concurrently."""
        if not self._category_blocks:
            logger.warning("No blocks to warm up")
            return

        all_blocks = [
            b for blocks in self._category_blocks.values() for b in blocks
        ]

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

        results = await asyncio.gather(*[_warm_one(b) for b in all_blocks])
        success = sum(1 for r in results if r["status"] == "success")
        logger.info(f"Warmup complete: {success}/{len(results)} blocks success")

    async def _match_categories(self, question: str) -> list[str]:
        """Stage 1: Use LLM to select relevant categories (only current question, no history)."""
        if not self._category_list:
            return []

        cat_list = "\n".join(f"- {c}" for c in self._category_list)

        try:
            result = await chat_completion(
                messages=[
                    {"role": "system", "content": "你是一个精确的查找类别的助手，只返回JSON。"},
                    {"role": "user", "content": CATEGORY_MATCH_PROMPT.format(
                        category_list=cat_list, question=question
                    )},
                ],
                model=settings.llm_model,
                max_tokens=300,
                temperature=0,
                response_format={"type": "json_object"},
            )
            matched = self._parse_json_ids(result)
            if matched is not None:
                # LLM responded successfully (may be empty = "no relevant categories")
                valid = [c for c in matched if c in self._category_blocks]
                if valid:
                    logger.info(f"Matched categories: {valid}")
                return valid  # [] means LLM explicitly said none
        except Exception as e:
            logger.error(f"Category matching error: {e}")

        # Fallback: only when LLM failed to respond (parse error / exception)
        logger.info("Category matching failed, falling back to all categories")
        return list(self._category_blocks.keys())

    async def match_categories(self, question: str) -> list[str]:
        """Step 1: Use LLM to select relevant categories. Returns category names."""
        return await self._match_categories(question)

    async def search_ids_in_blocks(
        self, categories: list[str], question: str, history: list[dict] | None = None
    ) -> list[str]:
        """Step 2: Search FAQ IDs within given categories' KV-cached blocks."""
        if not categories or not self._category_blocks:
            return []

        blocks_to_search = [
            b for cat in categories for b in self._category_blocks.get(cat, [])
        ]
        if not blocks_to_search:
            return []

        logger.info(
            f"Searching {len(blocks_to_search)} blocks across {len(categories)} categories (KV-cached)"
        )

        conv_parts = []
        if history:
            for msg in history[-3:]:
                role = "用户" if msg["role"] == "user" else "助手"
                conv_parts.append(f"{role}: {msg['content']}")
        conv_parts.append(f"用户: {question}")
        conv_context = "\n".join(conv_parts)

        search_prompt = (
            "你是一个FAQ检索专家。仔细阅读上面的FAQ内容，"
            "找出与当前对话相关的FAQ。\n\n"
            "返回一个JSON对象，格式为 [\"id1\", \"id2\", ...]\n"
            "如果都不相关则返回 []。\n"
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
                    max_tokens=1000,
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                if result and not result.endswith("\"]"):
                    result += "\"]"
                ids = self._parse_json_ids(result)
                if ids is not None:
                    valid = [i for i in ids if i in self._faq_map]
                    logger.info(f"Block {block.block_id}: parsed {len(ids)} IDs, {len(valid)} valid — {valid if valid else '全部不在_faq_map中'}")
                    if valid:
                        return valid
                else:
                    logger.info(f"Block {block.block_id}: 解析失败, raw: {result.strip()}")
                return []
            except Exception as e:
                logger.error(f"Block {block.block_id} search error: {e}")
                return []

        results = await asyncio.gather(*[_search_block(b) for b in blocks_to_search])

        seen: set[str] = set()
        all_ids: list[str] = []
        for ids in results:
            for i in ids:
                if i not in seen:
                    seen.add(i)
                    all_ids.append(i)

        return all_ids

    def get_faqs_by_ids(self, faq_ids: list[str], max_results: int = 5) -> list[dict]:
        results = [self._faq_map[i] for i in faq_ids if i in self._faq_map]
        return results[:max_results]

    def _parse_json_ids(self, text: str) -> list[str] | None:
        """Parse JSON array of ID strings from LLM output. Returns None if parsing failed."""
        text = text.strip()
        try:
            data = json.loads(text)
            result = self._extract_list(data)
            if result is not None:
                return result
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                result = self._extract_list(data)
                if result is not None:
                    return result
            except json.JSONDecodeError:
                pass
        # Fallback: find [...] array in text (handles LLM appending explanatory text)
        match = re.search(r"(\[[^\]]+\])", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                result = self._extract_list(data)
                if result is not None:
                    return result
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _extract_list(data) -> list[str] | None:
        """Extract string list from a JSON value — supports array or object with a list value."""
        if isinstance(data, list):
            return [str(x) for x in data if x]
        if isinstance(data, dict):
            # {"faq_ids": [...], ...} → find the first list value
            for v in data.values():
                if isinstance(v, list):
                    return [str(x) for x in v if x]
        return None


# Global singleton
block_manager = FaqBlockManager()
