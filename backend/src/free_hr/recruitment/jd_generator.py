from __future__ import annotations
import json
from typing import Any

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider
from .llm_util import collect_full_text


SYSTEM_PROMPT = """你是一名资深 HR，基于以下候选人画像，撰写一份清晰、专业、可直接发布的 JD（职位描述）。

要求：
- 使用 Markdown 格式
- 按固定段落组织：一级标题为职位名称，然后依次为：## 岗位职责、## 任职要求、## 薪资福利、## 工作地点与汇报
- "岗位职责"用 bullet list，动宾短语，每条 10-30 字
- "任职要求"分硬性要求与加分项两组
- 不要编造画像中没有的信息；画像缺失的段落（如薪资）用画像提供的原文照抄
- 不输出 JSON、不输出解释、不要加额外的封面/签名
"""


async def generate_jd(llm: LLMProvider, profile: dict[str, Any]) -> str:
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"候选人画像（JSON）：\n{json.dumps(profile, ensure_ascii=False, indent=2)}",
        ),
    ]
    opts = ChatOptions(temperature=0.3, max_tokens=2048)
    text = await collect_full_text(llm, messages, opts)
    return text.strip()
