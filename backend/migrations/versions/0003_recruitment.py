"""recruitment module tables

Revision ID: 0003_recruitment
Revises: 0002
Create Date: 2026-04-18
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


revision = "0003_recruitment"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recruitment_requests",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="drafting"),
        sa.Column("profile", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('drafting','pending_review','approved')",
            name="recruitment_requests_status_ck",
        ),
    )
    op.create_index(
        "ix_recruitment_requests_status_updated",
        "recruitment_requests",
        ["status", "updated_at"],
    )

    op.create_table(
        "recruitment_request_messages",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("recruitment_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('user','assistant')", name="recruitment_messages_role_ck"),
    )
    op.create_index(
        "ix_recruitment_messages_request_created",
        "recruitment_request_messages",
        ["request_id", "created_at"],
    )

    op.create_table(
        "recruitment_jd_drafts",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("recruitment_requests.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("content_md", sa.Text, nullable=False),
        sa.Column("edited_content_md", sa.Text, nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("recruitment_jd_drafts")
    op.drop_index("ix_recruitment_messages_request_created", table_name="recruitment_request_messages")
    op.drop_table("recruitment_request_messages")
    op.drop_index("ix_recruitment_requests_status_updated", table_name="recruitment_requests")
    op.drop_table("recruitment_requests")
