from __future__ import annotations
import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from .base import ChatCompletionChunk, ChatMessage, ChatOptions


class DeepSeekProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0)
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    )
    async def _post_stream(self, payload: dict[str, Any]) -> httpx.Response:
        resp = await self._client.send(
            self._client.build_request(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ),
            stream=True,
        )
        if resp.status_code >= 500:
            await resp.aclose()
            resp.raise_for_status()
        return resp

    async def chat_stream(
        self, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
    ) -> AsyncIterator[ChatCompletionChunk]:
        opts = opts or ChatOptions()
        payload: dict[str, Any] = {
            "model": opts.model or self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "stream": True,
        }
        payload.update(opts.extra)
        resp = await self._post_stream(payload)
        try:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(
                    f"LLM API error {resp.status_code}: "
                    f"{body.decode('utf-8', 'ignore')[:500]}"
                )
            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    evt = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = evt.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = (choice.get("delta") or {}).get("content") or ""
                finish = choice.get("finish_reason")
                usage = evt.get("usage")
                if delta or finish or usage:
                    yield ChatCompletionChunk(
                        delta_text=delta, finish_reason=finish, usage=usage
                    )
        finally:
            await resp.aclose()
