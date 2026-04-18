"""knowledge store: law_chunks, case_chunks, ingestion_runs + pgvector

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "law_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("law_name", sa.String(255), nullable=False),
        sa.Column("article_no", sa.String(64), nullable=True),
        sa.Column("chapter", sa.String(255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("region", sa.String(32), nullable=False, server_default="national"),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "law_name", "article_no", "region", "content_hash", name="uq_law_chunk_dedup"
        ),
    )
    op.create_index("ix_law_chunks_region", "law_chunks", ["region"])

    op.create_table(
        "case_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_title", sa.String(512), nullable=False),
        sa.Column("case_no", sa.String(128), nullable=True),
        sa.Column("court", sa.String(255), nullable=True),
        sa.Column("judgment_date", sa.Date(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String(64)), nullable=True),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("case_no", "content_hash", name="uq_case_chunk_dedup"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_path", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("stats_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    # HNSW indexes for cosine similarity.
    op.execute(
        "CREATE INDEX ix_law_chunks_embedding "
        "ON law_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_case_chunks_embedding "
        "ON case_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_case_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS ix_law_chunks_embedding")
    op.drop_table("ingestion_runs")
    op.drop_table("case_chunks")
    op.drop_index("ix_law_chunks_region", table_name="law_chunks")
    op.drop_table("law_chunks")
