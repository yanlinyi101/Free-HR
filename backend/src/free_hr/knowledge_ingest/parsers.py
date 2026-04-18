from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LawSource:
    law_name: str
    region: str
    effective_date: str | None
    source_url: str | None
    body: str


def read_law_file(path: Path) -> LawSource:
    """Law source file format:
    Line 1: `# <law_name>`
    Line 2 (optional): `<!-- region: beijing, effective: 2008-01-01, url: ... -->`
    Remaining lines: the law body text.
    """
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    assert lines and lines[0].startswith("# "), f"{path} first line must be '# <law_name>'"
    law_name = lines[0][2:].strip()
    region = "national"
    effective_date: str | None = None
    source_url: str | None = None
    body_start = 1
    if len(lines) > 1 and lines[1].strip().startswith("<!--"):
        meta = lines[1].strip().strip("<!-->").strip()
        for part in meta.split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                k, v = k.strip(), v.strip()
                if k == "region":
                    region = v
                elif k == "effective":
                    effective_date = v
                elif k == "url":
                    source_url = v
        body_start = 2
    body = "\n".join(lines[body_start:]).strip()
    return LawSource(
        law_name=law_name,
        region=region,
        effective_date=effective_date,
        source_url=source_url,
        body=body,
    )
