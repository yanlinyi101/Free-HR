import pytest
from httpx import ASGITransport, AsyncClient

from free_hr.api.main import app
from free_hr.api import deps as api_deps
from free_hr.chat import service as chat_service
from free_hr.llm_gateway.fake import FakeEmbeddingProvider, FakeLLMProvider


pytestmark = pytest.mark.asyncio


@pytest.fixture
def override_providers():
    """Override DB + LLM + embedder deps so the app runs with no DB/network."""
    async def _fake_db():
        yield None

    fake_llm_holder = {"llm": FakeLLMProvider(script=["结论：可以解除[#1]。"])}

    app.dependency_overrides[api_deps.get_db_dep] = _fake_db
    app.dependency_overrides[api_deps.get_llm_dep] = lambda: fake_llm_holder["llm"]
    app.dependency_overrides[api_deps.get_embedder_dep] = lambda: FakeEmbeddingProvider(dim=1024)
    try:
        yield fake_llm_holder
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def stub_retrieval(monkeypatch):
    """Stub vector search so no DB is needed."""
    import uuid
    from datetime import date
    from free_hr.knowledge_store.schemas import LawChunkHit

    def _stub(laws: list | None = None, cases: list | None = None) -> None:
        laws = laws if laws is not None else [
            LawChunkHit(
                id=uuid.uuid4(), law_name="劳动合同法", article_no="第三十九条",
                chapter=None, text="劳动者严重违反用人单位规章制度的...",
                region="national", source_url=None, effective_date=date(2008, 1, 1), score=0.9,
            ),
        ]
        cases = cases if cases is not None else []
        async def _fake_search_laws(session, query_vec, k=8, regions=None):
            return laws
        async def _fake_search_cases(session, query_vec, k=4):
            return cases
        monkeypatch.setattr(chat_service.ks_repo, "search_laws", _fake_search_laws)
        monkeypatch.setattr(chat_service.ks_repo, "search_cases", _fake_search_cases)
    return _stub


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health_returns_ok():
    async with await _client() as c:
        r = await c.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


async def test_post_chat_returns_text_and_citations(override_providers, stub_retrieval):
    stub_retrieval()
    async with await _client() as c:
        r = await c.post("/api/chat", json={"content": "严重违反规章制度能否解除？"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "[#1]" in body["text"]
    assert body["citations"][0]["idx"] == 1
    assert body["refs"][0]["label"].startswith("劳动合同法")


async def test_post_chat_rejects_empty_content(override_providers, stub_retrieval):
    stub_retrieval()
    async with await _client() as c:
        r = await c.post("/api/chat", json={"content": ""})
    # pydantic min_length=1 triggers 422
    assert r.status_code in (400, 422)


async def test_post_chat_counts_oob_citations(override_providers, stub_retrieval):
    stub_retrieval()
    # Override LLM to emit an out-of-bounds citation
    override_providers["llm"] = FakeLLMProvider(script=["A[#1] B[#7]."])
    async with await _client() as c:
        r = await c.post("/api/chat", json={"content": "q"})
    body = r.json()
    assert body["oob_count"] == 1
    assert [c["idx"] for c in body["citations"]] == [1]
