from __future__ import annotations
from collections.abc import Sequence

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider


async def collect_full_text(
    llm: LLMProvider, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
) -> str:
    buf: list[str] = []
    async for chunk in llm.chat_stream(messages, opts or ChatOptions()):
        if chunk.delta_text:
            buf.append(chunk.delta_text)
    return "".join(buf)
