from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..llm_gateway import EmbeddingProvider
from ..models import IngestionRun, LawChunk
from .chunker import chunk_law
from .parsers import read_law_file


@dataclass
class IngestStats:
    chunks_created: int = 0
    chunks_skipped: int = 0
    errors: int = 0


async def ingest_law_file(
    session: AsyncSession,
    embedder: EmbeddingProvider,
    path: Path,
    batch_size: int = 16,
) -> IngestStats:
    run = IngestionRun(source_type="law", source_path=str(path), status="running")
    session.add(run)
    await session.flush()
    stats = IngestStats()
    try:
        src = read_law_file(path)
        drafts = chunk_law(src.law_name, src.body)
        effective = dt.date.fromisoformat(src.effective_date) if src.effective_date else None

        existing_hashes = set(
            (
                await session.execute(
                    select(LawChunk.content_hash).where(
                        LawChunk.law_name == src.law_name,
                        LawChunk.region == src.region,
                    )
                )
            ).scalars()
        )
        new_drafts = [d for d in drafts if d.content_hash not in existing_hashes]
        stats.chunks_skipped = len(drafts) - len(new_drafts)

        for i in range(0, len(new_drafts), batch_size):
            batch = new_drafts[i : i + batch_size]
            embeddings = await embedder.embed([d.text for d in batch])
            for d, emb in zip(batch, embeddings, strict=True):
                session.add(
                    LawChunk(
                        law_name=d.law_name,
                        article_no=d.article_no,
                        chapter=d.chapter,
                        text=d.text,
                        region=src.region,
                        source_url=src.source_url,
                        effective_date=effective,
                        content_hash=d.content_hash,
                        embedding=emb,
                    )
                )
            await session.flush()

        stats.chunks_created = len(new_drafts)
        run.status = "success"
        run.stats_json = {
            "chunks_created": stats.chunks_created,
            "chunks_skipped": stats.chunks_skipped,
        }
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
    except Exception as e:
        await session.rollback()
        run2 = IngestionRun(
            source_type="law",
            source_path=str(path),
            status="failed",
            error_detail=repr(e),
            finished_at=dt.datetime.now(dt.timezone.utc),
        )
        session.add(run2)
        await session.commit()
        stats.errors = 1
        raise
    return stats


async def ingest_directory(
    session_factory,
    embedder: EmbeddingProvider,
    directory: Path,
) -> dict[str, IngestStats]:
    results: dict[str, IngestStats] = {}
    for path in sorted(directory.rglob("*.txt")):
        async with session_factory() as session:
            results[str(path)] = await ingest_law_file(session, embedder, path)
    return results
