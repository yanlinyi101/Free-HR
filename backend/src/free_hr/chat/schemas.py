from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ChatEventType(str, Enum):
    TOKEN = "token"
    CITATIONS = "citations"
    DONE = "done"
    ERROR = "error"


@dataclass
class ContextRef:
    """已排序的检索结果，供 prompt 生成时分配 [#n] 编号。"""
    idx: int               # 1-based
    kind: str              # law / case
    chunk_id: str
    label: str
    text: str


@dataclass
class ChatEvent:
    type: ChatEventType
    data: dict = field(default_factory=dict)
