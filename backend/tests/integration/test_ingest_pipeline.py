from pathlib import Path

import pytest
from sqlalchemy import text

from free_hr.db import get_sessionmaker
from free_hr.knowledge_ingest.pipeline import ingest_law_file
from free_hr.llm_gateway.fake import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio


@pytest.fixture
def tiny_law_file(tmp_path):
    p = tmp_path / "tiny.txt"
    p.write_text(
        """# 测试劳动法
<!-- region: beijing, effective: 2024-01-01 -->
第一条 本法为测试。
第二条 劳动者应当遵守。
""",
        encoding="utf-8",
    )
    return p


async def _clean(session):
    await session.execute(text("DELETE FROM law_chunks"))
    await session.execute(text("DELETE FROM ingestion_runs"))
    await session.commit()


async def test_ingest_law_file_creates_chunks_and_run_record(tiny_law_file: Path):
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean(s)
    async with maker() as s:
        stats = await ingest_law_file(s, FakeEmbeddingProvider(dim=1024), tiny_law_file)
        assert stats.chunks_created == 2
    async with maker() as s:
        count = (
            await s.execute(text("SELECT COUNT(*) FROM law_chunks WHERE region='beijing'"))
        ).scalar_one()
        assert count == 2
        runs = (await s.execute(text("SELECT status FROM ingestion_runs"))).scalars().all()
        assert runs == ["success"]


async def test_ingest_is_idempotent(tiny_law_file: Path):
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean(s)
    async with maker() as s:
        await ingest_law_file(s, FakeEmbeddingProvider(dim=1024), tiny_law_file)
    async with maker() as s:
        stats = await ingest_law_file(s, FakeEmbeddingProvider(dim=1024), tiny_law_file)
        assert stats.chunks_created == 0
        assert stats.chunks_skipped == 2
