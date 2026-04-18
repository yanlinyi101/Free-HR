from __future__ import annotations
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db as _db
from ..llm_gateway import EmbeddingProvider, LLMProvider, get_embedder, get_llm


async def get_db_dep() -> AsyncIterator[AsyncSession]:
    async for s in _db():
        yield s


def get_llm_dep() -> LLMProvider:
    return get_llm()


def get_embedder_dep() -> EmbeddingProvider:
    return get_embedder()
