"""Repository for substrate_knowledge table — CRUD + vector similarity search."""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.postgresql import SubstrateKnowledge
from src.rag.embedding import get_embedding
from src.rag.schemas import KnowledgeCreate, KnowledgeResponse, KnowledgeSearchResult

logger = logging.getLogger(__name__)


async def create_knowledge(
    session: AsyncSession,
    data: KnowledgeCreate,
    embedding: Optional[list[float]] = None,
) -> KnowledgeResponse:
    """Insert a knowledge record with optional embedding vector."""
    record = SubstrateKnowledge(
        id=uuid.uuid4(),
        title=data.title,
        content=data.content,
        source_type=data.source_type,
        metadata_json=data.metadata_json,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(record)
    await session.flush()

    # Set embedding via raw SQL (pgvector type not available in SQLite ORM)
    if embedding is not None:
        vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await session.execute(
            text("UPDATE substrate_knowledge SET embedding = :vec WHERE id = :id"),
            {"vec": vec_str, "id": str(record.id)},
        )

    await session.commit()
    await session.refresh(record)
    return KnowledgeResponse.model_validate(record)


async def get_knowledge_by_id(
    session: AsyncSession,
    knowledge_id: uuid.UUID,
) -> Optional[KnowledgeResponse]:
    """Get a single knowledge record by ID."""
    record = await session.get(SubstrateKnowledge, knowledge_id)
    if record is None:
        return None
    return KnowledgeResponse.model_validate(record)


async def search_knowledge_vector(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int = 5,
) -> list[KnowledgeSearchResult]:
    """Search knowledge base by cosine similarity (pgvector <=> operator)."""
    vec_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
    result = await session.execute(
        text(
            "SELECT id, title, content, embedding <=> :vec AS distance "
            "FROM substrate_knowledge "
            "WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> :vec "
            "LIMIT :limit"
        ),
        {"vec": vec_str, "limit": limit},
    )
    rows = result.fetchall()
    return [
        KnowledgeSearchResult(
            id=row[0],
            title=row[1],
            content=row[2],
            score=1.0 - float(row[3]),  # convert distance to similarity
        )
        for row in rows
    ]


async def search_knowledge_text(
    session: AsyncSession,
    query: str,
    limit: int = 5,
) -> list[KnowledgeSearchResult]:
    """Fallback text search using case-insensitive LIKE."""
    pattern = f"%{query.lower()}%"
    result = await session.execute(
        text(
            "SELECT id, title, content FROM substrate_knowledge "
            "WHERE LOWER(title) LIKE :pattern OR LOWER(content) LIKE :pattern "
            "LIMIT :limit"
        ),
        {"pattern": pattern, "limit": limit},
    )
    rows = result.fetchall()
    return [
        KnowledgeSearchResult(id=row[0], title=row[1], content=row[2], score=0.5)
        for row in rows
    ]


async def search_knowledge(
    session: AsyncSession,
    query: str,
    limit: int = 5,
) -> list[KnowledgeSearchResult]:
    """Search knowledge: vector similarity first, fallback to ILIKE."""
    embedding = await get_embedding(query)
    if embedding is not None:
        results = await search_knowledge_vector(session, embedding, limit)
        if results:
            return results
    return await search_knowledge_text(session, query, limit)


async def list_knowledge(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 20,
) -> list[KnowledgeResponse]:
    """List knowledge records with pagination."""
    result = await session.execute(
        text(
            "SELECT id, title, content, source_type, metadata_json, created_at, updated_at "
            "FROM substrate_knowledge ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {"limit": limit, "offset": offset},
    )
    rows = result.fetchall()
    return [
        KnowledgeResponse(
            id=row[0], title=row[1], content=row[2], source_type=row[3],
            metadata_json=json.loads(row[4]) if isinstance(row[4], str) else row[4],
            created_at=row[5], updated_at=row[6],
        )
        for row in rows
    ]
