from __future__ import annotations
from collections.abc import Iterable
from ..knowledge_store.schemas import CaseChunkHit, LawChunkHit
from .schemas import ContextRef


SYSTEM_PROMPT = """你是一名专注于中国大陆劳动法领域的合规咨询助手，主要服务中小企业的 HR 与管理层。

【引用规则】
- 只能基于下方 <context> 中提供的法条或案例作答，不得凭空引用其它法律条文。
- 每个结论性句子末尾必须以 [#n] 的形式标注引用来源编号（n 对应 <context> 中的条目编号）。
- 如 <context> 不足以回答该问题，直接说明"当前知识库暂无直接依据，建议咨询专业律师"，不要硬答。

【地域规则】
- 默认以国家法律和北京市地方规定为准。
- 若问题涉及其它地区，明确提示"以上答复基于国家层面规定，具体执行请参考当地地方法规"。

【风格】
- 先结论后依据，简明扼要。
- 面向非法律专业 HR，避免堆砌法言法语。
- 涉及重大法律风险时，明确提示风险等级。
"""

_MAX_CONTEXT_CHARS = 6000


def build_context_refs(
    law_hits: Iterable[LawChunkHit], case_hits: Iterable[CaseChunkHit]
) -> list[ContextRef]:
    """按相似度合并去重，截断到上下文预算，返回 1-based ContextRef 列表。"""
    merged: list[tuple[float, ContextRef]] = []
    for h in law_hits:
        merged.append((h.score, ContextRef(idx=0, kind="law", chunk_id=str(h.id), label=h.label, text=h.text)))
    for h in case_hits:
        merged.append((h.score, ContextRef(idx=0, kind="case", chunk_id=str(h.id), label=h.label, text=h.text)))
    merged.sort(key=lambda x: x[0], reverse=True)

    seen: set[str] = set()
    selected: list[ContextRef] = []
    remaining = _MAX_CONTEXT_CHARS
    for _, ref in merged:
        if ref.chunk_id in seen:
            continue
        if remaining <= 0 and selected:
            break
        seen.add(ref.chunk_id)
        remaining -= len(ref.text)
        selected.append(ref)

    for i, ref in enumerate(selected, start=1):
        ref.idx = i
    return selected


def render_context_block(refs: list[ContextRef]) -> str:
    if not refs:
        return "<context>\n（本次检索未找到相关法条或案例）\n</context>"
    lines = ["<context>"]
    for r in refs:
        prefix = "法条" if r.kind == "law" else "案例"
        lines.append(f"[#{r.idx}] 【{prefix}·{r.label}】{r.text}")
    lines.append("</context>")
    return "\n".join(lines)
