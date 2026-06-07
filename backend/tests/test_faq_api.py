import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.storage.file_store import get_faq_store


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_faq(client):
    resp = await client.post("/api/faqs", json={
        "category": "支付",
        "question": "如何退款？",
        "answer": "在订单页面操作。",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["category"] == "支付"
    assert data["data"]["question"] == "如何退款？"


@pytest.mark.asyncio
async def test_create_faq_missing_field(client):
    resp = await client.post("/api/faqs", json={"category": "测试"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_faqs(client):
    # Create some FAQs first
    await client.post("/api/faqs", json={"category": "A", "question": "Q1", "answer": "A1"})
    await client.post("/api/faqs", json={"category": "B", "question": "Q2", "answer": "A2"})
    resp = await client.get("/api/faqs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_faq(client):
    create_resp = await client.post("/api/faqs", json={
        "category": "C", "question": "Q?", "answer": "A!"
    })
    faq_id = create_resp.json()["data"]["id"]
    resp = await client.get(f"/api/faqs/{faq_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == faq_id


@pytest.mark.asyncio
async def test_get_faq_not_found(client):
    resp = await client.get("/api/faqs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_faq(client):
    create_resp = await client.post("/api/faqs", json={
        "category": "D", "question": "Old?", "answer": "Old"
    })
    faq_id = create_resp.json()["data"]["id"]
    resp = await client.put(f"/api/faqs/{faq_id}", json={"question": "New?"})
    assert resp.status_code == 200
    assert resp.json()["data"]["question"] == "New?"


@pytest.mark.asyncio
async def test_delete_faq(client):
    create_resp = await client.post("/api/faqs", json={
        "category": "E", "question": "Q?", "answer": "A"
    })
    faq_id = create_resp.json()["data"]["id"]
    resp = await client.delete(f"/api/faqs/{faq_id}")
    assert resp.status_code == 200
    # Verify deleted
    resp = await client.get(f"/api/faqs/{faq_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_create_faqs(client):
    resp = await client.post("/api/faqs/batch", json={
        "items": [
            {"category": "X", "question": "Q1", "answer": "A1"},
            {"category": "Y", "question": "Q2", "answer": "A2"},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
@patch("app.services.qa_service.chat_completion_stream")
async def test_qa_ask_no_faqs(mock_stream, client):
    """When no FAQs exist, block manager returns no candidates."""
    async def _gen(*args, **kwargs):
        yield "测试回答"
    mock_stream.side_effect = _gen
    resp = await client.post("/api/qa/ask", json={
        "question": "你好",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["answer"] is not None


@pytest.mark.asyncio
async def test_qa_ask_empty_question(client):
    resp = await client.post("/api/qa/ask", json={
        "question": "",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_document_upload_no_file(client):
    resp = await client.post("/api/documents/upload")
    assert resp.status_code == 422  # FastAPI validation error for missing file


@pytest.mark.asyncio
async def test_document_list(client):
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
    assert "data" in resp.json()
