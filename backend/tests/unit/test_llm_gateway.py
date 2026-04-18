import json

import httpx
import pytest

from free_hr.llm_gateway.base import ChatMessage
from free_hr.llm_gateway.deepseek import DeepSeekProvider
from free_hr.llm_gateway.fake import FakeEmbeddingProvider, FakeLLMProvider
from free_hr.llm_gateway.siliconflow import SiliconFlowEmbeddingProvider


def _sse_body(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        lines.append(f"data: {json.dumps(c)}")
        lines.append("")
    lines.append("data: [DONE]")
    lines.append("")
    return "\n".join(lines)


@pytest.mark.asyncio
async def test_deepseek_streams_and_parses_sse():
    sse = _sse_body([
        {"choices": [{"delta": {"content": "你好"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "世界"}, "finish_reason": None}]},
        {
            "choices": [{"delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        },
    ])
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            content=sse.encode("utf-8"),
            headers={"Content-Type": "text/event-stream"},
        )
    )
    client = httpx.AsyncClient(transport=transport, timeout=10.0)
    p = DeepSeekProvider(api_key="k", model="deepseek-chat", base_url="https://x", client=client)

    collected = []
    async for chunk in p.chat_stream([ChatMessage(role="user", content="hi")]):
        collected.append(chunk)

    assert "".join(c.delta_text for c in collected) == "你好世界"
    assert any(c.finish_reason == "stop" for c in collected)


@pytest.mark.asyncio
async def test_deepseek_raises_on_4xx():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(401, json={"error": "bad key"})
    )
    client = httpx.AsyncClient(transport=transport, timeout=10.0)
    p = DeepSeekProvider(api_key="k", model="m", base_url="https://x", client=client)

    with pytest.raises(RuntimeError, match="LLM API error 401"):
        async for _ in p.chat_stream([ChatMessage(role="user", content="hi")]):
            pass


@pytest.mark.asyncio
async def test_siliconflow_embed_returns_vectors():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]},
        )
    )
    client = httpx.AsyncClient(transport=transport)
    p = SiliconFlowEmbeddingProvider(api_key="k", model="bge-m3", base_url="https://y", client=client)
    out = await p.embed(["a", "b"])
    assert out == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_fake_embedder_is_deterministic():
    e = FakeEmbeddingProvider(dim=8)
    v1 = (await e.embed(["同一段文本"]))[0]
    v2 = (await e.embed(["同一段文本"]))[0]
    assert v1 == v2
    assert len(v1) == 8


@pytest.mark.asyncio
async def test_fake_llm_streams_script():
    p = FakeLLMProvider(script=["hello [#1] world"])
    out = []
    async for c in p.chat_stream([ChatMessage(role="user", content="x")]):
        out.append(c.delta_text)
    assert "".join(out).strip() == "hello [#1] world"
