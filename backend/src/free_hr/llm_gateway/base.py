from __future__ import annotations
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str  # system / user / assistant
    content: str


@dataclass
class ChatCompletionChunk:
    delta_text: str = ""
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


@dataclass
class ChatOptions:
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 2048
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def chat_stream(
        self, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
    ) -> AsyncIterator[ChatCompletionChunk]: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
