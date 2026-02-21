"""Pydantic schemas for RAG / Chat endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Knowledge ──

class KnowledgeCreate(BaseModel):
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=50000)
    source_type: str = Field(default="manual", max_length=50)
    metadata_json: Optional[dict] = None


class KnowledgeResponse(BaseModel):
    id: UUID
    title: str
    content: str
    source_type: str
    metadata_json: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchResult(BaseModel):
    id: UUID
    title: str
    content: str
    score: float = 0.0


# ── Chat ──

class ChatSessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=200)


class ChatSessionResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    context_chunks: Optional[list] = None
    token_count: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    session_id: UUID
    question: str = Field(..., min_length=1, max_length=2000)
    max_context_chunks: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    session_id: UUID
    answer: str
    context: list[KnowledgeSearchResult] = []
    token_count: Optional[int] = None
