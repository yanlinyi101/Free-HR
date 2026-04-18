from __future__ import annotations
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CaseChunk, LawChunk
from .schemas import CaseChunkHit, ChunkDetail, LawChunkHit


def _vec_literal(vec: Sequence[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in vec) + "]"


async def search_laws(
    session: AsyncSession,
    query_vec: Sequence[float],
    k: int = 8,
    regions: Sequence[str] | None = None,
) -> list[LawChunkHit]:
    vec_literal = _vec_literal(query_vec)
    sql = text(
        """
        SELECT id, law_name, article_no, chapter, text, region, source_url, effective_date,
               1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM law_chunks
        """
        + (" WHERE region = ANY(:regions) " if regions else "")
        + " ORDER BY embedding <=> CAST(:vec AS vector) LIMIT :k"
    )
    params: dict[str, Any] = {"vec": vec_literal, "k": k}
    if regions:
        params["regions"] = list(regions)
    rows = (await session.execute(sql, params)).mappings().all()
    return [
        LawChunkHit(
            id=r["id"],
            law_name=r["law_name"],
            article_no=r["article_no"],
            chapter=r["chapter"],
            text=r["text"],
            region=r["region"],
            source_url=r["source_url"],
            effective_date=r["effective_date"],
            score=float(r["score"]),
        )
        for r in rows
    ]


async def search_cases(
    session: AsyncSession, query_vec: Sequence[float], k: int = 4
) -> list[CaseChunkHit]:
    vec_literal = _vec_literal(query_vec)
    sql = text(
        """
        SELECT id, case_title, case_no, court, judgment_date, text, source_url,
               1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM case_chunks
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :k
        """
    )
    rows = (await session.execute(sql, {"vec": vec_literal, "k": k})).mappings().all()
    return [
        CaseChunkHit(
            id=r["id"],
            case_title=r["case_title"],
            case_no=r["case_no"],
            court=r["court"],
            judgment_date=r["judgment_date"],
            text=r["text"],
            source_url=r["source_url"],
            score=float(r["score"]),
        )
        for r in rows
    ]


async def get_chunk(session: AsyncSession, chunk_id: uuid.UUID) -> ChunkDetail | None:
    law = await session.get(LawChunk, chunk_id)
    if law is not None:
        return ChunkDetail(
            id=law.id,
            kind="law",
            label=f"{law.law_name}·{law.article_no}" if law.article_no else law.law_name,
            text=law.text,
            source_url=law.source_url,
            extra={
                "chapter": law.chapter,
                "region": law.region,
                "effective_date": law.effective_date.isoformat() if law.effective_date else None,
            },
        )
    case = await session.get(CaseChunk, chunk_id)
    if case is not None:
        return ChunkDetail(
            id=case.id,
            kind="case",
            label=case.case_no or case.case_title[:32],
            text=case.text,
            source_url=case.source_url,
            extra={
                "case_title": case.case_title,
                "court": case.court,
                "judgment_date": case.judgment_date.isoformat() if case.judgment_date else None,
            },
        )
    return None


async def list_laws(session: AsyncSession) -> list[dict[str, Any]]:
    sql = text(
        """
        SELECT law_name, region, COUNT(*) AS article_count, MIN(effective_date) AS effective_date
        FROM law_chunks
        GROUP BY law_name, region
        ORDER BY law_name
        """
    )
    return [dict(r) for r in (await session.execute(sql)).mappings().all()]
