# Free-HR Phase 1 Implementation Plan — AI Legal Chat MVP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零构建 Free-HR Phase 1——一个基于 RAG 的中国劳动法咨询聊天 MVP，支持自然语言提问、引用溯源（`[#n]` 内联编号 + hover 原文）、单租户自部署（`docker compose up` 起全栈）。

**Architecture:** Python FastAPI（异步 + SSE 流式）后端 + Next.js 14 前端 + PostgreSQL（pgvector）单库方案。六个后端模块按职责拆分（llm_gateway / knowledge_store / knowledge_ingest / chat / auth / api），每个模块边界清晰、可独立测试。RAG 两路召回（法条 + 案例）→ 合并 → Prompt 装配 → LLM 流式生成 → 引用编号解析。

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy 2.x (async) + Alembic + pgvector + uv；Next.js 14 + TypeScript + Tailwind + shadcn/ui + pnpm；PostgreSQL 16 + pgvector；Docker Compose；DeepSeek Chat + SiliconFlow bge-m3。

**Source spec:** [docs/superpowers/specs/2026-04-18-free-hr-phase1-legal-chat-design.md](../specs/2026-04-18-free-hr-phase1-legal-chat-design.md)

---

## 任务拆分概览

| # | 任务 | 产出 |
|---|---|---|
| 1 | 项目骨架 + 配置 + 数据库基础设施 | 可运行的 FastAPI health check + Alembic |
| 2 | 数据库迁移：users / sessions / messages | `0001` migration 可正反迁移 |
| 3 | 数据库迁移：law_chunks / case_chunks / ingestion_runs + pgvector | `0002` migration |
| 4 | LLM Gateway 模块 | DeepSeek + SiliconFlow + Fake provider，单元测试绿 |
| 5 | Auth 模块 | register / login / JWT / bootstrap admin，集成测试绿 |
| 6 | Knowledge Store 模块 | `search_laws` / `search_cases` / `get_chunk`，集成测试绿 |
| 7 | Knowledge Ingest 模块 + CLI | 法条分块器 + 摄入 pipeline，单元测试绿 |
| 8 | Chat 核心：prompt + 引用解析 | 纯函数单元测试绿 |
| 9 | Chat 服务 + RAG pipeline | `stream_answer` 集成测试绿（用 FakeProvider） |
| 10 | API 路由装配 + 异常处理 + SSE 端点 | HTTP 集成测试绿 |
| 11 | 前端骨架 + Tailwind + shadcn/ui | Next dev server 起、登录页渲染 |
| 12 | 前端登录页 + Auth Store + API client | 登录 → 跳 /chat |
| 13 | 前端 Chat 页：会话侧栏 + 消息列表 + SSE 流式 | 能发消息、看到流式回答 |
| 14 | 前端引用气泡 + Sources 页 | `[#n]` hover 展示原文，浏览法规库 |
| 15 | Docker Compose + 种子数据摄入脚本 | `docker compose up` 一键起全栈 |
| 16 | 评测集 + E2E smoke 测试 + README 打磨 | 可交付验收 |

每个任务结束必定 commit。

---

## Task 1: 项目骨架 + 配置 + 数据库连接

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/free_hr/__init__.py`
- Create: `backend/src/free_hr/config.py`
- Create: `backend/src/free_hr/db.py`
- Create: `backend/src/free_hr/api/main.py`
- Create: `backend/src/free_hr/api/__init__.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/unit/__init__.py`
- Create: `backend/tests/unit/test_config.py`
- Create: `.env.example`

- [ ] **Step 1.1: 创建 `backend/pyproject.toml`**

```toml
[project]
name = "free-hr"
version = "0.1.0"
description = "AI labor-law compliance assistant for Chinese SMEs"
requires-python = ">=3.11,<3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.30",
    "alembic>=1.13",
    "pgvector>=0.3.6",
    "pydantic>=2.9",
    "pydantic-settings>=2.5",
    "httpx>=0.27",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7.4",
    "typer>=0.12",
    "sse-starlette>=2.1",
    "python-multipart>=0.0.9",
    "tenacity>=9.0",
    "numpy>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "pytest-httpx>=0.32",
    "ruff>=0.7",
    "mypy>=1.11",
    "asgi-lifespan>=2.1",
]

[project.scripts]
free-hr-ingest = "free_hr.knowledge_ingest.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/free_hr"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra -q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "N"]
ignore = ["E501"]
```

- [ ] **Step 1.2: 创建 `backend/src/free_hr/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 1.3: 创建 `backend/src/free_hr/config.py`**

```python
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_url: str = Field(default="postgresql+asyncpg://free_hr:free_hr@localhost:5432/free_hr")

    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 24 * 3600

    admin_email: str = "admin@example.com"
    admin_password: str = "admin-change-me"

    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"

    embedding_provider: str = "siliconflow"
    embedding_api_key: str = ""
    embedding_model: str = "BAAI/bge-m3"
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_dim: int = 1024

    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 1.4: 创建 `backend/src/free_hr/db.py`**

```python
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().postgres_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker():
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session
```

- [ ] **Step 1.5: 创建 `backend/src/free_hr/api/__init__.py` (空文件) 和 `backend/src/free_hr/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Free-HR API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 1.6: 创建 Alembic 配置**

`backend/alembic.ini`:

```ini
[alembic]
script_location = migrations
prepend_sys_path = .
sqlalchemy.url = driver://user:pass@host/db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

`backend/migrations/env.py`:

```python
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from free_hr.config import get_settings
from free_hr.db import Base
import free_hr.models  # noqa: F401 — ensure models imported for autogenerate

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.postgres_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

`backend/migrations/script.py.mako`:

```python
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

创建空的 `backend/src/free_hr/models.py`（后续 Task 2 填充）：

```python
# Models are imported by migrations/env.py for autogenerate.
# Concrete model classes are added in later tasks.
from .db import Base  # noqa: F401
```

- [ ] **Step 1.7: 创建 `.env.example`（仓库根）**

```
# Backend
POSTGRES_URL=postgresql+asyncpg://free_hr:free_hr@postgres:5432/free_hr
JWT_SECRET=change-me-to-a-long-random-string
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me-too

LLM_PROVIDER=deepseek
LLM_API_KEY=
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1

EMBEDDING_PROVIDER=siliconflow
EMBEDDING_API_KEY=
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1

CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 1.8: 写失败的单元测试 `backend/tests/unit/test_config.py`**

```python
from free_hr.config import Settings


def test_settings_defaults_are_loaded():
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.jwt_algorithm == "HS256"
    assert s.embedding_dim == 1024
    assert s.llm_provider == "deepseek"


def test_settings_override_via_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "custom-secret")
    monkeypatch.setenv("LLM_MODEL", "deepseek-reasoner")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.jwt_secret == "custom-secret"
    assert s.llm_model == "deepseek-reasoner"
```

`backend/tests/conftest.py`:

```python
import os
os.environ.setdefault("POSTGRES_URL", "postgresql+asyncpg://free_hr:free_hr@localhost:5432/free_hr_test")
os.environ.setdefault("JWT_SECRET", "test-secret")
```

- [ ] **Step 1.9: 运行测试，应通过**

```bash
cd backend && uv sync --dev && uv run pytest tests/unit/test_config.py -v
```

Expected: 2 passed.

- [ ] **Step 1.10: 启 FastAPI，手测 /api/health**

```bash
cd backend && uv run uvicorn free_hr.api.main:app --port 8000
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 1.11: Commit**

```bash
git add backend/ .env.example
git commit -m "chore: scaffold backend project, config, db session, health endpoint"
```

---

## Task 2: 数据库迁移——users / chat_sessions / chat_messages

**Files:**
- Modify: `backend/src/free_hr/models.py`
- Create: `backend/migrations/versions/0001_initial_auth_chat.py`

- [ ] **Step 2.1: 填充 `backend/src/free_hr/models.py`（用户 + 对话部分）**

```python
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, CheckConstraint, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin','hr')", name="users_role_ck"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="chat_messages_role_ck"),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    token_usage_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped[ChatSession] = relationship(back_populates="messages")
```

- [ ] **Step 2.2: 生成迁移**

```bash
cd backend && uv run alembic revision --autogenerate -m "initial auth + chat"
# 重命名产物为 migrations/versions/0001_initial_auth_chat.py 并固定 revision id
```

- [ ] **Step 2.3: 人工核对迁移内容**，应包含创建三张表 + 两个 index + 两个 check constraint。

- [ ] **Step 2.4: 正向迁移**

```bash
docker compose -f infra/docker-compose.yml up -d postgres  # 若尚未启动
cd backend && uv run alembic upgrade head
```

Expected: 3 表创建成功，无报错。

- [ ] **Step 2.5: 反向迁移回归**

```bash
cd backend && uv run alembic downgrade base && uv run alembic upgrade head
```

Expected: 无错。

- [ ] **Step 2.6: Commit**

```bash
git add backend/src/free_hr/models.py backend/migrations/versions/0001_initial_auth_chat.py
git commit -m "feat(db): add users, chat_sessions, chat_messages tables"
```

---

## Task 3: 数据库迁移——law_chunks / case_chunks / ingestion_runs + pgvector

**Files:**
- Modify: `backend/src/free_hr/models.py`
- Create: `backend/migrations/versions/0002_knowledge_store.py`
- Create: `infra/postgres/init.sql`

- [ ] **Step 3.1: 添加 pgvector 初始化 SQL `infra/postgres/init.sql`**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

- [ ] **Step 3.2: 在 `backend/src/free_hr/models.py` 末尾追加知识库模型**

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from .config import get_settings

EMBED_DIM = get_settings().embedding_dim


class LawChunk(Base):
    __tablename__ = "law_chunks"
    __table_args__ = (
        UniqueConstraint("law_name", "article_no", "region", "content_hash", name="uq_law_chunk_dedup"),
        Index("ix_law_chunks_region", "region"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    law_name: Mapped[str] = mapped_column(String(255), nullable=False)
    article_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chapter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    region: Mapped[str] = mapped_column(String(32), nullable=False, server_default="national")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CaseChunk(Base):
    __tablename__ = "case_chunks"
    __table_args__ = (
        UniqueConstraint("case_no", "content_hash", name="uq_case_chunk_dedup"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_title: Mapped[str] = mapped_column(String(512), nullable=False)
    case_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    court: Mapped[str | None] = mapped_column(String(255), nullable=True)
    judgment_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # law / case
    source_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    stats_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 3.3: 生成迁移 `0002_knowledge_store.py`，在 upgrade 开头添加 pgvector 扩展 + HNSW 索引**

关键部分（在 autogenerate 基础上手工补齐）：

```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # (autogenerate 产生的 create_table 语句)
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
    # (autogenerate 产生的 drop_table 语句)
```

- [ ] **Step 3.4: 运行迁移验证**

```bash
cd backend && uv run alembic upgrade head
```

- [ ] **Step 3.5: 写集成测试 `backend/tests/integration/test_knowledge_schema.py`**

```python
import pytest
from sqlalchemy import text
from free_hr.db import get_sessionmaker

pytestmark = pytest.mark.asyncio


async def test_pgvector_extension_enabled():
    async with get_sessionmaker()() as session:
        row = (await session.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'"))).first()
        assert row is not None, "pgvector extension should be enabled"


async def test_hnsw_indexes_exist():
    async with get_sessionmaker()() as session:
        rows = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename IN ('law_chunks','case_chunks') AND indexname LIKE '%embedding%'")
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ix_law_chunks_embedding" in names
        assert "ix_case_chunks_embedding" in names
```

创建 `backend/tests/integration/__init__.py` 空文件。

- [ ] **Step 3.6: 运行测试**

```bash
cd backend && uv run pytest tests/integration/test_knowledge_schema.py -v
```

Expected: 2 passed.

- [ ] **Step 3.7: Commit**

```bash
git add backend/src/free_hr/models.py backend/migrations/versions/0002_knowledge_store.py backend/tests/integration/ infra/postgres/init.sql
git commit -m "feat(db): add law_chunks, case_chunks, ingestion_runs with pgvector HNSW"
```

---

## Task 4: LLM Gateway 模块

**Files:**
- Create: `backend/src/free_hr/llm_gateway/__init__.py`
- Create: `backend/src/free_hr/llm_gateway/base.py`
- Create: `backend/src/free_hr/llm_gateway/deepseek.py`
- Create: `backend/src/free_hr/llm_gateway/siliconflow.py`
- Create: `backend/src/free_hr/llm_gateway/fake.py`
- Create: `backend/src/free_hr/llm_gateway/factory.py`
- Create: `backend/tests/unit/test_llm_gateway.py`

- [ ] **Step 4.1: 定义抽象接口 `base.py`**

```python
from __future__ import annotations
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ChatMessage:
    role: str  # system / user / assistant
    content: str


@dataclass
class ChatCompletionChunk:
    delta_text: str = ""
    finish_reason: str | None = None
    usage: dict | None = None


@dataclass
class ChatOptions:
    model: str | None = None
    temperature: float = 0.2
    max_tokens: int = 2048
    extra: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    async def chat_stream(
        self, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
    ) -> AsyncIterator[ChatCompletionChunk]: ...


class EmbeddingProvider(Protocol):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...
```

- [ ] **Step 4.2: DeepSeek 实现 `deepseek.py`（OpenAI 兼容）**

```python
from __future__ import annotations
import json
from collections.abc import AsyncIterator, Sequence
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from .base import ChatCompletionChunk, ChatMessage, ChatOptions


class DeepSeekProvider:
    def __init__(self, api_key: str, model: str, base_url: str, client: httpx.AsyncClient | None = None):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    )
    async def _post_stream(self, payload: dict) -> httpx.Response:
        resp = await self._client.send(
            self._client.build_request(
                "POST",
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json=payload,
            ),
            stream=True,
        )
        if resp.status_code >= 500:
            await resp.aclose()
            resp.raise_for_status()
        return resp

    async def chat_stream(
        self, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
    ) -> AsyncIterator[ChatCompletionChunk]:
        opts = opts or ChatOptions()
        payload = {
            "model": opts.model or self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": opts.temperature,
            "max_tokens": opts.max_tokens,
            "stream": True,
        }
        payload.update(opts.extra)
        resp = await self._post_stream(payload)
        try:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"LLM API error {resp.status_code}: {body.decode('utf-8', 'ignore')[:500]}")
            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    evt = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = evt.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = (choice.get("delta") or {}).get("content") or ""
                finish = choice.get("finish_reason")
                usage = evt.get("usage")
                if delta or finish or usage:
                    yield ChatCompletionChunk(delta_text=delta, finish_reason=finish, usage=usage)
        finally:
            await resp.aclose()
```

- [ ] **Step 4.3: SiliconFlow Embedding 实现 `siliconflow.py`**

```python
from __future__ import annotations
from collections.abc import Sequence
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential_jitter


class SiliconFlowEmbeddingProvider:
    def __init__(self, api_key: str, model: str, base_url: str, client: httpx.AsyncClient | None = None):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=30.0)

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4))
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = await self._client.post(
            f"{self._base_url}/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            json={"model": self._model, "input": list(texts), "encoding_format": "float"},
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
```

- [ ] **Step 4.4: Fake provider `fake.py`**

```python
from __future__ import annotations
from collections.abc import AsyncIterator, Sequence
import hashlib
import math
from .base import ChatCompletionChunk, ChatMessage, ChatOptions


class FakeLLMProvider:
    def __init__(self, script: list[str] | None = None):
        self._script = script or ["Mock answer. [#1] is cited."]

    async def chat_stream(
        self, messages: Sequence[ChatMessage], opts: ChatOptions | None = None
    ) -> AsyncIterator[ChatCompletionChunk]:
        text = self._script[0] if self._script else ""
        for token in text.split(" "):
            yield ChatCompletionChunk(delta_text=(token + " "))
        yield ChatCompletionChunk(finish_reason="stop", usage={"prompt_tokens": 10, "completion_tokens": 5})


class FakeEmbeddingProvider:
    def __init__(self, dim: int = 1024):
        self._dim = dim

    async def embed(self, texts):
        out: list[list[float]] = []
        for t in texts:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            # 确定性伪向量，平均分布并归一化
            raw = [(h[i % len(h)] - 128) / 128.0 for i in range(self._dim)]
            norm = math.sqrt(sum(x * x for x in raw)) or 1.0
            out.append([x / norm for x in raw])
        return out
```

- [ ] **Step 4.5: Factory `factory.py`**

```python
from __future__ import annotations
from .base import EmbeddingProvider, LLMProvider
from .deepseek import DeepSeekProvider
from .siliconflow import SiliconFlowEmbeddingProvider
from .fake import FakeEmbeddingProvider, FakeLLMProvider
from ..config import get_settings


def get_llm() -> LLMProvider:
    s = get_settings()
    match s.llm_provider:
        case "deepseek":
            return DeepSeekProvider(api_key=s.llm_api_key, model=s.llm_model, base_url=s.llm_base_url)
        case "fake":
            return FakeLLMProvider()
        case other:
            raise ValueError(f"unsupported llm_provider={other}")


def get_embedder() -> EmbeddingProvider:
    s = get_settings()
    match s.embedding_provider:
        case "siliconflow":
            return SiliconFlowEmbeddingProvider(api_key=s.embedding_api_key, model=s.embedding_model, base_url=s.embedding_base_url)
        case "fake":
            return FakeEmbeddingProvider(dim=s.embedding_dim)
        case other:
            raise ValueError(f"unsupported embedding_provider={other}")
```

`__init__.py`:

```python
from .base import ChatCompletionChunk, ChatMessage, ChatOptions, EmbeddingProvider, LLMProvider
from .factory import get_embedder, get_llm

__all__ = ["ChatMessage", "ChatOptions", "ChatCompletionChunk", "LLMProvider", "EmbeddingProvider", "get_llm", "get_embedder"]
```

- [ ] **Step 4.6: 单元测试 `backend/tests/unit/test_llm_gateway.py`**

```python
import json
import pytest
import httpx
from free_hr.llm_gateway.deepseek import DeepSeekProvider
from free_hr.llm_gateway.siliconflow import SiliconFlowEmbeddingProvider
from free_hr.llm_gateway.fake import FakeLLMProvider, FakeEmbeddingProvider
from free_hr.llm_gateway.base import ChatMessage


def _sse_body(chunks: list[dict]) -> str:
    lines = []
    for c in chunks:
        lines.append(f"data: {json.dumps(c)}")
        lines.append("")
    lines.append("data: [DONE]")
    lines.append("")
    return "\n".join(lines)


@pytest.mark.asyncio
async def test_deepseek_streams_and_parses_sse():
    sse = _sse_body([
        {"choices": [{"delta": {"content": "你好"}, "finish_reason": None}]},
        {"choices": [{"delta": {"content": "世界"}, "finish_reason": None}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 3, "completion_tokens": 2}},
    ])
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=sse.encode("utf-8"), headers={"Content-Type": "text/event-stream"}))
    client = httpx.AsyncClient(transport=transport, timeout=10.0)
    p = DeepSeekProvider(api_key="k", model="deepseek-chat", base_url="https://x", client=client)

    collected = []
    async for chunk in p.chat_stream([ChatMessage(role="user", content="hi")]):
        collected.append(chunk)

    assert "".join(c.delta_text for c in collected) == "你好世界"
    assert any(c.finish_reason == "stop" for c in collected)


@pytest.mark.asyncio
async def test_deepseek_raises_on_4xx():
    transport = httpx.MockTransport(lambda req: httpx.Response(401, json={"error": "bad key"}))
    client = httpx.AsyncClient(transport=transport, timeout=10.0)
    p = DeepSeekProvider(api_key="k", model="m", base_url="https://x", client=client)

    with pytest.raises(RuntimeError, match="LLM API error 401"):
        async for _ in p.chat_stream([ChatMessage(role="user", content="hi")]):
            pass


@pytest.mark.asyncio
async def test_siliconflow_embed_returns_vectors():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})
    )
    client = httpx.AsyncClient(transport=transport)
    p = SiliconFlowEmbeddingProvider(api_key="k", model="bge-m3", base_url="https://y", client=client)
    out = await p.embed(["a", "b"])
    assert out == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_fake_embedder_is_deterministic():
    e = FakeEmbeddingProvider(dim=8)
    v1 = (await e.embed(["同一段文本"]))[0]
    v2 = (await e.embed(["同一段文本"]))[0]
    assert v1 == v2
    assert len(v1) == 8


@pytest.mark.asyncio
async def test_fake_llm_streams_script():
    p = FakeLLMProvider(script=["hello [#1] world"])
    out = []
    async for c in p.chat_stream([ChatMessage(role="user", content="x")]):
        out.append(c.delta_text)
    assert "".join(out).strip() == "hello [#1] world"
```

- [ ] **Step 4.7: 运行**

```bash
cd backend && uv run pytest tests/unit/test_llm_gateway.py -v
```

Expected: 5 passed.

- [ ] **Step 4.8: Commit**

```bash
git add backend/src/free_hr/llm_gateway/ backend/tests/unit/test_llm_gateway.py
git commit -m "feat(llm_gateway): add DeepSeek, SiliconFlow, Fake providers with streaming"
```

---

## Task 5: Auth 模块

**Files:**
- Create: `backend/src/free_hr/auth/__init__.py`
- Create: `backend/src/free_hr/auth/security.py`
- Create: `backend/src/free_hr/auth/repo.py`
- Create: `backend/src/free_hr/auth/service.py`
- Create: `backend/src/free_hr/auth/deps.py`
- Create: `backend/src/free_hr/auth/schemas.py`
- Create: `backend/tests/unit/test_auth_security.py`
- Create: `backend/tests/integration/test_auth_flow.py`

- [ ] **Step 5.1: `security.py`**

```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..config import get_settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(raw: str) -> str:
    return _pwd.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd.verify(raw, hashed)


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    s = get_settings()
    now = datetime.now(tz=timezone.utc)
    claims = {"sub": subject, "iat": int(now.timestamp()), "exp": int((now + timedelta(seconds=s.jwt_ttl_seconds)).timestamp())}
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError as e:
        raise ValueError("invalid token") from e
```

- [ ] **Step 5.2: `schemas.py`**

```python
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="hr", pattern="^(hr|admin)$")


class TokenResponse(BaseModel):
    token: str
    user: "UserInfo"


class UserInfo(BaseModel):
    id: str
    email: EmailStr
    role: str


TokenResponse.model_rebuild()
```

- [ ] **Step 5.3: `repo.py`**

```python
from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def create_user(session: AsyncSession, email: str, password_hash: str, role: str) -> User:
    u = User(email=email, password_hash=password_hash, role=role)
    session.add(u)
    await session.flush()
    return u
```

- [ ] **Step 5.4: `service.py`**

```python
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from . import repo
from .schemas import LoginRequest, RegisterRequest, TokenResponse, UserInfo
from .security import create_access_token, hash_password, verify_password


class AuthError(Exception):
    pass


async def register(session: AsyncSession, req: RegisterRequest) -> UserInfo:
    if await repo.get_user_by_email(session, req.email) is not None:
        raise AuthError("email already registered")
    user = await repo.create_user(session, req.email, hash_password(req.password), req.role)
    await session.commit()
    return UserInfo(id=str(user.id), email=user.email, role=user.role)


async def login(session: AsyncSession, req: LoginRequest) -> TokenResponse:
    user = await repo.get_user_by_email(session, req.email)
    if user is None or not verify_password(req.password, user.password_hash):
        raise AuthError("invalid credentials")
    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(token=token, user=UserInfo(id=str(user.id), email=user.email, role=user.role))


async def bootstrap_admin(session: AsyncSession, email: str, password: str) -> None:
    existing = await repo.get_user_by_email(session, email)
    if existing is not None:
        return
    await repo.create_user(session, email, hash_password(password), role="admin")
    await session.commit()
```

- [ ] **Step 5.5: `deps.py`**

```python
from __future__ import annotations
import uuid
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from . import repo
from .security import decode_token


async def current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = decode_token(token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    user = await repo.get_user_by_id(session, uuid.UUID(sub))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


def require_admin(user=Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
```

`__init__.py`:

```python
from . import deps, schemas, security, service

__all__ = ["deps", "schemas", "security", "service"]
```

- [ ] **Step 5.6: 单元测试 `backend/tests/unit/test_auth_security.py`**

```python
import pytest
from free_hr.auth.security import create_access_token, decode_token, hash_password, verify_password


def test_hash_and_verify_roundtrip():
    h = hash_password("hunter2hunter2")
    assert verify_password("hunter2hunter2", h)
    assert not verify_password("wrong-password", h)


def test_token_roundtrip_has_sub_and_role():
    t = create_access_token("user-123", extra_claims={"role": "hr"})
    claims = decode_token(t)
    assert claims["sub"] == "user-123"
    assert claims["role"] == "hr"


def test_decode_rejects_tampered_token():
    t = create_access_token("user-123") + "x"
    with pytest.raises(ValueError):
        decode_token(t)
```

- [ ] **Step 5.7: 集成测试 `backend/tests/integration/test_auth_flow.py`**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from free_hr.auth.schemas import LoginRequest, RegisterRequest
from free_hr.auth.service import AuthError, bootstrap_admin, login, register
from free_hr.db import get_sessionmaker

pytestmark = pytest.mark.asyncio


async def _clean_users(session: AsyncSession):
    from sqlalchemy import text
    await session.execute(text("DELETE FROM users"))
    await session.commit()


async def test_register_then_login_success():
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean_users(s)
        await register(s, RegisterRequest(email="a@x.com", password="password1", role="hr"))
    async with maker() as s:
        tok = await login(s, LoginRequest(email="a@x.com", password="password1"))
        assert tok.user.email == "a@x.com"
        assert tok.user.role == "hr"
        assert len(tok.token) > 20


async def test_register_duplicate_raises():
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean_users(s)
        await register(s, RegisterRequest(email="b@x.com", password="password1"))
    async with maker() as s:
        with pytest.raises(AuthError, match="already"):
            await register(s, RegisterRequest(email="b@x.com", password="password1"))


async def test_login_wrong_password_raises():
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean_users(s)
        await register(s, RegisterRequest(email="c@x.com", password="password1"))
    async with maker() as s:
        with pytest.raises(AuthError, match="invalid"):
            await login(s, LoginRequest(email="c@x.com", password="wrongpass"))


async def test_bootstrap_admin_is_idempotent():
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean_users(s)
    async with maker() as s:
        await bootstrap_admin(s, "admin@x.com", "adminpass")
    async with maker() as s:
        await bootstrap_admin(s, "admin@x.com", "adminpass")  # 再跑一次，不应报错
    async with maker() as s:
        tok = await login(s, LoginRequest(email="admin@x.com", password="adminpass"))
        assert tok.user.role == "admin"
```

- [ ] **Step 5.8: 运行测试**

```bash
cd backend && uv run pytest tests/unit/test_auth_security.py tests/integration/test_auth_flow.py -v
```

Expected: 7 passed.

- [ ] **Step 5.9: Commit**

```bash
git add backend/src/free_hr/auth/ backend/tests/unit/test_auth_security.py backend/tests/integration/test_auth_flow.py
git commit -m "feat(auth): add password hashing, JWT, register/login/bootstrap admin"
```

---

## Task 6: Knowledge Store 模块

**Files:**
- Create: `backend/src/free_hr/knowledge_store/__init__.py`
- Create: `backend/src/free_hr/knowledge_store/schemas.py`
- Create: `backend/src/free_hr/knowledge_store/repo.py`
- Create: `backend/tests/integration/test_knowledge_store.py`

- [ ] **Step 6.1: `schemas.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import uuid


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
    extra: dict
```

- [ ] **Step 6.2: `repo.py`**

```python
from __future__ import annotations
from collections.abc import Sequence
import uuid
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import CaseChunk, LawChunk
from .schemas import CaseChunkHit, ChunkDetail, LawChunkHit


async def search_laws(
    session: AsyncSession,
    query_vec: Sequence[float],
    k: int = 8,
    regions: Sequence[str] | None = None,
) -> list[LawChunkHit]:
    vec_literal = "[" + ",".join(f"{v:.7f}" for v in query_vec) + "]"
    sql = text(
        """
        SELECT id, law_name, article_no, chapter, text, region, source_url, effective_date,
               1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM law_chunks
        """
        + (" WHERE region = ANY(:regions) " if regions else "")
        + " ORDER BY embedding <=> CAST(:vec AS vector) LIMIT :k"
    )
    params: dict = {"vec": vec_literal, "k": k}
    if regions:
        params["regions"] = list(regions)
    rows = (await session.execute(sql, params)).mappings().all()
    return [
        LawChunkHit(
            id=r["id"], law_name=r["law_name"], article_no=r["article_no"], chapter=r["chapter"],
            text=r["text"], region=r["region"], source_url=r["source_url"],
            effective_date=r["effective_date"], score=float(r["score"]),
        )
        for r in rows
    ]


async def search_cases(
    session: AsyncSession, query_vec: Sequence[float], k: int = 4
) -> list[CaseChunkHit]:
    vec_literal = "[" + ",".join(f"{v:.7f}" for v in query_vec) + "]"
    sql = text(
        """
        SELECT id, case_title, case_no, court, judgment_date, text, source_url,
               1 - (embedding <=> CAST(:vec AS vector)) AS score
        FROM case_chunks
        ORDER BY embedding <=> CAST(:vec AS vector)
        LIMIT :k
        """
    )
    rows = (await session.execute(sql, {"vec": vec_literal, "k": k})).mappings().all()
    return [
        CaseChunkHit(
            id=r["id"], case_title=r["case_title"], case_no=r["case_no"], court=r["court"],
            judgment_date=r["judgment_date"], text=r["text"], source_url=r["source_url"],
            score=float(r["score"]),
        )
        for r in rows
    ]


async def get_chunk(session: AsyncSession, chunk_id: uuid.UUID) -> ChunkDetail | None:
    law = await session.get(LawChunk, chunk_id)
    if law is not None:
        return ChunkDetail(
            id=law.id, kind="law",
            label=f"{law.law_name}·{law.article_no}" if law.article_no else law.law_name,
            text=law.text, source_url=law.source_url,
            extra={"chapter": law.chapter, "region": law.region, "effective_date": law.effective_date.isoformat() if law.effective_date else None},
        )
    case = await session.get(CaseChunk, chunk_id)
    if case is not None:
        return ChunkDetail(
            id=case.id, kind="case",
            label=case.case_no or case.case_title[:32],
            text=case.text, source_url=case.source_url,
            extra={"case_title": case.case_title, "court": case.court, "judgment_date": case.judgment_date.isoformat() if case.judgment_date else None},
        )
    return None


async def list_laws(session: AsyncSession) -> list[dict]:
    sql = text(
        """
        SELECT law_name, region, COUNT(*) AS article_count, MIN(effective_date) AS effective_date
        FROM law_chunks
        GROUP BY law_name, region
        ORDER BY law_name
        """
    )
    return [dict(r) for r in (await session.execute(sql)).mappings().all()]
```

`__init__.py`:

```python
from . import repo, schemas
__all__ = ["repo", "schemas"]
```

- [ ] **Step 6.3: 集成测试 `backend/tests/integration/test_knowledge_store.py`**

```python
import hashlib
import pytest
from sqlalchemy import text
from free_hr.db import get_sessionmaker
from free_hr.knowledge_store import repo
from free_hr.llm_gateway.fake import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio


async def _seed_laws(session, items: list[tuple[str, str, str, str]]):
    """items: (law_name, article_no, region, body)"""
    embedder = FakeEmbeddingProvider(dim=1024)
    for law_name, art, region, body in items:
        vec = (await embedder.embed([body]))[0]
        vec_lit = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"
        h = hashlib.sha256(body.encode("utf-8")).hexdigest()
        await session.execute(
            text(
                "INSERT INTO law_chunks (law_name, article_no, text, region, content_hash, embedding) "
                "VALUES (:ln, :art, :tx, :rg, :ch, CAST(:em AS vector))"
            ),
            {"ln": law_name, "art": art, "tx": body, "rg": region, "ch": h, "em": vec_lit},
        )
    await session.commit()


async def test_search_laws_returns_nearest_first():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(s, [
            ("劳动合同法", "第三十九条", "national", "劳动者严重违反用人单位规章制度的，用人单位可以解除劳动合同"),
            ("劳动合同法", "第四十条", "national", "劳动者不能胜任工作，经过培训或者调整工作岗位仍不能胜任的"),
            ("社会保险法", "第五十八条", "national", "用人单位应当自用工之日起三十日内为其职工申请办理社会保险登记"),
        ])
    embedder = FakeEmbeddingProvider(dim=1024)
    q_vec = (await embedder.embed(["劳动者严重违反用人单位规章制度的，用人单位可以解除劳动合同"]))[0]
    async with maker() as s:
        hits = await repo.search_laws(s, q_vec, k=3)
        assert len(hits) == 3
        assert hits[0].article_no == "第三十九条"
        assert hits[0].score > hits[-1].score


async def test_search_laws_region_filter():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(s, [
            ("劳动合同法", "第三十九条", "national", "aaa"),
            ("北京市工资支付规定", "第十五条", "beijing", "bbb"),
        ])
    embedder = FakeEmbeddingProvider(dim=1024)
    q_vec = (await embedder.embed(["x"]))[0]
    async with maker() as s:
        hits_nat = await repo.search_laws(s, q_vec, k=5, regions=["national"])
        hits_bj = await repo.search_laws(s, q_vec, k=5, regions=["beijing"])
        assert {h.region for h in hits_nat} == {"national"}
        assert {h.region for h in hits_bj} == {"beijing"}


async def test_get_chunk_returns_law_or_none():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(s, [("劳动合同法", "第三十九条", "national", "aaa")])
        row = (await s.execute(text("SELECT id FROM law_chunks LIMIT 1"))).first()
        detail = await repo.get_chunk(s, row[0])
        assert detail is not None
        assert detail.kind == "law"
        assert detail.label == "劳动合同法·第三十九条"
    import uuid
    async with maker() as s:
        assert await repo.get_chunk(s, uuid.uuid4()) is None


async def test_list_laws_aggregates():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM law_chunks"))
        await _seed_laws(s, [
            ("劳动合同法", "第三十九条", "national", "a"),
            ("劳动合同法", "第四十条", "national", "b"),
            ("北京市工资支付规定", "第十五条", "beijing", "c"),
        ])
        rows = await repo.list_laws(s)
        by_name = {r["law_name"]: r for r in rows}
        assert by_name["劳动合同法"]["article_count"] == 2
        assert by_name["北京市工资支付规定"]["region"] == "beijing"
```

- [ ] **Step 6.4: 运行**

```bash
cd backend && uv run pytest tests/integration/test_knowledge_store.py -v
```

Expected: 4 passed.

- [ ] **Step 6.5: Commit**

```bash
git add backend/src/free_hr/knowledge_store/ backend/tests/integration/test_knowledge_store.py
git commit -m "feat(knowledge_store): add pgvector search for laws/cases with region filter"
```

---

## Task 7: Knowledge Ingest 模块 + CLI

**Files:**
- Create: `backend/src/free_hr/knowledge_ingest/__init__.py`
- Create: `backend/src/free_hr/knowledge_ingest/chunker.py`
- Create: `backend/src/free_hr/knowledge_ingest/parsers.py`
- Create: `backend/src/free_hr/knowledge_ingest/pipeline.py`
- Create: `backend/src/free_hr/knowledge_ingest/cli.py`
- Create: `backend/tests/unit/test_chunker.py`
- Create: `backend/tests/integration/test_ingest_pipeline.py`

- [ ] **Step 7.1: `chunker.py`——法条分块**

```python
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
    """按「第X条」硬切分，带回所在章。"""
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
    # fallback: 按字符窗口切
    out, i = [], 0
    while i < len(text):
        out.append(text[i : i + _MAX_CHUNK_CHARS])
        i += _MAX_CHUNK_CHARS - 80  # 80 char overlap
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
```

- [ ] **Step 7.2: `parsers.py`——读原文，解析元信息**

```python
from __future__ import annotations
import json
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
    """法规原文文件：首行为 `# 法名` 可选第二行 `<!-- region: beijing, effective: 2008-01-01, url: ... -->`，其余为正文。"""
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
    return LawSource(law_name=law_name, region=region, effective_date=effective_date, source_url=source_url, body=body)
```

- [ ] **Step 7.3: `pipeline.py`——摄入 orchestration**

```python
from __future__ import annotations
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from ..llm_gateway import EmbeddingProvider
from ..models import IngestionRun, LawChunk
from .chunker import LawChunkDraft, chunk_law
from .parsers import read_law_file


@dataclass
class IngestStats:
    chunks_created: int = 0
    chunks_skipped: int = 0
    errors: int = 0


async def ingest_law_file(
    session: AsyncSession, embedder: EmbeddingProvider, path: Path, batch_size: int = 16
) -> IngestStats:
    run = IngestionRun(source_type="law", source_path=str(path), status="running")
    session.add(run)
    await session.flush()
    stats = IngestStats()
    try:
        src = read_law_file(path)
        drafts = chunk_law(src.law_name, src.body)
        effective = dt.date.fromisoformat(src.effective_date) if src.effective_date else None

        existing_hashes = set(
            (await session.execute(
                select(LawChunk.content_hash).where(LawChunk.law_name == src.law_name, LawChunk.region == src.region)
            )).scalars()
        )
        new_drafts = [d for d in drafts if d.content_hash not in existing_hashes]
        stats.chunks_skipped = len(drafts) - len(new_drafts)

        for i in range(0, len(new_drafts), batch_size):
            batch = new_drafts[i : i + batch_size]
            embeddings = await embedder.embed([d.text for d in batch])
            for d, emb in zip(batch, embeddings, strict=True):
                session.add(LawChunk(
                    law_name=d.law_name, article_no=d.article_no, chapter=d.chapter, text=d.text,
                    region=src.region, source_url=src.source_url, effective_date=effective,
                    content_hash=d.content_hash, embedding=emb,
                ))
            await session.flush()

        stats.chunks_created = len(new_drafts)
        run.status = "completed"
        run.stats_json = {"chunks_created": stats.chunks_created, "chunks_skipped": stats.chunks_skipped}
        run.finished_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
    except Exception as e:
        await session.rollback()
        # 在新事务里记录失败状态
        run2 = IngestionRun(source_type="law", source_path=str(path), status="failed", error_detail=repr(e),
                            finished_at=dt.datetime.now(dt.timezone.utc))
        session.add(run2)
        await session.commit()
        stats.errors = 1
        raise
    return stats


async def ingest_directory(
    session_factory, embedder: EmbeddingProvider, directory: Path
) -> dict[str, IngestStats]:
    results: dict[str, IngestStats] = {}
    for path in sorted(directory.rglob("*.txt")):
        async with session_factory() as session:
            results[str(path)] = await ingest_law_file(session, embedder, path)
    return results
```

- [ ] **Step 7.4: CLI `cli.py`**

```python
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


@app.command()
def all():
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
```

`__init__.py`:

```python
from . import chunker, parsers, pipeline

__all__ = ["chunker", "parsers", "pipeline"]
```

- [ ] **Step 7.5: 单元测试 `backend/tests/unit/test_chunker.py`**

```python
from free_hr.knowledge_ingest.chunker import chunk_law

SAMPLE = """第一章 总则
第一条 为了规范用人单位的规章制度，制定本法。
第二条 本法适用于中华人民共和国境内的企业、个体经济组织。
第二章 劳动合同的订立
第十条 建立劳动关系，应当订立书面劳动合同。
第三十九条 劳动者有下列情形之一的，用人单位可以解除劳动合同：
（一）在试用期间被证明不符合录用条件的；
（二）严重违反用人单位的规章制度的；
（三）严重失职，营私舞弊，给用人单位造成重大损害的。
"""


def test_chunk_law_splits_by_article():
    chunks = chunk_law("劳动合同法", SAMPLE)
    nos = [c.article_no for c in chunks]
    assert "第一条" in nos
    assert "第十条" in nos
    assert "第三十九条" in nos


def test_chunk_law_attaches_chapter():
    chunks = chunk_law("劳动合同法", SAMPLE)
    first = next(c for c in chunks if c.article_no == "第一条")
    tenth = next(c for c in chunks if c.article_no == "第十条")
    assert "总则" in (first.chapter or "")
    assert "劳动合同的订立" in (tenth.chapter or "")


def test_chunk_law_hashes_are_stable_and_unique():
    a = chunk_law("劳动合同法", SAMPLE)
    b = chunk_law("劳动合同法", SAMPLE)
    assert [c.content_hash for c in a] == [c.content_hash for c in b]
    assert len({c.content_hash for c in a}) == len(a)


def test_long_article_splits_by_subclause():
    long_article = "第九十九条 " + "".join(
        f"（{chr(0x4E00 + i)}）详细条款正文" + "x" * 200 for i in range(5)
    )
    chunks = chunk_law("某大法", long_article)
    assert len(chunks) > 1
    assert all(len(c.text) <= 1000 for c in chunks)
```

- [ ] **Step 7.6: 集成测试 `backend/tests/integration/test_ingest_pipeline.py`**

```python
import os
from pathlib import Path
import pytest
from sqlalchemy import text
from free_hr.db import get_sessionmaker
from free_hr.knowledge_ingest.pipeline import ingest_law_file
from free_hr.llm_gateway.fake import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio


@pytest.fixture
def tiny_law_file(tmp_path):
    p = tmp_path / "tiny.txt"
    p.write_text(
        """# 测试劳动法
<!-- region: beijing, effective: 2024-01-01 -->
第一条 本法为测试。
第二条 劳动者应当遵守。
""",
        encoding="utf-8",
    )
    return p


async def _clean(session):
    await session.execute(text("DELETE FROM law_chunks"))
    await session.execute(text("DELETE FROM ingestion_runs"))
    await session.commit()


async def test_ingest_law_file_creates_chunks_and_run_record(tiny_law_file: Path):
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean(s)
    async with maker() as s:
        stats = await ingest_law_file(s, FakeEmbeddingProvider(dim=1024), tiny_law_file)
        assert stats.chunks_created == 2
    async with maker() as s:
        count = (await s.execute(text("SELECT COUNT(*) FROM law_chunks WHERE region='beijing'"))).scalar_one()
        assert count == 2
        runs = (await s.execute(text("SELECT status FROM ingestion_runs"))).scalars().all()
        assert runs == ["completed"]


async def test_ingest_is_idempotent(tiny_law_file: Path):
    maker = get_sessionmaker()
    async with maker() as s:
        await _clean(s)
    async with maker() as s:
        await ingest_law_file(s, FakeEmbeddingProvider(dim=1024), tiny_law_file)
    async with maker() as s:
        stats = await ingest_law_file(s, FakeEmbeddingProvider(dim=1024), tiny_law_file)
        assert stats.chunks_created == 0
        assert stats.chunks_skipped == 2
```

- [ ] **Step 7.7: 运行测试**

```bash
cd backend && uv run pytest tests/unit/test_chunker.py tests/integration/test_ingest_pipeline.py -v
```

Expected: 6 passed。

- [ ] **Step 7.8: Commit**

```bash
git add backend/src/free_hr/knowledge_ingest/ backend/tests/unit/test_chunker.py backend/tests/integration/test_ingest_pipeline.py
git commit -m "feat(knowledge_ingest): add law chunker + ingestion pipeline + Typer CLI"
```

---

## Task 8: Chat 核心——Prompt 装配 + 引用解析（纯函数）

**Files:**
- Create: `backend/src/free_hr/chat/__init__.py`
- Create: `backend/src/free_hr/chat/schemas.py`
- Create: `backend/src/free_hr/chat/prompt.py`
- Create: `backend/src/free_hr/chat/citations.py`
- Create: `backend/tests/unit/test_prompt.py`
- Create: `backend/tests/unit/test_citations.py`

- [ ] **Step 8.1: `schemas.py`**

```python
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
```

- [ ] **Step 8.2: `prompt.py`**

```python
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
        if remaining - len(ref.text) < 0 and selected:
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
```

- [ ] **Step 8.3: `citations.py`**

```python
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
```

`__init__.py`:

```python
from . import citations, prompt, schemas

__all__ = ["citations", "prompt", "schemas"]
```

- [ ] **Step 8.4: 测试 `backend/tests/unit/test_prompt.py`**

```python
import uuid
from datetime import date
from free_hr.chat.prompt import build_context_refs, render_context_block
from free_hr.knowledge_store.schemas import CaseChunkHit, LawChunkHit


def _law(text, score, art="第X条"):
    return LawChunkHit(
        id=uuid.uuid4(), law_name="劳动合同法", article_no=art, chapter=None,
        text=text, region="national", source_url=None, effective_date=date(2008, 1, 1), score=score,
    )


def _case(text, score):
    return CaseChunkHit(
        id=uuid.uuid4(), case_title="示例", case_no="(2023)京01民终1号", court=None,
        judgment_date=None, text=text, source_url=None, score=score,
    )


def test_build_context_refs_sorts_by_score_and_assigns_idx():
    refs = build_context_refs([_law("A", 0.3), _law("B", 0.9)], [_case("C", 0.7)])
    assert [r.idx for r in refs] == [1, 2, 3]
    assert refs[0].text == "B"
    assert refs[1].text == "C"
    assert refs[2].text == "A"


def test_build_context_refs_truncates_at_budget():
    big = "x" * 4000
    refs = build_context_refs([_law(big, 0.9, "第1条"), _law(big, 0.8, "第2条"), _law(big, 0.7, "第3条")], [])
    assert len(refs) == 2  # 第三条超预算被截


def test_build_context_refs_dedupes_same_chunk_id():
    same = _law("A", 0.9)
    refs = build_context_refs([same, same], [])
    assert len(refs) == 1


def test_render_context_block_contains_numbering_and_labels():
    refs = build_context_refs([_law("劳动者严重违反规章制度", 0.9, "第三十九条")], [_case("案例正文", 0.8)])
    block = render_context_block(refs)
    assert "[#1]" in block
    assert "[#2]" in block
    assert "法条·劳动合同法·第三十九条" in block
    assert "案例·(2023)京01民终1号" in block


def test_render_context_block_handles_empty():
    block = render_context_block([])
    assert "未找到相关法条" in block
```

- [ ] **Step 8.5: 测试 `backend/tests/unit/test_citations.py`**

```python
from free_hr.chat.citations import count_oob, extract_citations
from free_hr.chat.schemas import ContextRef


def _refs(n: int) -> list[ContextRef]:
    return [ContextRef(idx=i, kind="law", chunk_id=f"id-{i}", label=f"L{i}", text="") for i in range(1, n + 1)]


def test_extract_citations_preserves_first_occurrence_order():
    refs = _refs(3)
    text = "结论A [#2]。再看[#1]和[#2]，最后 [#3]。"
    out = extract_citations(text, refs)
    assert [c["idx"] for c in out] == [2, 1, 3]


def test_extract_citations_filters_out_of_bound():
    refs = _refs(2)
    text = "A [#1][#9][#2][#17]"
    out = extract_citations(text, refs)
    assert [c["idx"] for c in out] == [1, 2]


def test_count_oob_counts_every_occurrence():
    refs = _refs(2)
    text = "[#1][#5][#5][#2]"
    assert count_oob(text, refs) == 2
```

- [ ] **Step 8.6: 运行**

```bash
cd backend && uv run pytest tests/unit/test_prompt.py tests/unit/test_citations.py -v
```

Expected: 8 passed.

- [ ] **Step 8.7: Commit**

```bash
git add backend/src/free_hr/chat/ backend/tests/unit/test_prompt.py backend/tests/unit/test_citations.py
git commit -m "feat(chat): add system prompt, context builder, citation parser (pure fns)"
```

---

## Task 9: Chat 服务 + RAG pipeline

**Files:**
- Create: `backend/src/free_hr/chat/repo.py`
- Create: `backend/src/free_hr/chat/service.py`
- Create: `backend/tests/integration/test_chat_flow.py`

- [ ] **Step 9.1: `repo.py`**

```python
from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import ChatMessage, ChatSession


async def create_session(session: AsyncSession, user_id: uuid.UUID, title: str) -> ChatSession:
    obj = ChatSession(user_id=user_id, title=title or "新会话")
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def list_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[ChatSession]:
    stmt = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_session_for_user(session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
    stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_messages(session: AsyncSession, session_id: uuid.UUID) -> list[ChatMessage]:
    stmt = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
    return list((await session.execute(stmt)).scalars().all())


async def append_message(
    session: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    citations_json: list | None = None,
    token_usage_json: dict | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id, role=role, content=content,
        citations_json=citations_json, token_usage_json=token_usage_json,
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    return msg
```

- [ ] **Step 9.2: `service.py`——RAG pipeline + 流式回答**

```python
from __future__ import annotations
from collections.abc import AsyncIterator, Sequence
import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from ..knowledge_store import repo as ks_repo
from ..llm_gateway import ChatMessage as LLMMessage, ChatOptions, EmbeddingProvider, LLMProvider
from ..models import ChatMessage as DbMessage
from .citations import count_oob, extract_citations
from .prompt import SYSTEM_PROMPT, build_context_refs, render_context_block
from .schemas import ChatEvent, ChatEventType, ContextRef
from . import repo as chat_repo

log = logging.getLogger("free_hr.chat")

_HISTORY_TURNS = 6


def _compose_messages(system: str, history: Sequence[DbMessage], user_text: str) -> list[LLMMessage]:
    msgs: list[LLMMessage] = [LLMMessage(role="system", content=system)]
    tail = list(history)[-(_HISTORY_TURNS * 2):]
    for m in tail:
        msgs.append(LLMMessage(role=m.role, content=m.content))
    msgs.append(LLMMessage(role="user", content=user_text))
    return msgs


async def _retrieve(
    session: AsyncSession, embedder: EmbeddingProvider, query: str,
) -> list[ContextRef]:
    vec = (await embedder.embed([query]))[0]
    laws = await ks_repo.search_laws(session, vec, k=8, regions=["national", "beijing"])
    cases = await ks_repo.search_cases(session, vec, k=4)
    return build_context_refs(laws, cases)


async def stream_answer(
    session: AsyncSession,
    *,
    llm: LLMProvider,
    embedder: EmbeddingProvider,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    user_text: str,
) -> AsyncIterator[ChatEvent]:
    chat_session = await chat_repo.get_session_for_user(session, session_id, user_id)
    if chat_session is None:
        yield ChatEvent(type=ChatEventType.ERROR, data={"code": "not_found", "message": "session not found"})
        return

    await chat_repo.append_message(session, session_id, "user", user_text)

    try:
        refs = await _retrieve(session, embedder, user_text)
    except Exception as e:
        log.exception("retrieve failed")
        yield ChatEvent(type=ChatEventType.ERROR, data={"code": "retrieval_error", "message": str(e)})
        return

    context_block = render_context_block(refs)
    system = f"{SYSTEM_PROMPT}\n\n{context_block}"
    history = await chat_repo.list_messages(session, session_id)
    history = [m for m in history if m.content != user_text or m.role != "user"] + [m for m in history if m.content == user_text and m.role == "user"][:-1]
    messages = _compose_messages(system, history, user_text)

    buf: list[str] = []
    usage: dict | None = None
    try:
        async for chunk in llm.chat_stream(messages, ChatOptions()):
            if chunk.delta_text:
                buf.append(chunk.delta_text)
                yield ChatEvent(type=ChatEventType.TOKEN, data={"text": chunk.delta_text})
            if chunk.usage:
                usage = chunk.usage
    except Exception as e:
        log.exception("llm stream failed")
        yield ChatEvent(type=ChatEventType.ERROR, data={"code": "llm_error", "message": str(e)})
        return

    full_text = "".join(buf)
    citations = extract_citations(full_text, refs)
    oob = count_oob(full_text, refs)
    if oob:
        log.warning("citation out-of-bound count=%s session=%s", oob, session_id)

    saved = await chat_repo.append_message(session, session_id, "assistant", full_text, citations_json=citations, token_usage_json=usage)
    yield ChatEvent(type=ChatEventType.CITATIONS, data={"citations": citations})
    yield ChatEvent(type=ChatEventType.DONE, data={"message_id": str(saved.id)})
```

- [ ] **Step 9.3: 集成测试 `backend/tests/integration/test_chat_flow.py`**

```python
import hashlib
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from free_hr.auth.service import bootstrap_admin
from free_hr.auth.repo import get_user_by_email
from free_hr.chat import repo as chat_repo
from free_hr.chat.service import stream_answer
from free_hr.chat.schemas import ChatEventType
from free_hr.db import get_sessionmaker
from free_hr.llm_gateway.fake import FakeEmbeddingProvider, FakeLLMProvider

pytestmark = pytest.mark.asyncio


async def _seed_laws(session: AsyncSession):
    await session.execute(text("DELETE FROM law_chunks"))
    embedder = FakeEmbeddingProvider(dim=1024)
    for law, art, body in [
        ("劳动合同法", "第三十九条", "劳动者严重违反用人单位规章制度的，用人单位可以解除劳动合同"),
        ("劳动合同法", "第四十七条", "经济补偿按劳动者在本单位工作年限计算"),
    ]:
        vec = (await embedder.embed([body]))[0]
        vec_lit = "[" + ",".join(f"{v:.7f}" for v in vec) + "]"
        await session.execute(
            text(
                "INSERT INTO law_chunks (law_name, article_no, text, region, content_hash, embedding) "
                "VALUES (:ln, :art, :tx, 'national', :ch, CAST(:em AS vector))"
            ),
            {"ln": law, "art": art, "tx": body, "ch": hashlib.sha256(body.encode()).hexdigest(), "em": vec_lit},
        )
    await session.commit()


async def _fresh_user(session: AsyncSession, email: str):
    await session.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
    await session.commit()
    await bootstrap_admin(session, email, "pwd12345")
    return await get_user_by_email(session, email)


async def test_stream_answer_emits_token_citations_done():
    maker = get_sessionmaker()
    async with maker() as s:
        await _seed_laws(s)
        user = await _fresh_user(s, "chat_it_1@x.com")
        session_row = await chat_repo.create_session(s, user.id, "t")
        uid, sid = user.id, session_row.id

    llm = FakeLLMProvider(script=["结论：可以解除[#1]。 相关依据见上。 经济补偿参考[#2]."])
    async with maker() as s:
        events = []
        async for evt in stream_answer(
            s, llm=llm, embedder=FakeEmbeddingProvider(dim=1024),
            user_id=uid, session_id=sid, user_text="严重违反规章制度能不能解除？",
        ):
            events.append(evt)

    types = [e.type for e in events]
    assert types[0] == ChatEventType.TOKEN
    assert ChatEventType.CITATIONS in types
    assert types[-1] == ChatEventType.DONE
    cit_evt = next(e for e in events if e.type == ChatEventType.CITATIONS)
    assert {c["idx"] for c in cit_evt.data["citations"]} == {1, 2}


async def test_stream_answer_rejects_other_users_session():
    maker = get_sessionmaker()
    async with maker() as s:
        await _seed_laws(s)
        u1 = await _fresh_user(s, "chat_it_a@x.com")
        u2 = await _fresh_user(s, "chat_it_b@x.com")
        sess = await chat_repo.create_session(s, u1.id, "t")
        foreign_uid = u2.id
        sid = sess.id

    async with maker() as s:
        events = []
        async for evt in stream_answer(
            s, llm=FakeLLMProvider(), embedder=FakeEmbeddingProvider(dim=1024),
            user_id=foreign_uid, session_id=sid, user_text="hi",
        ):
            events.append(evt)
    assert events[0].type == ChatEventType.ERROR
    assert events[0].data["code"] == "not_found"


async def test_assistant_message_persists_with_citations():
    maker = get_sessionmaker()
    async with maker() as s:
        await _seed_laws(s)
        user = await _fresh_user(s, "chat_it_2@x.com")
        sess = await chat_repo.create_session(s, user.id, "t")
        uid, sid = user.id, sess.id

    async with maker() as s:
        async for _ in stream_answer(
            s, llm=FakeLLMProvider(script=["A[#1]."]), embedder=FakeEmbeddingProvider(dim=1024),
            user_id=uid, session_id=sid, user_text="q",
        ):
            pass

    async with maker() as s:
        msgs = await chat_repo.list_messages(s, sid)
        roles = [m.role for m in msgs]
        assert roles == ["user", "assistant"]
        assert msgs[1].citations_json and msgs[1].citations_json[0]["idx"] == 1
```

- [ ] **Step 9.4: 运行**

```bash
cd backend && uv run pytest tests/integration/test_chat_flow.py -v
```

Expected: 3 passed.

- [ ] **Step 9.5: Commit**

```bash
git add backend/src/free_hr/chat/repo.py backend/src/free_hr/chat/service.py backend/tests/integration/test_chat_flow.py
git commit -m "feat(chat): add RAG pipeline with two-way retrieval and streaming answer"
```

---

## Task 10: API 路由装配 + 异常处理 + SSE 端点

**Files:**
- Modify: `backend/src/free_hr/api/main.py`
- Create: `backend/src/free_hr/api/errors.py`
- Create: `backend/src/free_hr/api/sse.py`
- Create: `backend/src/free_hr/api/routes/__init__.py`
- Create: `backend/src/free_hr/api/routes/auth.py`
- Create: `backend/src/free_hr/api/routes/chat.py`
- Create: `backend/src/free_hr/api/routes/knowledge.py`
- Create: `backend/src/free_hr/api/lifespan.py`
- Create: `backend/tests/integration/test_api_endpoints.py`

- [ ] **Step 10.1: `errors.py`**

```python
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from ..auth.service import AuthError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def auth_error_handler(_req: Request, exc: AuthError):
        return JSONResponse(status_code=400, content={"error": str(exc)})
```

- [ ] **Step 10.2: `sse.py`——把 ChatEvent 转成 SSE**

```python
from __future__ import annotations
import json
from collections.abc import AsyncIterator
from ..chat.schemas import ChatEvent


async def chat_events_to_sse(events: AsyncIterator[ChatEvent]) -> AsyncIterator[dict]:
    async for evt in events:
        yield {"event": evt.type.value, "data": json.dumps(evt.data, ensure_ascii=False)}
```

- [ ] **Step 10.3: `routes/auth.py`**

```python
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ...auth import deps, schemas, service
from ...db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
async def login(body: schemas.LoginRequest, session: AsyncSession = Depends(get_db)):
    return await service.login(session, body)


@router.post("/register", response_model=schemas.UserInfo)
async def register(
    body: schemas.RegisterRequest,
    session: AsyncSession = Depends(get_db),
    _admin=Depends(deps.require_admin),
):
    return await service.register(session, body)


@router.get("/me", response_model=schemas.UserInfo)
async def me(user=Depends(deps.current_user)):
    return schemas.UserInfo(id=str(user.id), email=user.email, role=user.role)
```

- [ ] **Step 10.4: `routes/knowledge.py`**

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ...auth import deps
from ...db import get_db
from ...knowledge_store import repo as ks_repo

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/laws")
async def list_laws(session: AsyncSession = Depends(get_db), _user=Depends(deps.current_user)):
    return {"laws": await ks_repo.list_laws(session)}


@router.get("/chunks/{chunk_id}")
async def get_chunk(chunk_id: uuid.UUID, session: AsyncSession = Depends(get_db), _user=Depends(deps.current_user)):
    detail = await ks_repo.get_chunk(session, chunk_id)
    if detail is None:
        raise HTTPException(404, "chunk not found")
    return {
        "id": str(detail.id), "kind": detail.kind, "label": detail.label,
        "text": detail.text, "source_url": detail.source_url, "extra": detail.extra,
    }
```

- [ ] **Step 10.5: `routes/chat.py`（SSE）**

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from ...auth import deps
from ...chat import repo as chat_repo
from ...chat.service import stream_answer
from ...db import get_db, get_sessionmaker
from ...llm_gateway import get_embedder, get_llm
from ..sse import chat_events_to_sse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions")
async def create_session(
    body: dict = Body(default_factory=dict),
    session: AsyncSession = Depends(get_db),
    user=Depends(deps.current_user),
):
    title = (body or {}).get("title") or "新会话"
    obj = await chat_repo.create_session(session, user.id, title)
    return {"id": str(obj.id), "title": obj.title, "created_at": obj.created_at.isoformat()}


@router.get("/sessions")
async def list_sessions(session: AsyncSession = Depends(get_db), user=Depends(deps.current_user)):
    items = await chat_repo.list_sessions(session, user.id)
    return {"sessions": [{"id": str(o.id), "title": o.title, "created_at": o.created_at.isoformat()} for o in items]}


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: uuid.UUID, session: AsyncSession = Depends(get_db), user=Depends(deps.current_user)):
    if await chat_repo.get_session_for_user(session, session_id, user.id) is None:
        raise HTTPException(404, "session not found")
    msgs = await chat_repo.list_messages(session, session_id)
    return {
        "messages": [
            {
                "id": str(m.id), "role": m.role, "content": m.content,
                "citations": m.citations_json or [], "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ]
    }


@router.post("/sessions/{session_id}/messages")
async def post_message(
    session_id: uuid.UUID,
    body: dict = Body(...),
    user=Depends(deps.current_user),
):
    content = (body or {}).get("content", "").strip()
    if not content:
        raise HTTPException(400, "content required")

    uid = user.id
    sm = get_sessionmaker()
    llm = get_llm()
    embedder = get_embedder()

    async def event_stream():
        async with sm() as s:
            async for sse in chat_events_to_sse(
                stream_answer(s, llm=llm, embedder=embedder, user_id=uid, session_id=session_id, user_text=content)
            ):
                yield sse

    return EventSourceResponse(event_stream())
```

- [ ] **Step 10.6: `lifespan.py`（启动时 bootstrap admin）**

```python
from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from ..auth.service import bootstrap_admin
from ..config import get_settings
from ..db import get_sessionmaker


@asynccontextmanager
async def lifespan(_app: FastAPI):
    s = get_settings()
    async with get_sessionmaker()() as session:
        await bootstrap_admin(session, s.admin_email, s.admin_password)
    yield
```

- [ ] **Step 10.7: 改造 `api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings
from .errors import register_exception_handlers
from .lifespan import lifespan
from .routes import auth as auth_routes
from .routes import chat as chat_routes
from .routes import knowledge as knowledge_routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Free-HR API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(auth_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(knowledge_routes.router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

`routes/__init__.py` 为空。

- [ ] **Step 10.8: API 集成测试 `backend/tests/integration/test_api_endpoints.py`**

```python
import json
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from asgi_lifespan import LifespanManager

from free_hr.api.main import app
from free_hr.auth.service import bootstrap_admin
from free_hr.db import get_sessionmaker

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    maker = get_sessionmaker()
    async with maker() as s:
        await s.execute(text("DELETE FROM chat_messages"))
        await s.execute(text("DELETE FROM chat_sessions"))
        await s.execute(text("DELETE FROM users"))
        await s.commit()
    async with maker() as s:
        await bootstrap_admin(s, "admin@x.com", "admin123!")
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


async def _login(c, email, password):
    r = await c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


async def test_login_me_and_register_flow(client):
    tok = await _login(client, "admin@x.com", "admin123!")
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    r = await client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {tok}"},
        json={"email": "hr1@x.com", "password": "hr_pass_123", "role": "hr"},
    )
    assert r.status_code == 200
    r2 = await client.post("/api/auth/login", json={"email": "hr1@x.com", "password": "hr_pass_123"})
    assert r2.status_code == 200


async def test_non_admin_cannot_register(client):
    tok = await _login(client, "admin@x.com", "admin123!")
    await client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {tok}"},
        json={"email": "hr2@x.com", "password": "hr_pass_123", "role": "hr"},
    )
    hr_tok = (await client.post("/api/auth/login", json={"email": "hr2@x.com", "password": "hr_pass_123"})).json()["token"]
    r = await client.post(
        "/api/auth/register",
        headers={"Authorization": f"Bearer {hr_tok}"},
        json={"email": "x@x.com", "password": "abc12345", "role": "hr"},
    )
    assert r.status_code == 403


async def test_chat_session_crud(client):
    tok = await _login(client, "admin@x.com", "admin123!")
    h = {"Authorization": f"Bearer {tok}"}
    r = await client.post("/api/chat/sessions", headers=h, json={"title": "first"})
    assert r.status_code == 200
    sid = r.json()["id"]
    r = await client.get("/api/chat/sessions", headers=h)
    assert any(s["id"] == sid for s in r.json()["sessions"])
    r = await client.get(f"/api/chat/sessions/{sid}/messages", headers=h)
    assert r.status_code == 200
    assert r.json()["messages"] == []


async def test_chat_sse_stream_returns_events(client, monkeypatch):
    # 切换到 fake provider，避免调用外部 API
    from free_hr.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "fake")

    tok = await _login(client, "admin@x.com", "admin123!")
    h = {"Authorization": f"Bearer {tok}"}
    sid = (await client.post("/api/chat/sessions", headers=h, json={"title": "t"})).json()["id"]
    async with client.stream("POST", f"/api/chat/sessions/{sid}/messages", headers=h, json={"content": "hello"}) as r:
        events: list[tuple[str, str]] = []
        cur_event = None
        async for line in r.aiter_lines():
            line = line.strip()
            if line.startswith("event:"):
                cur_event = line[6:].strip()
            elif line.startswith("data:") and cur_event:
                events.append((cur_event, line[5:].strip()))
                cur_event = None
    types = [t for t, _ in events]
    assert "token" in types
    assert "done" in types
```

- [ ] **Step 10.9: 运行**

```bash
cd backend && uv run pytest tests/integration/test_api_endpoints.py -v
```

Expected: 4 passed.

- [ ] **Step 10.10: Commit**

```bash
git add backend/src/free_hr/api/ backend/tests/integration/test_api_endpoints.py
git commit -m "feat(api): wire up auth, chat SSE, knowledge routes with lifespan bootstrap"
```

---

## Task 11: 前端骨架 + Tailwind + shadcn/ui

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/page.tsx`
- Create: `frontend/.env.example`
- Create: `frontend/components/ui/button.tsx` (from shadcn)
- Create: `frontend/components/ui/input.tsx` (from shadcn)
- Create: `frontend/components/ui/card.tsx` (from shadcn)
- Create: `frontend/lib/utils.ts`

- [ ] **Step 11.1: `package.json`**

```json
{
  "name": "free-hr-frontend",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.15",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@radix-ui/react-popover": "^1.1.2",
    "@radix-ui/react-slot": "^1.1.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "lucide-react": "^0.452.0",
    "tailwind-merge": "^2.5.4",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.16.11",
    "@types/react": "18.3.11",
    "@types/react-dom": "18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "autoprefixer": "^10.4.20",
    "eslint": "^8.57.1",
    "eslint-config-next": "14.2.15",
    "happy-dom": "^15.7.4",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.13",
    "tailwindcss-animate": "^1.0.7",
    "typescript": "^5.6.3",
    "vitest": "^2.1.3",
    "@testing-library/react": "^16.0.1",
    "@testing-library/dom": "^10.4.0"
  }
}
```

- [ ] **Step 11.2: `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 11.3: `next.config.mjs`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
export default nextConfig;
```

- [ ] **Step 11.4: Tailwind + PostCSS 配置**

`tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)" },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
```

`postcss.config.js`:

```javascript
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };
```

- [ ] **Step 11.5: `app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222 47% 11%;
    --primary: 221 83% 53%;
    --primary-foreground: 210 40% 98%;
    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;
    --accent: 210 40% 96%;
    --accent-foreground: 222 47% 11%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 210 40% 98%;
    --border: 214 32% 91%;
    --radius: 0.5rem;
  }
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
```

- [ ] **Step 11.6: `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Free-HR",
  description: "AI 劳动法合规咨询",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">
        {children}
        <footer className="fixed bottom-0 inset-x-0 text-xs text-muted-foreground text-center py-2 bg-background/80 backdrop-blur">
          本工具仅供参考，不构成法律意见。
        </footer>
      </body>
    </html>
  );
}
```

- [ ] **Step 11.7: `app/page.tsx`——根据登录态重定向**

```tsx
import { redirect } from "next/navigation";
import { cookies } from "next/headers";

export default function Home() {
  const token = cookies().get("free_hr_token")?.value;
  redirect(token ? "/chat" : "/login");
}
```

- [ ] **Step 11.8: `lib/utils.ts`**

```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 11.9: shadcn/ui 基础组件（手写等价最小版本）**

`components/ui/button.tsx`:

```tsx
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
      },
      size: { sm: "h-8 px-3", md: "h-10 px-4", lg: "h-11 px-6" },
    },
    defaultVariants: { variant: "default", size: "md" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";
```

`components/ui/input.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
        "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        className
      )}
      ref={ref}
      {...props}
    />
  )
);
Input.displayName = "Input";
```

`components/ui/card.tsx`:

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />
  )
);
Card.displayName = "Card";

export const CardHeader = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col space-y-1.5 p-6", className)} {...p} />
);
export const CardContent = ({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-6 pt-0", className)} {...p} />
);
export const CardTitle = ({ className, ...p }: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={cn("text-2xl font-semibold leading-none tracking-tight", className)} {...p} />
);
```

- [ ] **Step 11.10: `frontend/.env.example`**

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 11.11: 启动前端 dev server 手动验证**

```bash
cd frontend && pnpm install && pnpm dev
```

访问 http://localhost:3000，应 301 到 /login（页面还没创建，会 404，这是下一个 task 的事；但 `/api/health` 代理应可用）。

- [ ] **Step 11.12: Commit**

```bash
git add frontend/
git commit -m "chore(frontend): scaffold Next.js 14 + Tailwind + base UI primitives"
```

---

## Task 12: 登录页 + Auth Store + API client

**Files:**
- Create: `frontend/lib/api-client.ts`
- Create: `frontend/lib/auth-store.ts`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/components/auth/login-form.tsx`

- [ ] **Step 12.1: `lib/api-client.ts`**

```typescript
export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

const BASE = ""; // 使用 Next rewrites，前端直接走 /api/*

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const r = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    let body: unknown = null;
    try { body = await r.json(); } catch {}
    throw new ApiError(r.status, `${r.status} ${r.statusText}`, body);
  }
  return (await r.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ token: string; user: { id: string; email: string; role: string } }>("/api/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  me: (token: string) =>
    request<{ id: string; email: string; role: string }>("/api/auth/me", {}, token),
  createSession: (token: string, title?: string) =>
    request<{ id: string; title: string; created_at: string }>("/api/chat/sessions", {
      method: "POST", body: JSON.stringify({ title }),
    }, token),
  listSessions: (token: string) =>
    request<{ sessions: { id: string; title: string; created_at: string }[] }>("/api/chat/sessions", {}, token),
  listMessages: (token: string, sid: string) =>
    request<{ messages: { id: string; role: string; content: string; citations: any[]; created_at: string }[] }>(
      `/api/chat/sessions/${sid}/messages`, {}, token
    ),
  getChunk: (token: string, chunkId: string) =>
    request<{ id: string; kind: string; label: string; text: string; source_url: string | null; extra: any }>(
      `/api/knowledge/chunks/${chunkId}`, {}, token
    ),
  listLaws: (token: string) =>
    request<{ laws: { law_name: string; region: string; article_count: number; effective_date: string | null }[] }>(
      "/api/knowledge/laws", {}, token
    ),
};
```

- [ ] **Step 12.2: `lib/auth-store.ts`**

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User { id: string; email: string; role: string }

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => {
        document.cookie = `free_hr_token=${token}; path=/; SameSite=Lax`;
        set({ token, user });
      },
      logout: () => {
        document.cookie = "free_hr_token=; path=/; max-age=0";
        set({ token: null, user: null });
      },
    }),
    { name: "free_hr_auth" }
  )
);
```

- [ ] **Step 12.3: `components/auth/login-form.tsx`**

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function LoginForm() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { token, user } = await api.login(email, password);
      setAuth(token, user);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? (err.status === 400 ? "邮箱或密码错误" : err.message) : "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Free-HR 登录</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "登录中…" : "登录"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 12.4: `app/login/page.tsx`**

```tsx
import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <main className="min-h-screen grid place-items-center p-6">
      <LoginForm />
    </main>
  );
}
```

- [ ] **Step 12.5: 手动验证**

后端跑起来（fake provider 亦可）、admin 已 bootstrap，浏览器访问 /login，用 `admin@example.com` / `.env` 里设置的密码登录，应跳 /chat（下一 task 再实现页面）。

- [ ] **Step 12.6: Commit**

```bash
git add frontend/lib frontend/app/login frontend/components/auth
git commit -m "feat(frontend): add login page, API client, zustand auth store"
```

---

## Task 13: Chat 页——会话侧栏 + 消息列表 + SSE 流式

**Files:**
- Create: `frontend/lib/sse.ts`
- Create: `frontend/app/chat/layout.tsx`
- Create: `frontend/app/chat/page.tsx`
- Create: `frontend/components/chat/session-sidebar.tsx`
- Create: `frontend/components/chat/message-list.tsx`
- Create: `frontend/components/chat/message-bubble.tsx`
- Create: `frontend/components/chat/composer.tsx`

- [ ] **Step 13.1: `lib/sse.ts`——fetch-based SSE reader（因为原生 EventSource 不支持 POST + Authorization）**

```typescript
export interface SseEvent {
  event: string;
  data: string;
}

export async function* streamSse(
  url: string,
  init: RequestInit & { signal?: AbortSignal }
): AsyncGenerator<SseEvent> {
  const resp = await fetch(url, init);
  if (!resp.ok || !resp.body) throw new Error(`SSE failed: ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let evt = "message";
      const dataLines: string[] = [];
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) evt = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      yield { event: evt, data: dataLines.join("\n") };
    }
  }
}
```

- [ ] **Step 13.2: `components/chat/session-sidebar.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Session = { id: string; title: string; created_at: string };

export function SessionSidebar({
  activeId,
  onSelect,
  onCreated,
}: {
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreated?: () => void;
}) {
  const token = useAuthStore((s) => s.token);
  const [items, setItems] = useState<Session[]>([]);

  const refresh = async () => {
    if (!token) return;
    const r = await api.listSessions(token);
    setItems(r.sessions);
  };

  useEffect(() => { void refresh(); }, [token]);

  const newSession = async () => {
    if (!token) return;
    const s = await api.createSession(token);
    await refresh();
    onSelect(s.id);
    onCreated?.();
  };

  return (
    <aside className="w-64 border-r flex flex-col">
      <div className="p-3">
        <Button onClick={newSession} className="w-full">新建会话</Button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {items.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={cn(
              "w-full text-left px-4 py-3 text-sm hover:bg-accent border-b",
              activeId === s.id && "bg-accent"
            )}
          >
            <div className="truncate">{s.title}</div>
            <div className="text-xs text-muted-foreground">{new Date(s.created_at).toLocaleString("zh-CN")}</div>
          </button>
        ))}
      </div>
    </aside>
  );
}
```

- [ ] **Step 13.3: `components/chat/message-bubble.tsx`**

```tsx
"use client";
import { cn } from "@/lib/utils";
import { CitationText } from "@/components/chat/citation-popover";

export interface Citation { idx: number; type: string; chunk_id: string; label: string }

export function MessageBubble({
  role, content, citations,
}: { role: "user" | "assistant"; content: string; citations?: Citation[] }) {
  const isUser = role === "user";
  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "rounded-2xl px-4 py-3 max-w-[85%] whitespace-pre-wrap leading-relaxed text-sm shadow-sm",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        )}
      >
        {isUser ? content : <CitationText text={content} citations={citations || []} />}
      </div>
    </div>
  );
}
```

- [ ] **Step 13.4: `components/chat/message-list.tsx`**

```tsx
"use client";
import { useEffect, useRef } from "react";
import { MessageBubble, type Citation } from "./message-bubble";

export interface ChatMsg { id: string; role: "user" | "assistant"; content: string; citations?: Citation[] }

export function MessageList({ messages, streamingText, streamingCitations }: {
  messages: ChatMsg[];
  streamingText: string;
  streamingCitations: Citation[];
}) {
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streamingText]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {messages.map((m) => (
        <MessageBubble key={m.id} role={m.role} content={m.content} citations={m.citations} />
      ))}
      {streamingText && (
        <MessageBubble role="assistant" content={streamingText} citations={streamingCitations} />
      )}
      <div ref={endRef} />
    </div>
  );
}
```

- [ ] **Step 13.5: `components/chat/composer.tsx`**

```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";

export function Composer({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState("");

  const submit = () => {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  };

  return (
    <div className="border-t p-3 flex gap-2 items-end">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        rows={2}
        placeholder="问一下劳动法问题（Enter 发送，Shift+Enter 换行）"
        className="flex-1 resize-none rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
      />
      <Button onClick={submit} disabled={disabled || !text.trim()}>发送</Button>
    </div>
  );
}
```

- [ ] **Step 13.6: `app/chat/layout.tsx`——未登录守卫**

```tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  useEffect(() => {
    if (!token) router.replace("/login");
  }, [token, router]);
  if (!token) return null;
  return <>{children}</>;
}
```

- [ ] **Step 13.7: `app/chat/page.tsx`——主页面**

```tsx
"use client";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import { streamSse } from "@/lib/sse";
import { SessionSidebar } from "@/components/chat/session-sidebar";
import { MessageList, type ChatMsg } from "@/components/chat/message-list";
import { Composer } from "@/components/chat/composer";
import type { Citation } from "@/components/chat/message-bubble";

export default function ChatPage() {
  const token = useAuthStore((s) => s.token)!;
  const [sid, setSid] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [streaming, setStreaming] = useState(false);

  useEffect(() => {
    if (!sid) return;
    void api.listMessages(token, sid).then((r) =>
      setMessages(r.messages.map((m) => ({
        id: m.id,
        role: m.role as "user" | "assistant",
        content: m.content,
        citations: m.citations as Citation[],
      })))
    );
  }, [sid, token]);

  const ready = useMemo(() => Boolean(sid) && !streaming, [sid, streaming]);

  const send = async (text: string) => {
    if (!sid) return;
    setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: "user", content: text }]);
    setStreamingText("");
    setStreamingCitations([]);
    setStreaming(true);

    try {
      const it = streamSse(`/api/chat/sessions/${sid}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
        body: JSON.stringify({ content: text }),
      });
      let buf = "";
      let finalCitations: Citation[] = [];
      for await (const evt of it) {
        if (evt.event === "token") {
          const payload = JSON.parse(evt.data);
          buf += payload.text;
          setStreamingText(buf);
        } else if (evt.event === "citations") {
          const payload = JSON.parse(evt.data);
          finalCitations = payload.citations as Citation[];
          setStreamingCitations(finalCitations);
        } else if (evt.event === "done") {
          const payload = JSON.parse(evt.data);
          setMessages((prev) => [...prev, { id: payload.message_id, role: "assistant", content: buf, citations: finalCitations }]);
          setStreamingText("");
          setStreamingCitations([]);
        } else if (evt.event === "error") {
          throw new Error(evt.data);
        }
      }
    } catch (e) {
      setMessages((prev) => [...prev, { id: `err-${Date.now()}`, role: "assistant", content: `⚠️ 发送失败：${String(e)}` }]);
    } finally {
      setStreaming(false);
    }
  };

  return (
    <main className="h-screen flex">
      <SessionSidebar activeId={sid} onSelect={setSid} />
      <section className="flex-1 flex flex-col">
        {!sid ? (
          <div className="flex-1 grid place-items-center text-muted-foreground">选择或新建会话开始咨询</div>
        ) : (
          <>
            <MessageList messages={messages} streamingText={streamingText} streamingCitations={streamingCitations} />
            <Composer disabled={!ready} onSend={send} />
          </>
        )}
      </section>
    </main>
  );
}
```

- [ ] **Step 13.8: 手动验证**：前后端都起来（fake provider）、登录、新建会话、发送消息，看到流式回答（没有引用气泡，是下一 task 的事）。

- [ ] **Step 13.9: Commit**

```bash
git add frontend/lib/sse.ts frontend/app/chat frontend/components/chat
git commit -m "feat(frontend): add chat page with sessions sidebar and SSE streaming"
```

---

## Task 14: 引用气泡 + Sources 页

**Files:**
- Create: `frontend/components/ui/popover.tsx`
- Create: `frontend/components/chat/citation-popover.tsx`
- Create: `frontend/app/sources/page.tsx`
- Create: `frontend/tests/components/citation-popover.test.tsx`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/tests/setup.ts`

- [ ] **Step 14.1: `components/ui/popover.tsx`（Radix 包装）**

```tsx
"use client";
import * as React from "react";
import * as Popover from "@radix-ui/react-popover";
import { cn } from "@/lib/utils";

export const PopoverRoot = Popover.Root;
export const PopoverTrigger = Popover.Trigger;

export const PopoverContent = React.forwardRef<
  React.ElementRef<typeof Popover.Content>,
  React.ComponentPropsWithoutRef<typeof Popover.Content>
>(({ className, align = "center", sideOffset = 4, ...props }, ref) => (
  <Popover.Portal>
    <Popover.Content
      ref={ref}
      align={align}
      sideOffset={sideOffset}
      className={cn(
        "z-50 w-80 rounded-md border bg-background p-3 text-sm shadow-md outline-none",
        className
      )}
      {...props}
    />
  </Popover.Portal>
));
PopoverContent.displayName = "PopoverContent";
```

- [ ] **Step 14.2: `components/chat/citation-popover.tsx`**

```tsx
"use client";
import { useState } from "react";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import { PopoverRoot, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import type { Citation } from "./message-bubble";

export function CitationText({ text, citations }: { text: string; citations: Citation[] }) {
  const parts: (string | Citation)[] = [];
  const re = /\[#(\d+)\]/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    const n = Number(m[1]);
    const start = m.index ?? 0;
    if (start > last) parts.push(text.slice(last, start));
    const c = citations.find((c) => c.idx === n);
    if (c) parts.push(c);
    else parts.push(m[0]);
    last = start + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));

  return (
    <span>
      {parts.map((p, i) =>
        typeof p === "string" ? <span key={i}>{p}</span> : <CitationChip key={i} citation={p} />
      )}
    </span>
  );
}

function CitationChip({ citation }: { citation: Citation }) {
  const token = useAuthStore((s) => s.token)!;
  const [detail, setDetail] = useState<{ label: string; text: string; source_url: string | null } | null>(null);

  const loadDetail = async () => {
    if (detail) return;
    const d = await api.getChunk(token, citation.chunk_id);
    setDetail({ label: d.label, text: d.text, source_url: d.source_url });
  };

  return (
    <PopoverRoot onOpenChange={(o) => o && loadDetail()}>
      <PopoverTrigger asChild>
        <button className="inline-flex items-center mx-0.5 px-1.5 py-0 rounded text-[11px] font-medium bg-primary/10 text-primary hover:bg-primary/20 align-middle">
          [#{citation.idx}]
        </button>
      </PopoverTrigger>
      <PopoverContent side="top">
        <div className="text-xs font-semibold mb-1">{citation.label}</div>
        <div className="text-xs text-muted-foreground whitespace-pre-wrap max-h-48 overflow-y-auto">
          {detail?.text ?? "加载中…"}
        </div>
        {detail?.source_url && (
          <a href={detail.source_url} target="_blank" rel="noreferrer" className="block mt-2 text-xs text-primary">
            查看来源 →
          </a>
        )}
      </PopoverContent>
    </PopoverRoot>
  );
}
```

- [ ] **Step 14.3: `app/sources/page.tsx`**

```tsx
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import { useAuthStore } from "@/lib/auth-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Law { law_name: string; region: string; article_count: number; effective_date: string | null }

export default function SourcesPage() {
  const token = useAuthStore((s) => s.token);
  const [laws, setLaws] = useState<Law[]>([]);
  useEffect(() => {
    if (!token) return;
    void api.listLaws(token).then((r) => setLaws(r.laws));
  }, [token]);

  return (
    <main className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">知识库</h1>
      <div className="space-y-3">
        {laws.map((l) => (
          <Card key={`${l.law_name}-${l.region}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{l.law_name}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              地域：{l.region}　｜　条文：{l.article_count} 条{l.effective_date ? `　｜　生效：${l.effective_date}` : ""}
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
```

- [ ] **Step 14.4: Vitest 配置**

`frontend/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: { environment: "happy-dom", setupFiles: ["./tests/setup.ts"], globals: true },
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
});
```

`frontend/tests/setup.ts`:

```typescript
import "@testing-library/react";
```

- [ ] **Step 14.5: `frontend/tests/components/citation-popover.test.tsx`**

```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CitationText } from "@/components/chat/citation-popover";

describe("CitationText", () => {
  it("renders citation chips for matching indices", () => {
    render(
      <CitationText
        text="结论 [#1] 很重要，其次 [#2] 也有用。"
        citations={[
          { idx: 1, type: "law", chunk_id: "c1", label: "劳动合同法·第三十九条" },
          { idx: 2, type: "case", chunk_id: "c2", label: "(2023)京01民终1号" },
        ]}
      />
    );
    expect(screen.getByText("[#1]")).toBeDefined();
    expect(screen.getByText("[#2]")).toBeDefined();
    expect(screen.getByText(/结论/)).toBeDefined();
  });

  it("keeps unresolved citation as plain text", () => {
    render(<CitationText text="x [#7] y" citations={[]} />);
    expect(screen.getByText(/\[#7\]/)).toBeDefined();
  });
});
```

- [ ] **Step 14.6: 运行前端测试**

```bash
cd frontend && pnpm test
```

Expected: 2 passed.

- [ ] **Step 14.7: 手动验证 hover**：起全栈、登录、发送一条 fake provider 返回带 `[#1]` 的回答，鼠标悬停 `[#1]` 气泡，应弹出 chunk 原文。

- [ ] **Step 14.8: Commit**

```bash
git add frontend/components/ui/popover.tsx frontend/components/chat/citation-popover.tsx frontend/app/sources frontend/vitest.config.ts frontend/tests
git commit -m "feat(frontend): add citation popover and knowledge sources page"
```

---

## Task 15: Docker Compose + 种子数据

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `backend/data/laws/labor_contract_law.txt`
- Create: `backend/data/laws/labor_law.txt`
- Create: `backend/data/laws/social_insurance_law.txt`
- Create: `backend/data/laws/labor_contract_law_regulations.txt`
- Create: `backend/data/laws/work_injury_regulations.txt`
- Create: `backend/data/local_regs/beijing_wage_payment.txt`
- Create: `backend/data/interpretations/sc_labor_disputes_1.txt`
- Create: `Makefile`

- [ ] **Step 15.1: `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev
COPY backend/ ./
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "sh", "-c", "alembic upgrade head && uvicorn free_hr.api.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 15.2: `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

FROM node:20-alpine AS build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
RUN pnpm build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
COPY --from=build /app ./
EXPOSE 3000
CMD ["pnpm", "start"]
```

- [ ] **Step 15.3: `infra/docker-compose.yml`**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: free_hr
      POSTGRES_PASSWORD: free_hr
      POSTGRES_DB: free_hr
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/00-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U free_hr -d free_hr"]
      interval: 5s
      timeout: 3s
      retries: 20

  backend:
    build:
      context: ..
      dockerfile: backend/Dockerfile
    env_file: ../.env
    environment:
      POSTGRES_URL: postgresql+asyncpg://free_hr:free_hr@postgres:5432/free_hr
      CORS_ORIGINS: http://localhost:3000
    depends_on:
      postgres:
        condition: service_healthy
    ports: ["8000:8000"]

  frontend:
    build:
      context: ..
      dockerfile: frontend/Dockerfile
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://backend:8000
    depends_on: [backend]
    ports: ["3000:3000"]

volumes:
  pgdata:
```

- [ ] **Step 15.4: 种子法规数据（示例：劳动合同法片段）**

> **说明**：法规原文受版权保护但属于官方公开法律文本，可从全国人大官网复制完整内容。下面给出**文件格式**和一条样例，engineer 须自行从 npc.gov.cn 完整抓取。

`backend/data/laws/labor_contract_law.txt`（**完整内容来自 npc.gov.cn，engineer 须补齐全文**）：

```
# 中华人民共和国劳动合同法
<!-- region: national, effective: 2013-07-01, url: http://www.npc.gov.cn/... -->

第一章 总则
第一条 为了完善劳动合同制度，明确劳动合同双方当事人的权利和义务，保护劳动者的合法权益，构建和发展和谐稳定的劳动关系，制定本法。
第二条 中华人民共和国境内的企业、个体经济组织、民办非企业单位等组织（以下称用人单位）与劳动者建立劳动关系，订立、履行、变更、解除或者终止劳动合同，适用本法。
...（engineer：从官方源站复制完整条文至本文件结尾，务必逐字核对）
```

对以下文件同样方式补齐：

- `backend/data/laws/labor_law.txt`（中华人民共和国劳动法）
- `backend/data/laws/social_insurance_law.txt`（社会保险法）
- `backend/data/laws/labor_contract_law_regulations.txt`（劳动合同法实施条例）
- `backend/data/laws/work_injury_regulations.txt`（工伤保险条例）
- `backend/data/local_regs/beijing_wage_payment.txt`（北京市工资支付规定，首行 meta 写 `region: beijing`）
- `backend/data/interpretations/sc_labor_disputes_1.txt`（最高人民法院关于审理劳动争议案件适用法律问题的解释）

所有文件首行 `# <法名>`；第二行 `<!-- region: ..., effective: YYYY-MM-DD, url: ... -->`；其余为正文，按"第 X 条"格式。

- [ ] **Step 15.5: 仓库根 `Makefile`**

```makefile
.PHONY: up down logs ingest backend-test frontend-test

up:
\tdocker compose -f infra/docker-compose.yml --env-file .env up -d --build

down:
\tdocker compose -f infra/docker-compose.yml down

logs:
\tdocker compose -f infra/docker-compose.yml logs -f backend frontend

ingest:
\tdocker compose -f infra/docker-compose.yml exec backend uv run free-hr-ingest all

backend-test:
\tcd backend && uv run pytest

frontend-test:
\tcd frontend && pnpm test
```

（Makefile 使用 Tab 缩进——replace `\t` with actual tab when creating file.）

- [ ] **Step 15.6: 起全栈**

```bash
cp .env.example .env   # 编辑 LLM_API_KEY / EMBEDDING_API_KEY
make up
# 等待健康检查
curl http://localhost:8000/api/health
# 摄入种子
make ingest
# 浏览器
open http://localhost:3000
```

- [ ] **Step 15.7: Commit**

```bash
git add infra/ backend/Dockerfile frontend/Dockerfile backend/data/ Makefile
git commit -m "chore: add docker-compose, dockerfiles, seed law data scaffolding, makefile"
```

---

## Task 16: 评测集 + E2E smoke + README 打磨

**Files:**
- Create: `backend/tests/eval/seed_questions.yaml`
- Create: `backend/tests/eval/run_eval.py`
- Create: `backend/tests/eval/__init__.py`
- Modify: `README.md`

- [ ] **Step 16.1: `seed_questions.yaml`（完整 15 题）**

```yaml
- id: q01
  question: 员工连续旷工 3 天，单位能否解除劳动合同？
  expected_laws: ["劳动合同法·第三十九条"]
  must_include_phrases: ["规章制度", "严重违反"]

- id: q02
  question: 试用期最长可以约定多久？
  expected_laws: ["劳动合同法·第十九条"]
  must_include_phrases: ["六个月", "三年以上"]

- id: q03
  question: 员工在试用期内被解除，需要给经济补偿吗？
  expected_laws: ["劳动合同法·第三十九条", "劳动合同法·第四十条"]
  must_include_phrases: ["不符合录用条件"]

- id: q04
  question: 未签订书面劳动合同超过一个月要承担什么责任？
  expected_laws: ["劳动合同法·第八十二条"]
  must_include_phrases: ["双倍工资", "二倍"]

- id: q05
  question: 经济补偿金如何计算？
  expected_laws: ["劳动合同法·第四十七条"]
  must_include_phrases: ["工作年限", "月工资"]

- id: q06
  question: 违法解除劳动合同，单位需要支付多少赔偿？
  expected_laws: ["劳动合同法·第四十八条", "劳动合同法·第八十七条"]
  must_include_phrases: ["二倍", "经济补偿"]

- id: q07
  question: 用人单位能否单方调岗？
  expected_laws: ["劳动合同法·第三十五条"]
  must_include_phrases: ["协商一致", "书面变更"]

- id: q08
  question: 加班费如何计算？
  expected_laws: ["劳动法·第四十四条"]
  must_include_phrases: ["百分之一百五十", "百分之二百", "百分之三百"]

- id: q09
  question: 员工隐瞒真实学历被发现可以解除吗？
  expected_laws: ["劳动合同法·第二十六条", "劳动合同法·第三十九条"]
  must_include_phrases: ["欺诈", "无效"]

- id: q10
  question: 工伤认定在职工死亡后多长时间内提出？
  expected_laws: ["工伤保险条例·第十七条"]
  must_include_phrases: ["30 日", "1 年"]

- id: q11
  question: 北京市工资支付有没有具体规定？
  expected_laws: ["北京市工资支付规定"]
  must_include_phrases: ["北京"]

- id: q12
  question: 劳务派遣工和正式员工有啥区别？
  expected_laws: ["劳动合同法·第五十七条", "劳动合同法·第六十六条"]
  must_include_phrases: ["临时性", "辅助性", "替代性"]

- id: q13
  question: 年休假天数怎么算？
  expected_laws: ["劳动法·第四十五条"]
  must_include_phrases: ["连续工作", "年休假"]

- id: q14
  question: 女职工产假有多少天？
  must_include_phrases: ["98 日", "九十八天"]

- id: q15
  question: 单位不给上社保，员工能要求什么？
  expected_laws: ["社会保险法", "劳动合同法·第三十八条"]
  must_include_phrases: ["解除", "经济补偿"]
```

- [ ] **Step 16.2: `run_eval.py`——手工评测脚本**

```python
"""
手工评测脚本：读入 seed_questions.yaml，依次对本地 API 发起真实请求，
把回答 + 命中的引用 dump 到 eval_report.md，人工核对。
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import httpx
import yaml


async def run():
    api_base = os.environ.get("API_BASE", "http://localhost:8000")
    email = os.environ.get("EVAL_EMAIL", "admin@example.com")
    password = os.environ.get("EVAL_PASSWORD", "admin-change-me")
    qs = yaml.safe_load(Path(__file__).with_name("seed_questions.yaml").read_text(encoding="utf-8"))

    async with httpx.AsyncClient(base_url=api_base, timeout=120.0) as c:
        tok = (await c.post("/api/auth/login", json={"email": email, "password": password})).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        sid = (await c.post("/api/chat/sessions", headers=h, json={"title": "eval"})).json()["id"]

        report: list[str] = ["# Eval Report\n"]
        for q in qs:
            report.append(f"\n## {q['id']}\n\n**Q:** {q['question']}\n")
            body = ""
            citations: list = []
            async with c.stream("POST", f"/api/chat/sessions/{sid}/messages", headers=h, json={"content": q["question"]}) as r:
                evt = None
                async for line in r.aiter_lines():
                    if line.startswith("event:"):
                        evt = line[6:].strip()
                    elif line.startswith("data:") and evt:
                        data = line[5:].strip()
                        if evt == "token":
                            body += json.loads(data)["text"]
                        elif evt == "citations":
                            citations = json.loads(data)["citations"]
                        evt = None
            report.append(f"\n**A:** {body}\n\n**Citations:** {[c['label'] for c in citations]}\n")
            report.append(f"\n**Expected laws:** {q.get('expected_laws', [])}")
            report.append(f"\n**Must include:** {q.get('must_include_phrases', [])}\n")

        Path("eval_report.md").write_text("\n".join(report), encoding="utf-8")
        print("Wrote eval_report.md")


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 16.3: 跑一次评测（在真实 API key 环境下）**

```bash
# 前提：make up && make ingest 已完成
cd backend && uv run python tests/eval/run_eval.py
# 人工打开 eval_report.md 逐题核对
```

- [ ] **Step 16.4: 更新 `README.md`**

```markdown
# Free-HR

面向中国大陆中小企业的用工合规 AI 助手。

## 产品定位

面向 HR、HR 主管、高管、老板：

1. **AI 法律咨询**：自然语言提问劳动法问题，回答基于国家法 + 北京地方法规 + 司法解释知识库，每条结论带 `[#n]` 引用编号，hover 可查原文。
2. **用工风险预警（可视化）**：上传员工花名册 / 合同 / 制度，覆盖入职→在职→离职全周期风险（Phase 2+ 规划中）。

## 交付阶段

| 阶段 | 范围 | 状态 |
|---|---|---|
| **Phase 1** | AI 法律咨询 MVP：RAG 对话 + 引用溯源 + 基础账号 | ✅ 已完成 |
| Phase 2 | 文档风险审查（合同 / 手册 / 规章制度） | 规划中 |
| Phase 3 | 员工全周期风险看板 | 规划中 |

## 技术栈

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy (async) + Alembic
- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **DB**: PostgreSQL 16 + pgvector（HNSW 向量索引）
- **LLM**: DeepSeek Chat（默认）/ 可切换 Qwen / OpenAI / Claude
- **Embedding**: bge-m3（via SiliconFlow）
- **Deploy**: Docker Compose 单租户自部署

## 快速开始

```bash
git clone https://github.com/yanlinyi101/Free-HR.git
cd Free-HR
cp .env.example .env         # 填 LLM_API_KEY 与 EMBEDDING_API_KEY
make up                      # 起全栈
make ingest                  # 导入种子知识库
open http://localhost:3000   # 默认账号见 .env 中 ADMIN_EMAIL / ADMIN_PASSWORD
```

## 本地开发

```bash
# 后端
cd backend && uv sync --dev && uv run uvicorn free_hr.api.main:app --reload

# 前端
cd frontend && pnpm install && pnpm dev
```

## 测试

```bash
make backend-test
make frontend-test
```

## 文档

- [Phase 1 设计 Spec](docs/superpowers/specs/2026-04-18-free-hr-phase1-legal-chat-design.md)
- [Phase 1 实现 Plan](docs/superpowers/plans/2026-04-18-free-hr-phase1-legal-chat.md)

## 免责声明

本工具输出内容仅供参考，不构成法律意见。重大法律事项请咨询专业律师。
```

- [ ] **Step 16.5: 最终全量测试 + 类型检查**

```bash
cd backend && uv run pytest -q && uv run ruff check src tests
cd frontend && pnpm typecheck && pnpm lint && pnpm test
```

Expected: 全部绿。

- [ ] **Step 16.6: Commit**

```bash
git add backend/tests/eval/ README.md
git commit -m "feat: add eval harness, seed questions, polish README for Phase 1 release"
```

- [ ] **Step 16.7: Push 到远端**

```bash
git push origin main
```

---

## 验收清单（对应 spec §12）

- [ ] `docker compose up` 起全栈，`/api/health` 200。
- [ ] admin 账号自动 bootstrap，登录后可通过 `/api/auth/register` 创建 HR 账号。
- [ ] `make ingest` 后 `/api/knowledge/laws` 返回 ≥ 6 部法规。
- [ ] HR 登录后在 `/chat` 创建会话，发问获得流式回答。
- [ ] 回答中 ≥ 80% 结论带 `[#n]` 引用（手工抽查 3 题）；hover 弹出原文。
- [ ] `backend/tests/eval/seed_questions.yaml` 15 题全部跑完，人工 diff `eval_report.md`。
- [ ] 所有单元 + 集成测试通过；`ruff check` / `pnpm typecheck` / `pnpm lint` 无报错。

---

## 自检结果（writer's own review）

**Spec coverage check**: 逐节对应——

- Spec §3 技术栈 → Task 1 / 11 / 15
- Spec §4 架构与模块 → Task 1 / 4-10
- Spec §5 数据模型 → Task 2 / 3
- Spec §6 RAG 流水线 → Task 8 / 9
- Spec §7 API → Task 10
- Spec §8 错误处理 → Task 9 / 10（SSE error 事件、越界引用过滤、越权 404）
- Spec §9 测试策略 → 散落在各 Task + Task 16 评测集
- Spec §10 安全 → Task 5（bcrypt、JWT）+ Task 11（免责声明）+ Task 10（越权 404）
- Spec §11 部署 → Task 15
- Spec §12 验收 → 文末验收清单

**Placeholder check**: 仅法规原文部分（Task 15 Step 15.4）要求 engineer 从官方源站抓取完整条文——这是一次性人工动作，且 spec §2 已明确要求这些法规为知识库冷启动内容，engineer 按文件格式填入即可。所有代码步骤均含完整可运行代码，无 TODO / TBD。

**Type consistency check**:

- `LawChunkHit` / `CaseChunkHit` 在 Task 6 定义，Task 8 / 9 使用，字段一致。
- `ContextRef` 在 Task 8 `chat/schemas.py` 定义，Task 8 / 9 使用。
- `ChatEvent` / `ChatEventType` Task 8 定义，Task 9 / 10 使用。
- 前端 `Citation` 接口在 Task 13 `message-bubble.tsx` 定义，Task 14 `citation-popover.tsx` 使用，字段一致（`idx` / `type` / `chunk_id` / `label`）。
- API 响应形状（`{token, user}` / `{sessions: [...]}` / `{citations: [...]}`）前后端对齐。
