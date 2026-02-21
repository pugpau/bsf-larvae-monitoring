"""RAG chain — retrieval-augmented generation using LangChain + LM Studio."""

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.rag.knowledge_repo import search_knowledge
from src.rag.schemas import ChatResponse, KnowledgeSearchResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "あなたはERC製品管理システムのアシスタントです。"
    "廃棄物処理配合最適化、基材配合、固化処理、溶出試験に関する質問に回答してください。"
    "以下のコンテキスト情報を参考にしてください。\n\n"
)


async def ask_with_rag(
    session: AsyncSession,
    question: str,
    session_id: str,
    max_context_chunks: int = 5,
) -> ChatResponse:
    """Run RAG pipeline: retrieve context → build prompt → call LLM."""
    # 1. Retrieve relevant context
    context_results = await search_knowledge(session, question, limit=max_context_chunks)

    # 2. Build prompt with context
    context_text = _build_context(context_results)
    full_prompt = SYSTEM_PROMPT + context_text + f"\n\n質問: {question}"

    # 3. Call LLM
    answer, token_count = await _call_llm(full_prompt)

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        context=context_results,
        token_count=token_count,
    )


async def ask_with_rag_stream(
    session: AsyncSession,
    question: str,
    session_id: str,
    max_context_chunks: int = 5,
) -> AsyncGenerator[str, None]:
    """Stream RAG response as SSE events."""
    import json as json_mod

    # 1. Retrieve context
    context_results = await search_knowledge(session, question, limit=max_context_chunks)

    # 2. Send context event
    context_data = [
        {"id": str(r.id), "title": r.title, "score": r.score}
        for r in context_results
    ]
    yield f"event: context\ndata: {json_mod.dumps(context_data, ensure_ascii=False)}\n\n"

    # 3. Build prompt and stream LLM response
    context_text = _build_context(context_results)
    full_prompt = SYSTEM_PROMPT + context_text + f"\n\n質問: {question}"

    async for chunk in _stream_llm(full_prompt):
        yield f"data: {json_mod.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

    yield "event: done\ndata: {}\n\n"


def _build_context(results: list[KnowledgeSearchResult], max_chars: int = 4000) -> str:
    """Format context chunks for the prompt, truncating at max_chars."""
    if not results:
        return "コンテキスト情報はありません。一般的な知識に基づいて回答してください。"

    parts = ["コンテキスト:"]
    current_len = len(parts[0])
    for i, r in enumerate(results, 1):
        chunk = f"[{i}] {r.title}: {r.content}"
        if current_len + len(chunk) + 1 > max_chars:
            break
        parts.append(chunk)
        current_len += len(chunk) + 1
    return "\n".join(parts)


async def _call_llm(prompt: str) -> tuple[str, Optional[int]]:
    """Call LM Studio chat completions API (non-streaming)."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/chat/completions",
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.3,
                },
                timeout=120.0,
            )
            if resp.status_code != 200:
                logger.error("LLM API returned %d: %s", resp.status_code, resp.text[:300])
                return "LLMサービスに接続できません。しばらくしてから再度お試しください。", None

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            token_count = data.get("usage", {}).get("completion_tokens")
            return content, token_count
    except httpx.ConnectError:
        return "LLMサービスが起動していません。管理者にお問い合わせください。", None
    except Exception as e:
        logger.error("LLM call error: %s", e)
        return "エラーが発生しました。しばらくしてから再度お試しください。", None


async def _stream_llm(prompt: str) -> AsyncGenerator[str, None]:
    """Stream LLM response token by token."""
    import httpx
    import json as json_mod

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{settings.LLM_BASE_URL}/chat/completions",
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.3,
                    "stream": True,
                },
                timeout=120.0,
            ) as resp:
                if resp.status_code != 200:
                    yield "LLMサービスに接続できません。"
                    return
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk_data = json_mod.loads(payload)
                        delta = chunk_data["choices"][0].get("delta", {})
                        text = delta.get("content", "")
                        if text:
                            yield text
                    except (json_mod.JSONDecodeError, KeyError, IndexError):
                        continue
    except httpx.ConnectError:
        yield "LLMサービスが起動していません。"
    except Exception as e:
        logger.error("LLM streaming error: %s", e)
        yield "エラーが発生しました。しばらくしてから再度お試しください。"
