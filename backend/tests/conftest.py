import pytest
import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment with temporary data directory."""
    tmp_dir = tempfile.mkdtemp()
    original_data_dir = settings.data_dir
    original_faq_dataset = settings.faq_dataset_path

    settings.data_dir = tmp_dir
    settings.faq_dataset_path = os.path.join(tmp_dir, "faq_dataset")

    # Ensure directories exist
    os.makedirs(tmp_dir, exist_ok=True)

    yield

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)
    settings.data_dir = original_data_dir
    settings.faq_dataset_path = original_faq_dataset


@pytest.fixture
def sample_faqs():
    """Provide sample FAQ data."""
    return [
        {
            "category": "支付",
            "question": "如何申请退款？",
            "answer": "在订单页面点击申请退款按钮。",
            "tags": ["退款", "售后"],
        },
        {
            "category": "支付",
            "question": "支持哪些支付方式？",
            "answer": "微信支付、支付宝、银行卡。",
            "tags": ["支付方式"],
        },
        {
            "category": "物流",
            "question": "发货后多长时间能到？",
            "answer": "同城1-2天，跨省3-7天。",
            "tags": ["物流", "配送"],
        },
    ]
