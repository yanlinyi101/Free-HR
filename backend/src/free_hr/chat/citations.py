from __future__ import annotations
import re
from .schemas import ContextRef

_CITE_RE = re.compile(r"\[#(\d+)\]")


def extract_citations(text: str, refs: list[ContextRef]) -> list[dict]:
    """返回唯一的、按首次出现顺序排列的引用列表；过滤越界编号。"""
    by_idx = {r.idx: r for r in refs}
    seen: set[int] = set()
    ordered: list[dict] = []
    for m in _CITE_RE.finditer(text):
        n = int(m.group(1))
        if n in seen or n not in by_idx:
            continue
        seen.add(n)
        ref = by_idx[n]
        ordered.append({
            "idx": n,
            "type": ref.kind,
            "chunk_id": ref.chunk_id,
            "label": ref.label,
        })
    return ordered


def count_oob(text: str, refs: list[ContextRef]) -> int:
    """越界（hallucinated）引用数量，供日志/告警用。"""
    valid = {r.idx for r in refs}
    return sum(1 for m in _CITE_RE.finditer(text) if int(m.group(1)) not in valid)
