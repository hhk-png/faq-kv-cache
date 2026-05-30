import pytest

from app.services.cache_service import build_faq_blocks
from app.core.config import settings


class TestCacheService:
    def test_build_faq_blocks_empty(self):
        l1_index, l1_prefix, l2_blocks = build_faq_blocks([])
        assert l1_index is not None
        assert l1_prefix == "[FAQ_CATEGORY_INDEX]"
        assert l2_blocks == []

    def test_build_faq_blocks_single_category(self):
        faqs = [
            {"id": "1", "category": "支付", "question": "Q1", "answer": "A1"},
            {"id": "2", "category": "支付", "question": "Q2", "answer": "A2"},
        ]
        l1_index, l1_prefix, l2_blocks = build_faq_blocks(faqs)
        assert "支付: 2条" in l1_index
        assert len(l2_blocks) == 1
        assert l2_blocks[0]["category"] == "支付"
        assert l2_blocks[0]["block_id"] == "BLOCK:支付:01"

    def test_build_faq_blocks_multiple_categories(self):
        faqs = [
            {"id": "1", "category": "支付", "question": "Q1", "answer": "A1"},
            {"id": "2", "category": "物流", "question": "Q2", "answer": "A2"},
            {"id": "3", "category": "账户", "question": "Q3", "answer": "A3"},
        ]
        l1_index, l1_prefix, l2_blocks = build_faq_blocks(faqs)
        for cat in ["支付", "物流", "账户"]:
            assert f"{cat}: 1条" in l1_index
        assert len(l2_blocks) == 3

    def test_build_faq_blocks_block_size(self):
        original_size = settings.faq_block_size
        settings.faq_block_size = 2
        faqs = [
            {"id": f"{i}", "category": "测试", "question": f"Q{i}", "answer": f"A{i}"}
            for i in range(5)
        ]
        l1_index, l1_prefix, l2_blocks = build_faq_blocks(faqs)
        # 5 items in blocks of 2 = 3 blocks
        assert len(l2_blocks) == 3
        assert l2_blocks[0]["block_id"] == "BLOCK:测试:01"
        assert l2_blocks[1]["block_id"] == "BLOCK:测试:02"
        assert l2_blocks[2]["block_id"] == "BLOCK:测试:03"
        assert len(l2_blocks[0]["faq_ids"]) == 2
        assert len(l2_blocks[1]["faq_ids"]) == 2
        assert len(l2_blocks[2]["faq_ids"]) == 1
        settings.faq_block_size = original_size
