"""Unit tests for RAG embedding service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.embedding import get_embedding, get_embeddings_batch, EMBEDDING_DIM


def _make_mock_client(response):
    """Create a mock AsyncClient that returns the given response from post()."""
    mock_client = AsyncMock()
    mock_client.post.return_value = response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestGetEmbedding:
    @pytest.mark.asyncio
    async def test_successful_embedding(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * EMBEDDING_DIM}]
        }

        with patch("httpx.AsyncClient", return_value=_make_mock_client(mock_response)):
            result = await get_embedding("test text")

        assert result is not None
        assert len(result) == EMBEDDING_DIM
        assert result[0] == 0.1

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient", return_value=_make_mock_client(mock_response)):
            result = await get_embedding("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_none(self):
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await get_embedding("test text")

        assert result is None

    @pytest.mark.asyncio
    async def test_unexpected_dimension_still_returns(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.5] * 384}]  # wrong dim
        }

        with patch("httpx.AsyncClient", return_value=_make_mock_client(mock_response)):
            result = await get_embedding("test text")

        assert result is not None
        assert len(result) == 384


class TestGetEmbeddingsBatch:
    @pytest.mark.asyncio
    async def test_batch_returns_aligned_results(self):
        call_count = 0

        async def mock_get_embedding(text):
            nonlocal call_count
            call_count += 1
            return [float(call_count)] * EMBEDDING_DIM

        with patch("src.rag.embedding.get_embedding", side_effect=mock_get_embedding):
            results = await get_embeddings_batch(["text1", "text2", "text3"])

        assert len(results) == 3
        assert results[0][0] == 1.0
        assert results[1][0] == 2.0
        assert results[2][0] == 3.0

    @pytest.mark.asyncio
    async def test_batch_with_failures(self):
        async def mock_get_embedding(text):
            if "fail" in text:
                return None
            return [0.1] * EMBEDDING_DIM

        with patch("src.rag.embedding.get_embedding", side_effect=mock_get_embedding):
            results = await get_embeddings_batch(["ok", "fail", "ok2"])

        assert len(results) == 3
        assert results[0] is not None
        assert results[1] is None
        assert results[2] is not None
