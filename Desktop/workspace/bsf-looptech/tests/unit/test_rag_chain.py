"""Unit tests for RAG chain."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.chain import _build_context, _call_llm, ask_with_rag
from src.rag.schemas import KnowledgeSearchResult


class TestBuildContext:
    def test_empty_results(self):
        result = _build_context([])
        assert "コンテキスト情報はありません" in result

    def test_formats_results(self):
        results = [
            KnowledgeSearchResult(
                id="00000000-0000-0000-0000-000000000001",
                title="BSF飼育", content="温度は27-30℃", score=0.9,
            ),
            KnowledgeSearchResult(
                id="00000000-0000-0000-0000-000000000002",
                title="配合比率", content="C/N比15-25", score=0.8,
            ),
        ]
        text = _build_context(results)
        assert "[1] BSF飼育" in text
        assert "[2] 配合比率" in text
        assert "27-30℃" in text


class TestCallLlm:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "回答テキスト"}}],
            "usage": {"completion_tokens": 42},
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            answer, tokens = await _call_llm("テスト質問")

        assert answer == "回答テキスト"
        assert tokens == 42

    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            answer, tokens = await _call_llm("テスト")

        assert "接続できません" in answer
        assert tokens is None

    @pytest.mark.asyncio
    async def test_connection_error(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            answer, tokens = await _call_llm("テスト")

        assert "起動していません" in answer


class TestAskWithRag:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        mock_session = AsyncMock()

        mock_search_results = [
            KnowledgeSearchResult(
                id="00000000-0000-0000-0000-000000000001",
                title="BSF温度", content="27-30℃が最適", score=0.95,
            ),
        ]

        with patch("src.rag.chain.search_knowledge", return_value=mock_search_results), \
             patch("src.rag.chain._call_llm", return_value=("BSFの最適温度は27-30℃です。", 30)):
            response = await ask_with_rag(
                mock_session, "BSFの最適温度は？", "00000000-0000-0000-0000-000000000099",
            )

        assert "27-30℃" in response.answer
        assert len(response.context) == 1
        assert response.token_count == 30

    @pytest.mark.asyncio
    async def test_no_context_still_answers(self):
        mock_session = AsyncMock()

        with patch("src.rag.chain.search_knowledge", return_value=[]), \
             patch("src.rag.chain._call_llm", return_value=("一般的な知識に基づく回答", None)):
            response = await ask_with_rag(mock_session, "質問", "00000000-0000-0000-0000-000000000099")

        assert response.answer == "一般的な知識に基づく回答"
        assert response.context == []
