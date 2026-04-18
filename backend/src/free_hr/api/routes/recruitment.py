from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...llm_gateway import LLMProvider
from ...recruitment import service as svc
from ...recruitment.profile import is_ready_for_jd, missing_fields
from ...recruitment.schemas import (
    JDRead,
    MessageRead,
    PatchRequestBody,
    PostMessageRequest,
    PostMessageResponse,
    RequestListItem,
    RequestRead,
)
from ..deps import get_db_dep, get_llm_dep


router = APIRouter(prefix="/api/recruitment", tags=["recruitment"])


def _to_request_read(req) -> RequestRead:
    jd = None
    if req.jd_draft is not None:
        jd = JDRead(
            content_md=req.jd_draft.content_md,
            edited_content_md=req.jd_draft.edited_content_md,
            generated_at=req.jd_draft.generated_at,
            approved_at=req.jd_draft.approved_at,
        )
    return RequestRead(
        id=req.id,
        title=req.title,
        status=req.status,
        profile=req.profile,
        missing_fields=missing_fields(req.profile),
        ready_for_jd=is_ready_for_jd(req.profile),
        messages=[
            MessageRead(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
            for m in req.messages
        ],
        jd=jd,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.post("/requests", response_model=RequestRead)
async def create_request(session: AsyncSession = Depends(get_db_dep)) -> RequestRead:
    req = await svc.create_request(session)
    await session.refresh(req, attribute_names=["messages", "jd_draft"])
    return _to_request_read(req)


@router.get("/requests", response_model=list[RequestListItem])
async def list_requests(session: AsyncSession = Depends(get_db_dep)) -> list[RequestListItem]:
    reqs = await svc.list_requests(session)
    return [
        RequestListItem(id=r.id, title=r.title, status=r.status, updated_at=r.updated_at)
        for r in reqs
    ]


@router.get("/requests/{request_id}", response_model=RequestRead)
async def get_request(request_id: UUID, session: AsyncSession = Depends(get_db_dep)) -> RequestRead:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    return _to_request_read(req)


@router.post("/requests/{request_id}/messages", response_model=PostMessageResponse)
async def post_message(
    request_id: UUID,
    body: PostMessageRequest,
    session: AsyncSession = Depends(get_db_dep),
    llm: LLMProvider = Depends(get_llm_dep),
) -> PostMessageResponse:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        turn = await svc.append_user_message(session, llm=llm, request=req, user_content=body.content.strip())
    except svc.StateError as e:
        code = str(e).split(":", 1)[0]
        if code == "conversation_too_long":
            raise HTTPException(status_code=409, detail={"error": code})
        raise HTTPException(status_code=400, detail={"error": code})

    await session.refresh(req, attribute_names=["messages"])
    assistant_msg = req.messages[-1]
    return PostMessageResponse(
        assistant_message=MessageRead(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            created_at=assistant_msg.created_at,
        ),
        profile=turn.profile,
        missing_fields=turn.missing,
        ready_for_jd=turn.ready,
    )


@router.post("/requests/{request_id}/jd", response_model=RequestRead)
async def post_jd(
    request_id: UUID,
    session: AsyncSession = Depends(get_db_dep),
    llm: LLMProvider = Depends(get_llm_dep),
) -> RequestRead:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        await svc.generate_and_save_jd(session, llm=llm, request=req)
    except svc.StateError as e:
        msg = str(e)
        if msg.startswith("missing_fields"):
            fields = msg.split(":", 1)[1].split(",") if ":" in msg else []
            raise HTTPException(status_code=400, detail={"error": "missing_fields", "fields": fields})
        if msg == "invalid_state":
            raise HTTPException(status_code=409, detail={"error": "invalid_state"})
        raise HTTPException(status_code=500, detail={"error": msg})

    await session.refresh(req, attribute_names=["messages", "jd_draft"])
    return _to_request_read(req)


@router.patch("/requests/{request_id}", response_model=RequestRead)
async def patch_request(
    request_id: UUID,
    body: PatchRequestBody,
    session: AsyncSession = Depends(get_db_dep),
) -> RequestRead:
    req = await svc.get_request(session, request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="not found")
    try:
        await svc.patch_request(
            session,
            request=req,
            edited_content_md=body.edited_content_md,
            action=body.action,
        )
    except svc.StateError as e:
        code = str(e)
        raise HTTPException(status_code=409, detail={"error": code})

    await session.refresh(req, attribute_names=["messages", "jd_draft"])
    return _to_request_read(req)
