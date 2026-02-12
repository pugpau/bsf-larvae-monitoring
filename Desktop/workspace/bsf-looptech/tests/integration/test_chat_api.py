"""Integration tests for Chat & Knowledge API endpoints (Phase 4)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing."""
    from src.database.postgresql import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestChatSessionEndpoints:
    @pytest.mark.asyncio
    async def test_create_session(self, client):
        resp = await client.post("/api/v1/chat/sessions", json={"title": "テストチャット"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "テストチャット"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_session_default_title(self, client):
        resp = await client.post("/api/v1/chat/sessions", json={})
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Chat"

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client):
        resp = await client.get("/api/v1/chat/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_sessions_after_create(self, client):
        await client.post("/api/v1/chat/sessions", json={"title": "Session 1"})
        await client.post("/api/v1/chat/sessions", json={"title": "Session 2"})
        resp = await client.get("/api/v1/chat/sessions")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    @pytest.mark.asyncio
    async def test_get_session_detail(self, client):
        create_resp = await client.post("/api/v1/chat/sessions", json={"title": "Detail Test"})
        session_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Detail Test"
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/chat/sessions/{fake_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session(self, client):
        create_resp = await client.post("/api/v1/chat/sessions", json={"title": "Delete Me"})
        session_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify deleted
        resp = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/v1/chat/sessions/{fake_id}")
        assert resp.status_code == 404


class TestChatAskEndpoint:
    @pytest.mark.asyncio
    async def test_ask_requires_valid_session(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.post("/api/v1/chat/ask", json={
            "session_id": fake_id,
            "question": "テスト質問",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ask_with_mock_llm(self, client):
        # Create session first
        create_resp = await client.post("/api/v1/chat/sessions", json={"title": "Ask Test"})
        session_id = create_resp.json()["id"]

        # Mock the RAG pipeline
        from src.rag.schemas import ChatResponse
        mock_response = ChatResponse(
            session_id=session_id,
            answer="BSFの最適温度は27-30℃です。",
            context=[],
            token_count=20,
        )

        with patch("src.api.routes.chat.ask_with_rag", return_value=mock_response):
            resp = await client.post("/api/v1/chat/ask", json={
                "session_id": session_id,
                "question": "BSFの温度は？",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert "27-30℃" in data["answer"]


class TestKnowledgeEndpoints:
    @pytest.mark.asyncio
    async def test_create_knowledge(self, client):
        with patch("src.api.routes.chat.get_embedding", return_value=None):
            resp = await client.post("/api/v1/knowledge", json={
                "title": "テスト知識",
                "content": "BSF幼虫の飼育情報。",
                "source_type": "manual",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "テスト知識"

    @pytest.mark.asyncio
    async def test_list_knowledge(self, client):
        with patch("src.api.routes.chat.get_embedding", return_value=None):
            await client.post("/api/v1/knowledge", json={
                "title": "知識A", "content": "内容A",
            })
        resp = await client.get("/api/v1/knowledge")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_seed_knowledge(self, client):
        with patch("src.api.routes.chat.seed_knowledge", return_value=5):
            resp = await client.post("/api/v1/knowledge/seed")
        assert resp.status_code == 200
        assert resp.json()["records_created"] == 5
