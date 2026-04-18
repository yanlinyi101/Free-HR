from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...chat.service import answer_once
from ...llm_gateway import EmbeddingProvider, LLMProvider
from ..deps import get_db_dep, get_embedder_dep, get_llm_dep

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    text: str
    citations: list[dict]
    refs: list[dict]
    oob_count: int


@router.post("", response_model=ChatResponse)
async def post_chat(
    body: ChatRequest,
    session: AsyncSession = Depends(get_db_dep),
    llm: LLMProvider = Depends(get_llm_dep),
    embedder: EmbeddingProvider = Depends(get_embedder_dep),
) -> ChatResponse:
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    result = await answer_once(session, llm=llm, embedder=embedder, user_text=content)
    return ChatResponse(
        text=result.text,
        citations=result.citations,
        refs=result.refs,
        oob_count=result.oob_count,
    )


class TestResponse(BaseModel):
    ok: bool
    text: str = ""
    error: str = ""


@router.post("/test", response_model=TestResponse)
async def test_chat(
    llm: LLMProvider = Depends(get_llm_dep),
) -> TestResponse:
    """Lightweight connectivity test: sends a one-token prompt to verify the LLM config."""
    from ...llm_gateway.base import ChatMessage, ChatOptions
    try:
        chunks: list[str] = []
        async for chunk in llm.chat_stream(
            [ChatMessage(role="user", content="回复OK两个字即可，不要多余输出。")],
            ChatOptions(max_tokens=20),
        ):
            if chunk.delta_text:
                chunks.append(chunk.delta_text)
            if chunk.finish_reason:
                break
        return TestResponse(ok=True, text="".join(chunks).strip())
    except Exception as exc:
        return TestResponse(ok=False, error=str(exc))
