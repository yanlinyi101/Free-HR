import uuid
from datetime import date
from typing import Any

import pytest

from free_hr.chat import service as chat_service
from free_hr.chat.service import answer_once
from free_hr.knowledge_store.schemas import CaseChunkHit, LawChunkHit
from free_hr.llm_gateway.fake import FakeEmbeddingProvider, FakeLLMProvider


pytestmark = pytest.mark.asyncio


def _law(text: str, score: float, art: str = "第X条") -> LawChunkHit:
    return LawChunkHit(
        id=uuid.uuid4(), law_name="劳动合同法", article_no=art, chapter=None,
        text=text, region="national", source_url=None, effective_date=date(2008, 1, 1), score=score,
    )


def _case(text: str, score: float) -> CaseChunkHit:
    return CaseChunkHit(
        id=uuid.uuid4(), case_title="示例", case_no="(2023)京01民终1号", court=None,
        judgment_date=None, text=text, source_url=None, score=score,
    )


@pytest.fixture
def stub_retrieval(monkeypatch):
    """Stub the vector-search calls so tests don't need a DB."""
    def _stub(laws: list[LawChunkHit], cases: list[CaseChunkHit]) -> None:
        async def _fake_search_laws(session, query_vec, k=8, regions=None):
            return laws
        async def _fake_search_cases(session, query_vec, k=4):
            return cases
        monkeypatch.setattr(chat_service.ks_repo, "search_laws", _fake_search_laws)
        monkeypatch.setattr(chat_service.ks_repo, "search_cases", _fake_search_cases)
    return _stub


async def test_answer_once_returns_text_and_citations(stub_retrieval):
    stub_retrieval(
        [_law("劳动者严重违反规章制度可以解除", 0.9, "第三十九条")],
        [_case("案例正文", 0.8)],
    )
    llm = FakeLLMProvider(script=["结论：可以解除[#1]。经济补偿见[#2]。"])

    result = await answer_once(
        session=None,  # stubs don't touch it
        llm=llm,
        embedder=FakeEmbeddingProvider(dim=1024),
        user_text="严重违反规章制度能不能解除？",
    )

    assert "[#1]" in result.text
    assert [c["idx"] for c in result.citations] == [1, 2]
    assert len(result.refs) == 2
    assert result.oob_count == 0


async def test_answer_once_counts_out_of_bound_citations(stub_retrieval):
    stub_retrieval([_law("A", 0.9)], [])
    llm = FakeLLMProvider(script=["A[#1] B[#5]."])  # [#5] is OOB

    result = await answer_once(
        session=None, llm=llm, embedder=FakeEmbeddingProvider(dim=1024),
        user_text="q",
    )
    assert [c["idx"] for c in result.citations] == [1]
    assert result.oob_count == 1


async def test_answer_once_empty_retrieval_yields_no_refs(stub_retrieval):
    stub_retrieval([], [])
    llm = FakeLLMProvider(script=["知识库暂无直接依据。"])

    result = await answer_once(
        session=None, llm=llm, embedder=FakeEmbeddingProvider(dim=1024),
        user_text="q",
    )
    assert result.refs == []
    assert result.citations == []
    assert "知识库" in result.text
