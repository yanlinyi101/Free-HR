from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class LawChunkHit:
    id: uuid.UUID
    law_name: str
    article_no: str | None
    chapter: str | None
    text: str
    region: str
    source_url: str | None
    effective_date: date | None
    score: float  # 1 - cosine_distance

    @property
    def label(self) -> str:
        return f"{self.law_name}·{self.article_no}" if self.article_no else self.law_name


@dataclass
class CaseChunkHit:
    id: uuid.UUID
    case_title: str
    case_no: str | None
    court: str | None
    judgment_date: date | None
    text: str
    source_url: str | None
    score: float

    @property
    def label(self) -> str:
        return self.case_no or self.case_title[:32]


@dataclass
class ChunkDetail:
    id: uuid.UUID
    kind: str  # law / case
    label: str
    text: str
    source_url: str | None
    extra: dict[str, Any]
