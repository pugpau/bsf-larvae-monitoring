"""Embedding service — wraps LM Studio /v1/embeddings endpoint."""

import asyncio
import logging
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
EMBEDDING_DIM = 768
_TIMEOUT = 30.0


async def get_embedding(text: str) -> Optional[list[float]]:
    """Get embedding vector for a single text string.

    Returns None if LM Studio is unreachable or the model is unavailable.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/embeddings",
                json={"model": EMBEDDING_MODEL, "input": text},
                timeout=_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning("Embedding API returned %d: %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            embedding = data.get("data", [{}])[0].get("embedding", [])
            if len(embedding) != EMBEDDING_DIM:
                logger.warning("Unexpected embedding dim: %d (expected %d)", len(embedding), EMBEDDING_DIM)
            return embedding
    except httpx.ConnectError:
        logger.warning("LM Studio not reachable at %s", settings.LLM_BASE_URL)
        return None
    except Exception as e:
        logger.error("Embedding error: %s", e)
        return None


async def get_embeddings_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Get embeddings for multiple texts with concurrency limit.

    Uses asyncio.gather with a semaphore to limit concurrent requests
    to LM Studio (default: 5 concurrent).
    """
    semaphore = asyncio.Semaphore(5)

    async def _get(t: str) -> Optional[list[float]]:
        async with semaphore:
            return await get_embedding(t)

    return list(await asyncio.gather(*[_get(t) for t in texts]))
