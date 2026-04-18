from __future__ import annotations
import hashlib
import math
from collections.abc import AsyncIterator, Sequence

from .base import ChatCompletionChunk, ChatMessage, ChatOptions


class FakeLLMProvider:
    def __init__(self, script: list[str] | None = None):
        self._script = script or ["Mock answer. [#1] is cited."]

    async def chat_stream(
        self, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
    ) -> AsyncIterator[ChatCompletionChunk]:
        text = self._script[0] if self._script else ""
        for token in text.split(" "):
            yield ChatCompletionChunk(delta_text=(token + " "))
        yield ChatCompletionChunk(
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )


class FakeEmbeddingProvider:
    def __init__(self, dim: int = 1024):
        self._dim = dim

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            raw = [(h[i % len(h)] - 128) / 128.0 for i in range(self._dim)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            out.append([x / norm for x in raw])
        return out
