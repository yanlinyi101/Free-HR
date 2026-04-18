from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...knowledge_store import repo as ks_repo
from ..deps import get_db_dep

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/laws")
async def list_laws(session: AsyncSession = Depends(get_db_dep)) -> dict:
    return {"laws": await ks_repo.list_laws(session)}


@router.get("/chunks/{chunk_id}")
async def get_chunk(chunk_id: uuid.UUID, session: AsyncSession = Depends(get_db_dep)) -> dict:
    detail = await ks_repo.get_chunk(session, chunk_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="chunk not found")
    return {
        "id": str(detail.id),
        "kind": detail.kind,
        "label": detail.label,
        "text": detail.text,
        "source_url": detail.source_url,
        "extra": detail.extra,
    }
