from __future__ import annotations
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from ..db import get_db as _db
from ..llm_gateway import EmbeddingProvider, LLMProvider, get_embedder, get_llm
from ..llm_gateway.deepseek import DeepSeekProvider
from ..config import get_settings


async def get_db_dep() -> AsyncIterator[AsyncSession]:
    async for s in _db():
        yield s


def get_llm_dep(request: Request) -> LLMProvider:
    """Return LLM provider, optionally overridden by per-request headers.

    Frontend can pass x-llm-api-key / x-llm-model / x-llm-base-url headers
    (stored in the user's browser) to override the backend .env defaults.
    If no API key header is present, fall back to the server-side provider.
    """
    api_key = request.headers.get("x-llm-api-key", "").strip()
    if api_key:
        s = get_settings()
        model = request.headers.get("x-llm-model", "").strip() or s.llm_model
        base_url = request.headers.get("x-llm-base-url", "").strip() or s.llm_base_url
        return DeepSeekProvider(api_key=api_key, model=model, base_url=base_url)
    return get_llm()


def get_embedder_dep() -> EmbeddingProvider:
    return get_embedder()
