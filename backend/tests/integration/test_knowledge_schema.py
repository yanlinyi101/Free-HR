import pytest
from sqlalchemy import text
from free_hr.db import get_sessionmaker

pytestmark = pytest.mark.asyncio


async def test_pgvector_extension_enabled():
    async with get_sessionmaker()() as session:
        row = (await session.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'"))).first()
        assert row is not None, "pgvector extension should be enabled"


async def test_hnsw_indexes_exist():
    async with get_sessionmaker()() as session:
        rows = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename IN ('law_chunks','case_chunks') AND indexname LIKE '%embedding%'")
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ix_law_chunks_embedding" in names
        assert "ix_case_chunks_embedding" in names
