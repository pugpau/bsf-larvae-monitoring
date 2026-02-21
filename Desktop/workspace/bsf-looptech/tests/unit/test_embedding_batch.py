"""Unit tests for embedding batch processing (Phase 2-6)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.unit
class TestGetEmbeddingsBatch:
    """Tests for get_embeddings_batch with concurrency."""

    @pytest.mark.asyncio
    async def test_batch_returns_aligned_results(self):
        """Each input text should have a corresponding embedding."""
        fake_embeddings = [[0.1] * 768, [0.2] * 768, [0.3] * 768]

        with patch("src.rag.embedding.get_embedding", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = fake_embeddings

            from src.rag.embedding import get_embeddings_batch

            results = await get_embeddings_batch(["text1", "text2", "text3"])

        assert len(results) == 3
        assert results[0] == fake_embeddings[0]
        assert results[1] == fake_embeddings[1]
        assert results[2] == fake_embeddings[2]

    @pytest.mark.asyncio
    async def test_batch_handles_none_embeddings(self):
        """When LM Studio is down, get_embedding returns None."""
        with patch("src.rag.embedding.get_embedding", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            from src.rag.embedding import get_embeddings_batch

            results = await get_embeddings_batch(["a", "b"])

        assert results == [None, None]
        assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        """Empty input should return empty list."""
        from src.rag.embedding import get_embeddings_batch

        results = await get_embeddings_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_single_item(self):
        """Single item should work like get_embedding."""
        fake = [0.5] * 768

        with patch("src.rag.embedding.get_embedding", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = fake

            from src.rag.embedding import get_embeddings_batch

            results = await get_embeddings_batch(["single"])

        assert len(results) == 1
        assert results[0] == fake

    @pytest.mark.asyncio
    async def test_batch_concurrency_limited(self):
        """Semaphore should limit concurrent calls to 5."""
        max_concurrent = 0
        current = 0
        lock = asyncio.Lock()

        async def _tracking_embedding(text: str):
            nonlocal max_concurrent, current
            async with lock:
                current += 1
                if current > max_concurrent:
                    max_concurrent = current
            await asyncio.sleep(0.01)
            async with lock:
                current -= 1
            return [0.1] * 768

        with patch("src.rag.embedding.get_embedding", side_effect=_tracking_embedding):
            from src.rag.embedding import get_embeddings_batch

            await get_embeddings_batch([f"text_{i}" for i in range(10)])

        assert max_concurrent <= 5, f"Max concurrent was {max_concurrent}, expected <= 5"

    @pytest.mark.asyncio
    async def test_batch_mixed_success_failure(self):
        """Some embeddings succeed, some fail — results should be aligned."""
        side_effects = [
            [0.1] * 768,
            None,
            [0.3] * 768,
            None,
        ]

        with patch("src.rag.embedding.get_embedding", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = side_effects

            from src.rag.embedding import get_embeddings_batch

            results = await get_embeddings_batch(["a", "b", "c", "d"])

        assert len(results) == 4
        assert results[0] == [0.1] * 768
        assert results[1] is None
        assert results[2] == [0.3] * 768
        assert results[3] is None
