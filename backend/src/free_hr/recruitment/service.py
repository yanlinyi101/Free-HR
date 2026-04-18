from __future__ import annotations
import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider
from ..models import JDDraft, RecruitmentRequest, RequestMessage
from .extractor import extract_profile
from .jd_generator import generate_jd
from .llm_util import collect_full_text
from .profile import empty_profile, is_ready_for_jd, missing_fields


class StateError(Exception):
    """Raised when a state transition is invalid. Message includes a machine-readable code."""


REPLY_SYSTEM_PROMPT = """你是 HR 助手，帮业务部门梳理招聘需求。基于已知画像和缺项，自然地追问 1-2 个最相关的缺项（不要像填表单一样逐项盘问）。
若用户在上一轮提供了新信息，先简短确认（1 句），再追问缺项。
语气专业、友好、中文。不要输出 JSON 或代码块。
如果所有必填字段都已填写，告诉用户"信息已经齐备，可以点'生成 JD'了"。
"""


@dataclass
class MessageTurn:
    user_content: str
    assistant_content: str
    profile: dict[str, Any]
    missing: list[str]
    ready: bool


def derive_title(profile: dict[str, Any], *, fallback: str) -> str:
    title = profile.get("position", {}).get("title")
    dept = profile.get("position", {}).get("department")
    if title and dept:
        return f"{dept} · {title}"
    if title:
        return title
    return fallback


def validate_transition_to_pending_review(*, status: str, profile: dict[str, Any]) -> None:
    if status != "drafting":
        raise StateError("invalid_state")
    if not is_ready_for_jd(profile):
        raise StateError(f"missing_fields:{','.join(missing_fields(profile))}")


def validate_transition_to_approved(*, status: str) -> None:
    if status != "pending_review":
        raise StateError("invalid_state")


async def create_request(session: AsyncSession) -> RecruitmentRequest:
    now_tag = uuid.uuid4().hex[:8]
    req = RecruitmentRequest(
        title=f"新需求-{now_tag}",
        status="drafting",
        profile=empty_profile(),
    )
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def get_request(session: AsyncSession, request_id: uuid.UUID) -> RecruitmentRequest | None:
    stmt = (
        select(RecruitmentRequest)
        .options(selectinload(RecruitmentRequest.messages), selectinload(RecruitmentRequest.jd_draft))
        .where(RecruitmentRequest.id == request_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_requests(session: AsyncSession) -> list[RecruitmentRequest]:
    stmt = select(RecruitmentRequest).order_by(RecruitmentRequest.updated_at.desc())
    return list((await session.execute(stmt)).scalars().all())


MAX_TURNS = 20


async def append_user_message(
    session: AsyncSession,
    *,
    llm: LLMProvider,
    request: RecruitmentRequest,
    user_content: str,
) -> MessageTurn:
    if len(request.messages) // 2 >= MAX_TURNS:
        raise StateError("conversation_too_long")

    session.add(RequestMessage(request_id=request.id, role="user", content=user_content))
    await session.flush()

    history = [{"role": m.role, "content": m.content} for m in request.messages] + [
        {"role": "user", "content": user_content}
    ]

    new_profile = await extract_profile(
        llm, history=history, current_profile=request.profile or empty_profile()
    )
    request.profile = new_profile
    request.title = derive_title(new_profile, fallback=request.title)
    miss = missing_fields(new_profile)
    ready = is_ready_for_jd(new_profile)

    reply_messages = [
        ChatMessage(role="system", content=REPLY_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=(
                f"已知画像:\n{json.dumps(new_profile, ensure_ascii=False)}\n"
                f"缺项（按优先级）:\n{miss}\n"
                f"对话:\n" + "\n".join(f"[{m['role']}] {m['content']}" for m in history)
            ),
        ),
    ]
    assistant_text = await collect_full_text(
        llm, reply_messages, ChatOptions(temperature=0.5, max_tokens=800)
    )
    if not assistant_text.strip():
        assistant_text = "（系统提示：回复生成失败，请重试）"

    session.add(RequestMessage(request_id=request.id, role="assistant", content=assistant_text))
    await session.commit()
    await session.refresh(request)
    return MessageTurn(
        user_content=user_content,
        assistant_content=assistant_text,
        profile=new_profile,
        missing=miss,
        ready=ready,
    )


async def generate_and_save_jd(
    session: AsyncSession, *, llm: LLMProvider, request: RecruitmentRequest
) -> JDDraft:
    validate_transition_to_pending_review(status=request.status, profile=request.profile)

    md = await generate_jd(llm, request.profile)
    if not md.strip():
        raise StateError("jd_generation_empty")

    draft = JDDraft(request_id=request.id, content_md=md)
    session.add(draft)
    request.status = "pending_review"
    await session.commit()
    await session.refresh(request)
    return draft


async def patch_request(
    session: AsyncSession,
    *,
    request: RecruitmentRequest,
    edited_content_md: str | None,
    action: str | None,
) -> RecruitmentRequest:
    from datetime import datetime, timezone

    if edited_content_md is not None:
        if request.jd_draft is None:
            raise StateError("no_jd_to_edit")
        request.jd_draft.edited_content_md = edited_content_md

    if action == "approve":
        validate_transition_to_approved(status=request.status)
        request.status = "approved"
        if request.jd_draft is not None:
            request.jd_draft.approved_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(request)
    return request
