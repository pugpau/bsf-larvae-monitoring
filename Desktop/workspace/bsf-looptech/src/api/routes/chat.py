"""Chat & Knowledge API endpoints (Phase 4 RAG)."""

import csv
import io
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User, UserRole
from src.auth.security import SKIP_AUTH, get_current_active_user, require_role
from src.database.postgresql import get_async_session
from src.rag import chat_repo, knowledge_repo
from src.rag.chain import ask_with_rag, ask_with_rag_stream
from src.rag.embedding import get_embedding
from src.rag.knowledge_seeder import seed_knowledge
from src.rag.schemas import (
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    KnowledgeCreate,
    KnowledgeResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat", "knowledge"])


# ── Chat Sessions ──


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    data: ChatSessionCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new chat session."""
    chat_session = await chat_repo.create_session(session, title=data.title, user_id=current_user.id)
    return ChatSessionResponse.model_validate(chat_session)


@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    offset: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List chat sessions (newest first), filtered by current user."""
    sessions = await chat_repo.list_sessions(session, offset=offset, limit=limit, user_id=current_user.id)
    return [ChatSessionResponse.model_validate(s) for s in sessions]


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Get chat session with message history."""
    chat_session = await chat_repo.get_session(session, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not SKIP_AUTH and chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ChatSessionDetailResponse.model_validate(chat_session)


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a chat session and all its messages."""
    # Ownership check
    chat_session = await chat_repo.get_session(session, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not SKIP_AUTH and chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    await chat_repo.delete_session(session, session_id)
    return {"status": "deleted", "session_id": str(session_id)}


# ── Chat Ask ──


@router.post("/chat/ask", response_model=ChatResponse)
async def chat_ask(
    data: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Send a question and get a RAG-augmented answer."""
    # Verify session exists and belongs to user
    chat_session = await chat_repo.get_session(session, data.session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not SKIP_AUTH and chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Save user message
    await chat_repo.add_message(session, data.session_id, "user", data.question)

    # Get RAG answer
    response = await ask_with_rag(
        session, data.question, str(data.session_id),
        max_context_chunks=data.max_context_chunks,
    )

    # Save assistant message
    context_refs = [
        {"id": str(c.id), "title": c.title, "score": c.score}
        for c in response.context
    ]
    await chat_repo.add_message(
        session, data.session_id, "assistant", response.answer,
        context_chunks=context_refs, token_count=response.token_count,
    )

    return response


@router.post("/chat/ask/stream")
async def chat_ask_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Send a question and get SSE streaming RAG answer."""
    chat_session = await chat_repo.get_session(session, data.session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not SKIP_AUTH and chat_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    await chat_repo.add_message(session, data.session_id, "user", data.question)

    return StreamingResponse(
        ask_with_rag_stream(
            session, data.question, str(data.session_id),
            max_context_chunks=data.max_context_chunks,
        ),
        media_type="text/event-stream",
    )


# ── Knowledge Base ──


@router.post("/knowledge", response_model=KnowledgeResponse)
async def create_knowledge_entry(
    data: KnowledgeCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Add a knowledge entry to the RAG knowledge base."""
    embedding = await get_embedding(data.content)
    result = await knowledge_repo.create_knowledge(session, data, embedding=embedding)
    return result


@router.get("/knowledge", response_model=list[KnowledgeResponse])
async def list_knowledge(
    q: str = "",
    offset: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """List or search knowledge entries."""
    if q:
        results = await knowledge_repo.search_knowledge(session, q, limit=limit)
        return [
            KnowledgeResponse(
                id=r.id, title=r.title, content=r.content,
                source_type="", created_at=None, updated_at=None,
            )
            for r in results
        ]
    return await knowledge_repo.list_knowledge(session, offset=offset, limit=limit)


@router.post("/knowledge/seed")
async def seed_knowledge_base(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_async_session),
):
    """Seed initial BSF domain knowledge into the knowledge base."""
    count = await seed_knowledge(session)
    return {"status": "ok", "records_created": count}


@router.post("/knowledge/import-csv")
async def import_knowledge_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    session: AsyncSession = Depends(get_async_session),
):
    """Bulk import knowledge entries from CSV.

    CSV format: title,content,source_type (BOM-UTF-8 supported).
    Each row gets an embedding generated automatically.
    Maximum file size: 10 MB.
    """
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(raw)} bytes). Maximum is {MAX_UPLOAD_BYTES} bytes.",
        )
    content = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    imported, skipped = 0, 0
    errors: list[str] = []

    for i, row in enumerate(reader, start=2):
        title = row.get("title", "").strip()
        body = row.get("content", "").strip()
        source_type = row.get("source_type", "csv").strip() or "csv"

        if not title or not body:
            skipped += 1
            errors.append(f"Row {i}: title or content is empty")
            continue

        try:
            data = KnowledgeCreate(title=title, content=body, source_type=source_type)
            embedding = await get_embedding(body)
            await knowledge_repo.create_knowledge(session, data, embedding=embedding)
            imported += 1
        except Exception as e:
            skipped += 1
            errors.append(f"Row {i}: {e}")

    return {"imported": imported, "skipped": skipped, "errors": errors}
