from __future__ import annotations
import json
import logging
import re
from typing import Any

from ..llm_gateway import ChatMessage, ChatOptions, LLMProvider
from .llm_util import collect_full_text
from .profile import merge_profile

log = logging.getLogger("free_hr.recruitment.extractor")


SYSTEM_PROMPT = """你是招聘需求抽取助手。根据对话历史，把用户**明确提到**的岗位信息抽成严格 JSON。
不要推断、不要编造。用户没提的字段一律返回 null 或空数组。

输出必须是且仅是一个 JSON 对象，结构如下（所有字段都必须出现）：
{
  "position": {"title": null, "department": null, "report_to": null, "headcount": null, "location": null, "start_date": null},
  "responsibilities": [],
  "hard_requirements": {"education": null, "years": null, "skills": [], "industry": null},
  "soft_preferences": {"bonus_points": [], "culture_fit": null, "team_style": null},
  "compensation": {"salary_range": null, "level": null, "employment_type": null}
}

不要输出 JSON 之外的任何文字，不要加 ```json 标签外的解释。
"""


def _format_history(history: list[dict[str, str]]) -> str:
    return "\n".join(f"[{m['role']}] {m['content']}" for m in history)


def _parse_json(text: str) -> dict[str, Any] | None:
    """Try to extract a JSON object from LLM output, tolerating code fences and extra whitespace."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
    return None


async def extract_profile(
    llm: LLMProvider,
    *,
    history: list[dict[str, str]],
    current_profile: dict[str, Any],
) -> dict[str, Any]:
    """Extract profile from dialog history and merge with current_profile.
    On parse failure, return current_profile unchanged.
    """
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=f"已知画像:\n{json.dumps(current_profile, ensure_ascii=False)}\n\n对话:\n{_format_history(history)}",
        ),
    ]
    opts = ChatOptions(temperature=0.0, max_tokens=1024)
    text = await collect_full_text(llm, messages, opts)

    parsed = _parse_json(text)
    if parsed is None:
        log.warning("extract_profile: JSON parse failed, keeping old profile")
        return current_profile

    return merge_profile(current_profile, parsed)
