"""Unit tests for RAG chat repository."""

import uuid

import pytest

from src.database.postgresql import ChatSession, ChatMessage
from src.rag import chat_repo


@pytest.fixture
async def chat_session_id(async_session):
    """Create a chat session and return its ID."""
    session = await chat_repo.create_session(async_session, title="Test Chat")
    return session.id


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_create_default_title(self, async_session):
        session = await chat_repo.create_session(async_session)
        assert session.title == "New Chat"
        assert session.id is not None
        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_create_custom_title(self, async_session):
        session = await chat_repo.create_session(async_session, title="BSF相談")
        assert session.title == "BSF相談"

    @pytest.mark.asyncio
    async def test_create_with_user_id(self, async_session):
        uid = uuid.uuid4()
        session = await chat_repo.create_session(async_session, user_id=uid)
        assert session.user_id is not None


class TestGetSession:
    @pytest.mark.asyncio
    async def test_get_existing(self, async_session, chat_session_id):
        session = await chat_repo.get_session(async_session, chat_session_id)
        assert session is not None
        assert session.title == "Test Chat"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, async_session):
        result = await chat_repo.get_session(async_session, uuid.uuid4())
        assert result is None


class TestListSessions:
    @pytest.mark.asyncio
    async def test_list_empty(self, async_session):
        sessions = await chat_repo.list_sessions(async_session)
        assert sessions == []

    @pytest.mark.asyncio
    async def test_list_multiple(self, async_session):
        await chat_repo.create_session(async_session, title="Chat 1")
        await chat_repo.create_session(async_session, title="Chat 2")
        sessions = await chat_repo.list_sessions(async_session)
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_list_with_limit(self, async_session):
        for i in range(5):
            await chat_repo.create_session(async_session, title=f"Chat {i}")
        sessions = await chat_repo.list_sessions(async_session, limit=3)
        assert len(sessions) == 3


class TestDeleteSession:
    @pytest.mark.asyncio
    async def test_delete_existing(self, async_session, chat_session_id):
        result = await chat_repo.delete_session(async_session, chat_session_id)
        assert result is True
        # Verify deleted
        session = await chat_repo.get_session(async_session, chat_session_id)
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, async_session):
        result = await chat_repo.delete_session(async_session, uuid.uuid4())
        assert result is False


class TestAddMessage:
    @pytest.mark.asyncio
    async def test_add_user_message(self, async_session, chat_session_id):
        msg = await chat_repo.add_message(
            async_session, chat_session_id, "user", "BSFの温度は？"
        )
        assert msg.role == "user"
        assert msg.content == "BSFの温度は？"
        assert msg.session_id == chat_session_id

    @pytest.mark.asyncio
    async def test_add_assistant_message_with_context(self, async_session, chat_session_id):
        ctx = [{"id": "123", "title": "BSF飼育", "score": 0.9}]
        msg = await chat_repo.add_message(
            async_session, chat_session_id, "assistant", "27-30℃です。",
            context_chunks=ctx, token_count=15,
        )
        assert msg.role == "assistant"
        assert msg.token_count == 15
        assert msg.context_chunks is not None


class TestGetSessionMessages:
    @pytest.mark.asyncio
    async def test_ordered_messages(self, async_session, chat_session_id):
        await chat_repo.add_message(async_session, chat_session_id, "user", "質問1")
        await chat_repo.add_message(async_session, chat_session_id, "assistant", "回答1")
        await chat_repo.add_message(async_session, chat_session_id, "user", "質問2")

        messages = await chat_repo.get_session_messages(async_session, chat_session_id)
        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"

    @pytest.mark.asyncio
    async def test_empty_session(self, async_session, chat_session_id):
        messages = await chat_repo.get_session_messages(async_session, chat_session_id)
        assert messages == []
