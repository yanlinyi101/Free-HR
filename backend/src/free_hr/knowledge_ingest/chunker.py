from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass


_ARTICLE_RE = re.compile(r"^第[一二三四五六七八九十百千零〇两\d]+条\s*", re.MULTILINE)
_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千零〇两\d]+章\s+.+$", re.MULTILINE)
_MAX_CHUNK_CHARS = 800
_SUBCLAUSE_RE = re.compile(r"(?=\n?（[一二三四五六七八九十百]+）)")


@dataclass
class LawChunkDraft:
    law_name: str
    article_no: str
    chapter: str | None
    text: str
    content_hash: str


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _iter_articles(full_text: str):
    lines = full_text.splitlines()
    current_chapter: str | None = None
    buf: list[str] = []
    article_no: str | None = None
    for line in lines + [""]:
        if _CHAPTER_RE.match(line.strip()):
            if buf and article_no:
                yield article_no, current_chapter, "\n".join(buf).strip()
                buf, article_no = [], None
            current_chapter = line.strip()
            continue
        m = _ARTICLE_RE.match(line)
        if m:
            if buf and article_no:
                yield article_no, current_chapter, "\n".join(buf).strip()
            article_no = m.group(0).strip()
            buf = [line[len(m.group(0)):]]
        else:
            if article_no is not None:
                buf.append(line)
    if buf and article_no:
        yield article_no, current_chapter, "\n".join(buf).strip()


def _split_long_article(text: str) -> list[str]:
    if len(text) <= _MAX_CHUNK_CHARS:
        return [text]
    parts = [p.strip() for p in _SUBCLAUSE_RE.split(text) if p.strip()]
    if len(parts) > 1 and all(len(p) <= _MAX_CHUNK_CHARS for p in parts):
        return parts
    out: list[str] = []
    i = 0
    while i < len(text):
        out.append(text[i : i + _MAX_CHUNK_CHARS])
        i += _MAX_CHUNK_CHARS - 80
    return out


def chunk_law(law_name: str, full_text: str) -> list[LawChunkDraft]:
    drafts: list[LawChunkDraft] = []
    for article_no, chapter, body in _iter_articles(full_text):
        for piece in _split_long_article(body):
            if not piece.strip():
                continue
            drafts.append(
                LawChunkDraft(
                    law_name=law_name,
                    article_no=article_no,
                    chapter=chapter,
                    text=piece.strip(),
                    content_hash=_hash(f"{law_name}|{article_no}|{piece}"),
                )
            )
    return drafts
