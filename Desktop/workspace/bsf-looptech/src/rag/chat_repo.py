"""Repository for chat_sessions and chat_messages tables."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.postgresql import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


async def create_session(
    session: AsyncSession,
    title: str = "New Chat",
    user_id: Optional[uuid.UUID] = None,
) -> ChatSession:
    """Create a new chat session."""
    chat_session = ChatSession(
        id=uuid.uuid4(),
        title=title,
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return chat_session


async def get_session(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> Optional[ChatSession]:
    """Get chat session by ID with messages eagerly loaded."""
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_sessions(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 20,
    user_id: Optional[uuid.UUID] = None,
) -> list[ChatSession]:
    """List chat sessions, newest first. Optionally filter by user_id."""
    stmt = select(ChatSession).order_by(ChatSession.updated_at.desc())
    if user_id is not None:
        stmt = stmt.where(ChatSession.user_id == user_id)
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_session(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> bool:
    """Delete a chat session (cascades to messages). Returns True if found."""
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        return False
    await session.delete(chat_session)
    await session.commit()
    return True


async def add_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    context_chunks: Optional[list] = None,
    token_count: Optional[int] = None,
) -> ChatMessage:
    """Add a message to a chat session."""
    message = ChatMessage(
        id=uuid.uuid4(),
        session_id=session_id,
        role=role,
        content=content,
        context_chunks=context_chunks,
        token_count=token_count,
        created_at=datetime.now(timezone.utc),
    )
    session.add(message)

    # Update session timestamp
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is not None:
        chat_session.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(message)
    return message


async def get_session_messages(
    session: AsyncSession,
    session_id: uuid.UUID,
) -> list[ChatMessage]:
    """Get all messages for a session, ordered by created_at."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
