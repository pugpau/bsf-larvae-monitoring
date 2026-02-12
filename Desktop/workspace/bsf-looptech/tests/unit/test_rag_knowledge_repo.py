"""Unit tests for RAG knowledge repository."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from src.rag.knowledge_repo import (
    create_knowledge,
    get_knowledge_by_id,
    list_knowledge,
    search_knowledge,
    search_knowledge_text,
)
from src.rag.schemas import KnowledgeCreate


class TestCreateKnowledge:
    @pytest.mark.asyncio
    async def test_create_without_embedding(self, async_session):
        data = KnowledgeCreate(
            title="BSF基本情報",
            content="ブラックソルジャーフライの基本的な飼育情報。",
            source_type="manual",
        )
        result = await create_knowledge(async_session, data)
        assert result.title == "BSF基本情報"
        assert result.source_type == "manual"
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_with_metadata(self, async_session):
        data = KnowledgeCreate(
            title="テスト知識",
            content="テスト内容。",
            metadata_json={"category": "test", "priority": 1},
        )
        result = await create_knowledge(async_session, data)
        assert result.metadata_json == {"category": "test", "priority": 1}


class TestGetKnowledgeById:
    @pytest.mark.asyncio
    async def test_get_existing(self, async_session):
        data = KnowledgeCreate(title="取得テスト", content="内容")
        created = await create_knowledge(async_session, data)
        result = await get_knowledge_by_id(async_session, created.id)
        assert result is not None
        assert result.title == "取得テスト"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, async_session):
        result = await get_knowledge_by_id(async_session, uuid.uuid4())
        assert result is None


class TestSearchKnowledgeText:
    @pytest.mark.asyncio
    async def test_text_search(self, async_session):
        await create_knowledge(
            async_session,
            KnowledgeCreate(title="BSF温度管理", content="最適温度は27-30℃"),
        )
        await create_knowledge(
            async_session,
            KnowledgeCreate(title="配合比率", content="C/N比15-25"),
        )

        results = await search_knowledge_text(async_session, "温度")
        assert len(results) == 1
        assert results[0].title == "BSF温度管理"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, async_session):
        results = await search_knowledge_text(async_session, "存在しないキーワード")
        assert results == []


class TestSearchKnowledge:
    @pytest.mark.asyncio
    async def test_falls_back_to_text_when_no_embedding(self):
        mock_session = AsyncMock()

        with patch("src.rag.knowledge_repo.get_embedding", return_value=None), \
             patch("src.rag.knowledge_repo.search_knowledge_text", return_value=[]) as mock_text:
            results = await search_knowledge(mock_session, "テスト")
            mock_text.assert_awaited_once()
            assert results == []

    @pytest.mark.asyncio
    async def test_uses_vector_when_embedding_available(self):
        mock_session = AsyncMock()
        mock_results = [AsyncMock(id=uuid.uuid4(), title="Result", content="C", score=0.9)]

        with patch("src.rag.knowledge_repo.get_embedding", return_value=[0.1] * 768), \
             patch("src.rag.knowledge_repo.search_knowledge_vector", return_value=mock_results):
            results = await search_knowledge(mock_session, "テスト")
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_falls_back_when_vector_returns_empty(self):
        mock_session = AsyncMock()

        with patch("src.rag.knowledge_repo.get_embedding", return_value=[0.1] * 768), \
             patch("src.rag.knowledge_repo.search_knowledge_vector", return_value=[]), \
             patch("src.rag.knowledge_repo.search_knowledge_text", return_value=[]) as mock_text:
            results = await search_knowledge(mock_session, "テスト")
            mock_text.assert_awaited_once()


class TestListKnowledge:
    @pytest.mark.asyncio
    async def test_list_empty(self, async_session):
        results = await list_knowledge(async_session)
        assert results == []

    @pytest.mark.asyncio
    async def test_list_with_records(self, async_session):
        await create_knowledge(
            async_session, KnowledgeCreate(title="知識1", content="内容1"),
        )
        await create_knowledge(
            async_session, KnowledgeCreate(title="知識2", content="内容2"),
        )
        results = await list_knowledge(async_session)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, async_session):
        for i in range(5):
            await create_knowledge(
                async_session, KnowledgeCreate(title=f"知識{i}", content=f"内容{i}"),
            )
        results = await list_knowledge(async_session, limit=3)
        assert len(results) == 3
