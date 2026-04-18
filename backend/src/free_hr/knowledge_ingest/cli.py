from __future__ import annotations
import asyncio
from pathlib import Path

import typer

from ..db import get_sessionmaker
from ..llm_gateway import get_embedder
from .pipeline import ingest_directory, ingest_law_file

app = typer.Typer(add_completion=False, help="Free-HR knowledge ingestion CLI")


@app.command()
def law_file(path: Path):
    """Ingest a single law file."""

    async def run():
        async with get_sessionmaker()() as s:
            stats = await ingest_law_file(s, get_embedder(), path)
            typer.echo(f"{path}: created={stats.chunks_created} skipped={stats.chunks_skipped}")

    asyncio.run(run())


@app.command()
def law_dir(directory: Path):
    """Ingest all .txt law files under a directory (recursive)."""

    async def run():
        results = await ingest_directory(get_sessionmaker(), get_embedder(), directory)
        for p, s in results.items():
            typer.echo(f"{p}: created={s.chunks_created} skipped={s.chunks_skipped}")

    asyncio.run(run())


@app.command(name="all")
def ingest_all():
    """Ingest default seed bundle under backend/data/."""

    async def run():
        base = Path(__file__).resolve().parents[3] / "data"
        for sub in ("laws", "local_regs", "interpretations"):
            d = base / sub
            if d.exists():
                results = await ingest_directory(get_sessionmaker(), get_embedder(), d)
                for p, stats in results.items():
                    typer.echo(f"{p}: created={stats.chunks_created} skipped={stats.chunks_skipped}")

    asyncio.run(run())


if __name__ == "__main__":
    app()
