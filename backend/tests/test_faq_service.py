import pytest

from app.services.faq_service import (
    list_faqs,
    get_faq,
    create_faq,
    update_faq,
    delete_faq,
    batch_create_faqs,
    get_categories,
)
from app.storage.file_store import get_all_faqs


class TestFaqService:
    def test_create_faq(self):
        faq = create_faq({
            "category": "测试",
            "question": "测试问题？",
            "answer": "测试答案",
            "tags": ["测试"],
        })
        assert faq["id"] is not None
        assert faq["category"] == "测试"
        assert faq["question"] == "测试问题？"
        assert "created_at" in faq
        assert "updated_at" in faq

    def test_list_faqs(self):
        create_faq({"category": "A", "question": "Q1", "answer": "A1"})
        create_faq({"category": "B", "question": "Q2", "answer": "A2"})
        items = list_faqs()
        assert len(items) == 2

    def test_list_faqs_filter_by_category(self):
        create_faq({"category": "支付", "question": "Q1", "answer": "A1"})
        create_faq({"category": "物流", "question": "Q2", "answer": "A2"})
        items = list_faqs(category="支付")
        assert len(items) == 1
        assert items[0]["category"] == "支付"

    def test_list_faqs_filter_by_keyword(self):
        create_faq({"category": "A", "question": "如何退款", "answer": "等待退款", "tags": ["退款"]})
        create_faq({"category": "B", "question": "如何发货", "answer": "等待发货", "tags": ["物流"]})
        items = list_faqs(keyword="退款")
        assert len(items) == 1

    def test_get_faq(self):
        faq = create_faq({"category": "C", "question": "Q?", "answer": "A!"})
        found = get_faq(faq["id"])
        assert found is not None
        assert found["question"] == "Q?"
        assert get_faq("nonexistent") is None

    def test_update_faq(self):
        faq = create_faq({"category": "C", "question": "Old?", "answer": "Old"})
        updated = update_faq(faq["id"], {"question": "New?"})
        assert updated["question"] == "New?"
        assert updated["updated_at"] != faq["created_at"]

    def test_delete_faq(self):
        faq = create_faq({"category": "C", "question": "Q?", "answer": "A"})
        assert delete_faq(faq["id"]) is True
        assert get_faq(faq["id"]) is None
        assert delete_faq("nonexistent") is False

    def test_batch_create_faqs(self):
        items = [
            {"category": "A", "question": "Q1", "answer": "A1"},
            {"category": "B", "question": "Q2", "answer": "A2"},
        ]
        created = batch_create_faqs(items)
        assert len(created) == 2
        assert len(get_all_faqs()) == 2

    def test_get_categories(self):
        create_faq({"category": "支付", "question": "Q1", "answer": "A1"})
        create_faq({"category": "支付", "question": "Q2", "answer": "A2"})
        create_faq({"category": "物流", "question": "Q3", "answer": "A3"})
        cats = get_categories()
        assert len(cats) == 2
        cat_map = {c["name"]: c["count"] for c in cats}
        assert cat_map["支付"] == 2
        assert cat_map["物流"] == 1
