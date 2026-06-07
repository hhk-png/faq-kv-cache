"""Tests for FaqBlockManager — match_categories + search_ids_in_blocks."""
import pytest
from unittest.mock import patch

from app.services.block_manager import FaqBlockManager


@pytest.fixture
def block_mgr():
    mgr = FaqBlockManager()
    mgr._category_blocks = {
        "口腔癌": [
            type("FaqBlock", (), {
                "block_id": "口腔癌:001",
                "prefix": "[CAT:口腔癌:001]",
                "content": "口腔癌相关FAQ内容",
                "faq_ids": [f"oral_{i}" for i in range(20)],
            })()
        ],
        "乳腺纤维腺瘤": [
            type("FaqBlock", (), {
                "block_id": "乳腺纤维腺瘤:001",
                "prefix": "[CAT:乳腺纤维腺瘤:001]",
                "content": "乳腺纤维腺瘤相关FAQ内容",
                "faq_ids": [f"breast_{i}" for i in range(30)],
            })()
        ],
    }
    mgr._category_list = ["口腔癌", "乳腺纤维腺瘤"]
    mgr._faq_map = {}
    for cat, blocks in mgr._category_blocks.items():
        for b in blocks:
            for fid in b.faq_ids:
                mgr._faq_map[fid] = {
                    "id": fid, "category": cat,
                    "question": f"{cat}问题", "answer": f"{cat}答案",
                }
    return mgr


class TestMatchCategories:
    """match_categories — LLM selects relevant categories."""

    @patch("app.services.block_manager.chat_completion")
    async def test_matches_relevant_categories(self, mock_chat, block_mgr):
        mock_chat.return_value = '["口腔癌"]'
        cats = await block_mgr.match_categories("口腔癌怎么治")
        assert cats == ["口腔癌"]

    @patch("app.services.block_manager.chat_completion")
    async def test_returns_empty_when_none_match(self, mock_chat, block_mgr):
        mock_chat.return_value = "[]"
        cats = await block_mgr.match_categories("你好，今天天气怎么样")
        assert cats == []

    @patch("app.services.block_manager.chat_completion")
    async def test_fallback_all_categories_on_parse_error(self, mock_chat, block_mgr):
        mock_chat.return_value = "garbage"
        cats = await block_mgr.match_categories("随便问问")
        assert set(cats) == {"口腔癌", "乳腺纤维腺瘤"}


class TestSearchIdsInBlocks:
    """search_ids_in_blocks — LLM finds specific FAQ IDs in KV-cached blocks."""

    @patch("app.services.block_manager.chat_completion")
    async def test_returns_specific_ids(self, mock_chat, block_mgr):
        mock_chat.side_effect = [
            '["oral_0", "oral_3", "oral_7"]',  # 口腔癌 block search
        ]
        ids = await block_mgr.search_ids_in_blocks(["口腔癌"], "口腔癌怎么治")
        assert ids == ["oral_0", "oral_3", "oral_7"]

    @patch("app.services.block_manager.chat_completion")
    async def test_multiple_blocks_deduplicated(self, mock_chat, block_mgr):
        block_mgr._category_blocks["口腔癌"].append(
            type("FaqBlock", (), {
                "block_id": "口腔癌:002",
                "prefix": "[CAT:口腔癌:002]",
                "content": "更多内容",
                "faq_ids": [f"oral_{i}" for i in range(10, 30)],
            })()
        )
        mock_chat.side_effect = [
            '["oral_5", "oral_10"]',   # block 1
            '["oral_10", "oral_15"]',  # block 2 (oral_10 overlaps)
        ]
        ids = await block_mgr.search_ids_in_blocks(["口腔癌"], "口腔癌问题")
        assert ids == ["oral_5", "oral_10", "oral_15"]

    @patch("app.services.block_manager.chat_completion")
    async def test_returns_empty_when_none_found(self, mock_chat, block_mgr):
        mock_chat.return_value = "[]"
        ids = await block_mgr.search_ids_in_blocks(["口腔癌", "乳腺纤维腺瘤"], "不相关的问题")
        assert ids == []

    async def test_returns_empty_for_no_blocks(self, block_mgr):
        ids = await block_mgr.search_ids_in_blocks([], "test")
        assert ids == []

    async def test_returns_empty_for_unknown_categories(self, block_mgr):
        ids = await block_mgr.search_ids_in_blocks(["不存在的类别"], "test")
        assert ids == []
