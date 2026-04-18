import hashlib
import uuid

import pytest
from sqlalchemy import text

from free_hr.db import get_sessionmaker
from free_hr.knowledge_store import repo
from free_hr.llm_gateway.fake import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio


async def _seed_laws(session, items: list[tuple[str, str, str, str]]):
    """items: (law_name, article_no, region, body)"""
    embedder = FakeEmbeddingProvider(dim=1024)
    for law_name, art, region, body in items:
        vec = (await embedder.embed([body]))[0]
        vec_lit = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        await session.execute(
            text(
                "INSERT INTO law_chunks (law_name, article_no, text, region, content_hash, embedding) "
                "VALUES (:ln, :art, :tx, :rg, :ch, CAST(:em AS vector))"
            ),
            {"ln": law_name, "art": art, "tx": body, "rg": region, "ch": h, "em": vec_lit},
        )
    await session.commit()


async def test_search_laws_returns_nearest_first():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(
            s,
            [
                ("劳动合同法", "第三十九条", "national", "劳动者严重违反用人单位规章制度的，用人单位可以解除劳动合同"),
                ("劳动合同法", "第四十条", "national", "劳动者不能胜任工作，经过培训或者调整工作岗位仍不能胜任的"),
                ("社会保险法", "第五十八条", "national", "用人单位应当自用工之日起三十日内为其职工申请办理社会保险登记"),
            ],
        )
    embedder = FakeEmbeddingProvider(dim=1024)
    q_vec = (await embedder.embed(["劳动者严重违反用人单位规章制度的，用人单位可以解除劳动合同"]))[0]
    async with maker() as s:
        hits = await repo.search_laws(s, q_vec, k=3)
        assert len(hits) == 3
        assert hits[0].article_no == "第三十九条"
        assert hits[0].score > hits[-1].score


async def test_search_laws_region_filter():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(
            s,
            [
                ("劳动合同法", "第三十九条", "national", "aaa"),
                ("北京市工资支付规定", "第十五条", "beijing", "bbb"),
            ],
        )
    embedder = FakeEmbeddingProvider(dim=1024)
    q_vec = (await embedder.embed(["x"]))[0]
    async with maker() as s:
        hits_nat = await repo.search_laws(s, q_vec, k=5, regions=["national"])
        hits_bj = await repo.search_laws(s, q_vec, k=5, regions=["beijing"])
        assert {h.region for h in hits_nat} == {"national"}
        assert {h.region for h in hits_bj} == {"beijing"}


async def test_get_chunk_returns_law_or_none():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(s, [("劳动合同法", "第三十九条", "national", "aaa")])
        row = (await s.execute(text("SELECT id FROM law_chunks LIMIT 1"))).first()
        detail = await repo.get_chunk(s, row[0])
        assert detail is not None
        assert detail.kind == "law"
        assert detail.label == "劳动合同法·第三十九条"
    async with maker() as s:
        assert await repo.get_chunk(s, uuid.uuid4()) is None


async def test_list_laws_aggregates():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(
            s,
            [
                ("劳动合同法", "第三十九条", "national", "a"),
                ("劳动合同法", "第四十条", "national", "b"),
                ("北京市工资支付规定", "第十五条", "beijing", "c"),
            ],
        )
        rows = await repo.list_laws(s)
        by_name = {r["law_name"]: r for r in rows}
        assert by_name["劳动合同法"]["article_count"] == 2
        assert by_name["北京市工资支付规定"]["region"] == "beijing"
