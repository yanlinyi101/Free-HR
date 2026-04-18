from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from ..knowledge_store import repo as ks_repo
from ..llm_gateway import ChatMessage, ChatOptions, EmbeddingProvider, LLMProvider
from .citations import count_oob, extract_citations
from .prompt import SYSTEM_PROMPT, build_context_refs, render_context_block
from .schemas import ContextRef

log = logging.getLogger("free_hr.chat")


@dataclass
class AnswerResult:
    text: str
    citations: list[dict[str, Any]]
    refs: list[dict[str, Any]]
    oob_count: int
    usage: dict[str, Any] | None = None


async def _retrieve(
    session: AsyncSession, embedder: EmbeddingProvider, query: str
) -> list[ContextRef]:
    vec = (await embedder.embed([query]))[0]
    laws = await ks_repo.search_laws(session, vec, k=8, regions=["national", "beijing"])
    cases = await ks_repo.search_cases(session, vec, k=4)
    return build_context_refs(laws, cases)


async def answer_once(
    session: AsyncSession,
    *,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    user_text: str,
) -> AnswerResult:
    """Stateless RAG: retrieve -> prompt -> LLM (collect full stream) -> parse citations."""
    refs = await _retrieve(session, embedder, user_text)
    context_block = render_context_block(refs)
    system = f"{SYSTEM_PROMPT}\n\n{context_block}"
    messages = [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user_text),
    ]

    buf: list[str] = []
    usage: dict[str, Any] | None = None
    async for chunk in llm.chat_stream(messages, ChatOptions()):
        if chunk.delta_text:
            buf.append(chunk.delta_text)
        if chunk.usage:
            usage = chunk.usage
    full_text = "".join(buf)

    citations = extract_citations(full_text, refs)
    oob = count_oob(full_text, refs)
    if oob:
        log.warning("citation out-of-bound count=%s", oob)

    return AnswerResult(
        text=full_text,
        citations=citations,
        refs=[{"idx": r.idx, "kind": r.kind, "chunk_id": r.chunk_id, "label": r.label} for r in refs],
        oob_count=oob,
        usage=usage,
    )
